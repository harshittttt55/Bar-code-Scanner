import os
import re
import json
import time
import logging
import asyncio
from typing import Optional, Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "45"))
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "86400"))
CACHE_MAX_ITEMS = 1000
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()
]
INCLUDE_RAW = os.getenv("DEBUG_RAW_RESPONSE", "").lower() in ("1", "true", "yes")

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is not configured. Web research is disabled.")

# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="Product Barcode Lookup API",
    description="Multi-source barcode lookup using public product databases and Google Search research.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Models
# ---------------------------------------------------------


class BarcodeRequest(BaseModel):
    barcode: str = Field(..., min_length=1, max_length=100)


class ProductInfo(BaseModel):
    barcode: str
    product_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    mrp: Optional[float] = None
    ingredients: Optional[str] = None
    nutritional_info: Optional[Any] = None
    best_before: Optional[str] = None
    instructions: Optional[str] = None
    manufacturer: Optional[str] = None
    country_of_origin: Optional[str] = None
    net_weight: Optional[str] = None
    allergens: Optional[str] = None
    storage_instructions: Optional[str] = None
    certifications: Optional[str] = None
    additional_info: Optional[str] = None
    found: bool = False
    sources: list[str] = Field(default_factory=list)
    verification_status: str = "not_found"
    check_digit_valid: bool = True
    raw_response: Optional[str] = None


# ---------------------------------------------------------
# Simple in-memory TTL cache
# ---------------------------------------------------------

_cache: dict[str, tuple[float, ProductInfo]] = {}


def cache_get(barcode: str) -> Optional[ProductInfo]:
    item = _cache.get(barcode)
    if not item:
        return None
    stored_at, data = item
    if time.time() - stored_at > CACHE_TTL:
        _cache.pop(barcode, None)
        return None
    return data


def cache_set(barcode: str, data: ProductInfo) -> None:
    if len(_cache) >= CACHE_MAX_ITEMS:
        oldest = min(_cache, key=lambda k: _cache[k][0])
        _cache.pop(oldest, None)
    _cache[barcode] = (time.time(), data)


# ---------------------------------------------------------
# Barcode helpers
# ---------------------------------------------------------


def clean_barcode(value: str) -> str:
    """Remove whitespace and hyphens."""
    return re.sub(r"[\s-]", "", value.strip())


def is_supported_barcode(barcode: str) -> bool:
    """Digits only, EAN-8 / UPC-A / EAN-13 / GTIN-14 lengths."""
    return barcode.isdigit() and len(barcode) in (8, 12, 13, 14)


def has_valid_check_digit(barcode: str) -> bool:
    digits = [int(c) for c in barcode]
    check_digit = digits.pop()
    weighted_sum = sum(
        d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits))
    )
    return check_digit == (10 - weighted_sum % 10) % 10


def same_barcode(a: str, b: str) -> bool:
    """Treat UPC-A and zero-padded EAN-13 forms as equal."""
    return a.lstrip("0") == b.lstrip("0")


# ---------------------------------------------------------
# General helpers
# ---------------------------------------------------------


def has_value(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def first_value(*values):
    for value in values:
        if has_value(value):
            return value
    return None


def text_value(value: Any) -> Optional[str]:
    if not has_value(value):
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def extract_json(text: str) -> dict:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        result = json.loads(cleaned)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(0))
            return result if isinstance(result, dict) else {}
        except json.JSONDecodeError:
            pass
    return {}


def extract_grounding_sources(response) -> list[str]:
    urls = []
    try:
        for candidate in response.candidates or []:
            metadata = getattr(candidate, "grounding_metadata", None)
            if not metadata:
                continue
            for chunk in getattr(metadata, "grounding_chunks", None) or []:
                web_item = getattr(chunk, "web", None)
                uri = getattr(web_item, "uri", None) if web_item else None
                if uri and uri.startswith(("https://", "http://")):
                    urls.append(uri)
    except Exception:
        logger.exception("Could not extract grounding sources.")
    return list(dict.fromkeys(urls))


def parse_mrp(value: Any) -> Optional[float]:
    """Parse a single clean price: 45, "45", "₹45", "Rs. 45.50", "MRP ₹45"."""
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        number = float(value)
        return number if 0 < number < 10_000_000 else None

    text = str(value).strip()
    if not text:
        return None

    if re.search(
        r"\b(from|starting|approx|around|between|sale price|selling price|discount|offer price)\b",
        text,
        re.I,
    ):
        return None

    match = re.fullmatch(
        r"(?:MRP\s*:?\s*)?(?:₹|Rs\.?|INR)?\s*(\d[\d,]*(?:\.\d{1,2})?)\s*(?:/-|INR|rupees?)?",
        text,
        re.I,
    )
    if not match:
        return None

    try:
        number = float(match.group(1).replace(",", ""))
        return number if 0 < number < 10_000_000 else None
    except ValueError:
        return None


def slim_nutriments(value: Any) -> Any:
    """Open Food Facts nutriments is huge; keep only per-100g values."""
    if isinstance(value, dict):
        slim = {k: v for k, v in value.items() if k.endswith("_100g")}
        return slim or None
    return value


# ---------------------------------------------------------
# Public product databases
# ---------------------------------------------------------


async def fetch_json(client: httpx.AsyncClient, url: str) -> Optional[dict]:
    try:
        response = await client.get(url)
        if response.status_code != 200:
            logger.info("Source returned HTTP %s: %s", response.status_code, url)
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Source request failed for %s: %s", url, exc)
        return None


async def lookup_product_databases(barcode: str) -> list[dict]:
    """Query Open Food Facts and Open Beauty Facts for an exact barcode match."""
    headers = {"User-Agent": "BarcodeProductLookup/3.0 (product research application)"}

    databases = [
        (
            "Open Food Facts",
            f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json",
            f"https://world.openfoodfacts.org/product/{barcode}",
        ),
        (
            "Open Beauty Facts",
            f"https://world.openbeautyfacts.org/api/v2/product/{barcode}.json",
            f"https://world.openbeautyfacts.org/product/{barcode}",
        ),
    ]

    async with httpx.AsyncClient(
        timeout=12.0, headers=headers, follow_redirects=True
    ) as client:
        results = await asyncio.gather(*(fetch_json(client, url) for _, url, _ in databases))

    records = []
    for (source_name, _, product_url), data in zip(databases, results):
        if not data or data.get("status") != 1:
            continue

        product = data.get("product")
        if not isinstance(product, dict):
            continue

        returned = clean_barcode(str(product.get("code") or ""))
        if not same_barcode(returned, barcode):
            continue

        records.append(
            {
                "source": source_name,
                "barcode": barcode,
                "product_name": product.get("product_name") or product.get("product_name_en"),
                "brand": product.get("brands"),
                "category": product.get("categories"),
                "net_weight": product.get("quantity") or product.get("product_quantity"),
                "ingredients": product.get("ingredients_text"),
                "nutritional_info": slim_nutriments(product.get("nutriments")),
                "best_before": product.get("expiration_date"),
                "manufacturer": product.get("manufacturing_places"),
                "country_of_origin": product.get("origins"),
                "allergens": product.get("allergens"),
                "storage_instructions": product.get("preservation"),
                "certifications": product.get("labels"),
                "product_url": product_url,
            }
        )

    return records


# ---------------------------------------------------------
# Gemini research
# ---------------------------------------------------------


async def research_with_google(
    barcode: str, database_records: list[dict]
) -> tuple[dict, list[str]]:
    """Research the barcode with Gemini + Google Search grounding."""
    if gemini_client is None:
        return {}, []

    db_hint = json.dumps(
        [
            {k: r.get(k) for k in ("source", "product_name", "brand", "net_weight")}
            for r in database_records
        ],
        ensure_ascii=False,
        default=str,
    )

    prompt = f"""
You are a careful product-identification assistant.

The user scanned this exact barcode:
{barcode}

Public product database hints:
{db_hint}

Use Google Search to research the exact barcode and product.

Rules:
1. Never infer a product identity from the barcode prefix alone.
2. A matching brand name is not proof of an exact barcode match.
3. Confirm a match only when a source explicitly connects the exact
   barcode {barcode} to the product and pack size.
4. Do not invent product names, pack sizes, manufacturers, or MRP.
5. A retailer's current selling price is not the printed MRP.
6. Only return an MRP when a source supports the printed MRP for the
   same product and pack size, as a single number (e.g. 45 or 45.50).
7. If the product cannot be identified, set product_name to null and
   barcode_match_confirmed to false.
8. barcode_evidence must quote or summarize evidence that explicitly
   includes the exact barcode string {barcode}.
9. If there is no MRP evidence, set mrp and mrp_evidence to null.
10. Return a single JSON object only. No Markdown.

Schema:
{{
  "barcode_match_confirmed": false,
  "barcode_evidence": null,
  "product_name": null,
  "brand": null,
  "category": null,
  "mrp": null,
  "mrp_evidence": null,
  "ingredients": null,
  "nutritional_info": null,
  "best_before": null,
  "instructions": null,
  "manufacturer": null,
  "country_of_origin": null,
  "net_weight": null,
  "allergens": null,
  "storage_instructions": null,
  "certifications": null,
  "additional_info": null
}}
"""

    try:
        # Note: response_mime_type="application/json" is NOT used here because
        # it is not supported together with the Google Search tool.
        response = await asyncio.wait_for(
            asyncio.to_thread(
                gemini_client.models.generate_content,
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1,
                ),
            ),
            timeout=GEMINI_TIMEOUT,
        )

        research = extract_json(getattr(response, "text", None) or "")
        sources = extract_grounding_sources(response)

        logger.info(
            "Gemini research for %s: product=%s confirmed=%s sources=%d",
            barcode,
            research.get("product_name"),
            research.get("barcode_match_confirmed"),
            len(sources),
        )
        return research, sources

    except asyncio.TimeoutError:
        logger.warning("Gemini research timed out for barcode %s", barcode)
        return {}, []
    except Exception:
        logger.exception("Gemini research failed for barcode %s", barcode)
        return {}, []


async def verify_barcode_in_sources(barcode: str, urls: list[str]) -> list[str]:
    """
    Fetch the cited pages and keep only those whose text actually contains
    the barcode. This is the real proof; the model's own claim is not.
    """
    if not urls:
        return []

    headers = {"User-Agent": "Mozilla/5.0 (compatible; BarcodeProductLookup/3.0)"}

    async def check(client: httpx.AsyncClient, url: str) -> Optional[str]:
        try:
            response = await client.get(url)
            if response.status_code != 200:
                return None
            if barcode in response.text[:500_000]:
                return str(response.url)
        except httpx.HTTPError:
            return None
        return None

    async with httpx.AsyncClient(
        timeout=10.0, headers=headers, follow_redirects=True
    ) as client:
        results = await asyncio.gather(*(check(client, u) for u in urls[:8]))

    return list(dict.fromkeys(r for r in results if r))


# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------


@app.get("/")
async def root():
    return {"message": "Product Barcode Lookup API is running", "docs": "/docs"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gemini_configured": gemini_client is not None,
        "model": GEMINI_MODEL,
        "cached_items": len(_cache),
    }


@app.post("/api/product", response_model=ProductInfo)
async def get_product(request: BarcodeRequest):
    barcode = clean_barcode(request.barcode)

    if not is_supported_barcode(barcode):
        raise HTTPException(
            status_code=400,
            detail="Barcode must be 8, 12, 13 or 14 digits.",
        )

    cached = cache_get(barcode)
    if cached:
        return cached

    # A bad check digit is reported, but we still try the lookup.
    check_ok = has_valid_check_digit(barcode)

    # Step 1: public databases
    try:
        records = await lookup_product_databases(barcode)
    except Exception:
        logger.exception("Product database lookup failed.")
        records = []

    usable_records = [r for r in records if has_value(r.get("product_name"))]

    # Step 2: web research
    research, web_sources = await research_with_google(barcode, records)

    # Step 3: verify the barcode on the actual cited pages
    verified_urls: list[str] = []
    if research.get("barcode_match_confirmed") is True and has_value(
        research.get("product_name")
    ):
        verified_urls = await verify_barcode_in_sources(barcode, web_sources)

    web_verified = bool(verified_urls)
    usable_research = research if web_verified else {}

    def db_value(key: str):
        for record in usable_records:
            if has_value(record.get(key)):
                return record.get(key)
        return None

    # Step 4: core fields
    product_name = first_value(db_value("product_name"), usable_research.get("product_name"))
    brand = first_value(db_value("brand"), usable_research.get("brand"))
    category = first_value(db_value("category"), usable_research.get("category"))

    # Step 5: MRP only with verified identity AND evidence
    mrp = None
    mrp_evidence = None
    if web_verified:
        candidate = parse_mrp(usable_research.get("mrp"))
        evidence = usable_research.get("mrp_evidence")
        if candidate is not None and has_value(evidence):
            mrp, mrp_evidence = candidate, evidence

    # Step 6: other fields
    fields = {
        key: first_value(db_value(key), usable_research.get(key))
        for key in (
            "ingredients",
            "nutritional_info",
            "best_before",
            "instructions",
            "manufacturer",
            "country_of_origin",
            "net_weight",
            "allergens",
            "storage_instructions",
            "certifications",
        )
    }

    # Step 7: notes
    notes = []
    if not check_ok:
        notes.append(
            "The barcode's check digit is invalid. It may be mistyped or an internal/store code."
        )
    if usable_records:
        notes.append("Exact barcode match found in a public product database.")
    else:
        notes.append("No usable record in the public product databases.")

    if web_verified:
        notes.append(
            f"Barcode found on {len(verified_urls)} cited web page(s). Review the sources before relying on it."
        )
    elif research.get("barcode_match_confirmed") is True:
        notes.append(
            "Web research claimed a match, but no cited page contained the barcode, so it was discarded."
        )
    elif research:
        notes.append("Web research found no confirmed product for this barcode.")
    else:
        notes.append("No web research result was available.")

    if mrp is not None:
        notes.append(f"MRP: {mrp}. Evidence: {mrp_evidence}")
    else:
        notes.append("No supported printed MRP found. A retailer price is not necessarily the MRP.")

    # Step 8: sources
    sources = [r["product_url"] for r in usable_records if r.get("product_url")]
    sources.extend(verified_urls)
    sources = list(dict.fromkeys(sources))

    # Step 9: status
    if usable_records and web_verified:
        status = "database_and_web_verified"
    elif usable_records:
        status = "database_match"
    elif web_verified:
        status = "web_verified"
    else:
        status = "not_found"

    found = bool(product_name) and status != "not_found"

    raw = None
    if INCLUDE_RAW:
        raw = json.dumps(
            {
                "database_records": records,
                "web_research": research,
                "web_sources": web_sources,
                "verified_urls": verified_urls,
            },
            ensure_ascii=False,
            default=str,
        )

    result = ProductInfo(
        barcode=barcode,
        product_name=text_value(product_name),
        brand=text_value(brand),
        category=text_value(category),
        mrp=mrp,
        ingredients=text_value(fields["ingredients"]),
        nutritional_info=fields["nutritional_info"],
        best_before=text_value(fields["best_before"]),
        instructions=text_value(fields["instructions"]),
        manufacturer=text_value(fields["manufacturer"]),
        country_of_origin=text_value(fields["country_of_origin"]),
        net_weight=text_value(fields["net_weight"]),
        allergens=text_value(fields["allergens"]),
        storage_instructions=text_value(fields["storage_instructions"]),
        certifications=text_value(fields["certifications"]),
        additional_info=" ".join(notes),
        found=found,
        sources=sources,
        verification_status=status,
        check_digit_valid=check_ok,
        raw_response=raw,
    )

    # Don't cache results when research failed outright (could be transient).
    if found or research or gemini_client is None:
        cache_set(barcode, result)

    logger.info(
        "Lookup finished for %s: found=%s mrp=%s status=%s",
        barcode,
        result.found,
        result.mrp,
        result.verification_status,
    )
    return result