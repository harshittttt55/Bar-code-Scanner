import os
import re
import json
import logging
import asyncio
import sqlite3
import time
from typing import Optional, Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
CACHE_DB_PATH = os.getenv("PRODUCT_CACHE_DB", "product_cache.sqlite3")
CACHE_TTL_SECONDS = int(os.getenv("PRODUCT_CACHE_TTL_SECONDS", "86400"))

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is not configured; web research is disabled.")

app = FastAPI(
    title="Product Barcode Lookup API",
    description="Database-first barcode lookup with cautious, source-aware web research.",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    verification_status: str = "not_verified"
    raw_response: Optional[str] = None


def clean_barcode(value: str) -> str:
    return re.sub(r"[\s-]", "", value.strip())


def is_valid_barcode(barcode: str) -> bool:
    """Validate common EAN/UPC/GTIN lengths and their check digit."""
    if not barcode.isdigit() or len(barcode) not in (8, 12, 13, 14):
        return False
    digits = [int(char) for char in barcode]
    check_digit = digits.pop()
    weighted_sum = sum(
        digit * (3 if index % 2 == 0 else 1)
        for index, digit in enumerate(reversed(digits))
    )
    expected_digit = (10 - weighted_sum % 10) % 10
    return check_digit == expected_digit


def init_cache() -> None:
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS product_cache (
                barcode TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                saved_at REAL NOT NULL
            )
        """)
        conn.commit()


def cache_get(barcode: str) -> Optional[dict]:
    try:
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            row = conn.execute(
                "SELECT response_json, saved_at FROM product_cache WHERE barcode = ?",
                (barcode,),
            ).fetchone()
        if not row:
            return None
        response_json, saved_at = row
        if time.time() - saved_at > CACHE_TTL_SECONDS:
            with sqlite3.connect(CACHE_DB_PATH) as conn:
                conn.execute("DELETE FROM product_cache WHERE barcode = ?", (barcode,))
                conn.commit()
            return None
        result = json.loads(response_json)
        return result if isinstance(result, dict) else None
    except (sqlite3.Error, json.JSONDecodeError) as exc:
        logger.warning("Product cache read failed: %s", exc)
        return None


def cache_set(barcode: str, response_data: dict) -> None:
    try:
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            conn.execute(
                """INSERT INTO product_cache (barcode, response_json, saved_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(barcode) DO UPDATE SET
                     response_json = excluded.response_json,
                     saved_at = excluded.saved_at""",
                (barcode, json.dumps(response_data, ensure_ascii=False), time.time()),
            )
            conn.commit()
    except sqlite3.Error as exc:
        logger.warning("Product cache write failed: %s", exc)


@app.on_event("startup")
async def startup_event():
    init_cache()


async def fetch_json(client: httpx.AsyncClient, url: str) -> Optional[dict]:
    try:
        response = await client.get(url)
        if response.status_code != 200:
            logger.info("Product source returned %s: %s", response.status_code, url)
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Product source request failed: %s", exc)
        return None


async def lookup_product_databases(barcode: str) -> list[dict]:
    """Search public product databases and only accept exact barcode records."""
    headers = {"User-Agent": "BarcodeProductLookup/2.1 (product research application)"}
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
        results = await asyncio.gather(
            *(fetch_json(client, url) for _, url, _ in databases)
        )

    records = []
    for (source_name, _, product_url), data in zip(databases, results):
        if not data or data.get("status") != 1:
            continue
        product = data.get("product")
        if not isinstance(product, dict):
            continue
        if clean_barcode(str(product.get("code") or "")) != barcode:
            continue

        records.append({
            "source": source_name,
            "barcode": barcode,
            "product_name": product.get("product_name") or product.get("product_name_en"),
            "brand": product.get("brands"),
            "category": product.get("categories"),
            "net_weight": product.get("quantity"),
            "ingredients": product.get("ingredients_text") or product.get("ingredients_text_en"),
            "nutritional_info": product.get("nutriments"),
            "allergens": product.get("allergens"),
            "manufacturer": product.get("manufacturing_places"),
            "country_of_origin": product.get("origins"),
            "instructions": product.get("preparation"),
            "storage_instructions": product.get("conservation") or product.get("storage_conditions"),
            "certifications": product.get("labels"),
            "image_url": product.get("image_front_url") or product.get("image_url"),
            "product_url": product_url,
        })
    return records


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
        logger.exception("Could not extract Gemini grounding sources.")
    return list(dict.fromkeys(urls))


def parse_mrp(value: Any) -> Optional[float]:
    """Parse an explicit numeric MRP value; do not parse vague ranges or prices."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if 0 < number < 10_000_000 else None

    text = str(value).strip()
    if not text or re.search(r"\b(from|starting|approx|around|between|sale price|selling price|discount)\b", text, re.I):
        return None
    match = re.search(
        r"(?:₹|INR\s*)(\d[\d,]*(?:\.\d{1,2})?)|"
        r"(\d[\d,]*(?:\.\d{1,2})?)\s*(?:INR|rupees?)\b",
        text,
        re.I,
    )
    if not match:
        return None
    try:
        number = float((match.group(1) or match.group(2)).replace(",", ""))
        return number if 0 < number < 10_000_000 else None
    except (TypeError, ValueError):
        return None


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


async def research_with_google(barcode: str, database_records: list[dict]) -> tuple[dict, list[str]]:
    """Use Gemini + Google Search as a discovery aid, not as independent proof."""
    if not gemini_client:
        return {}, []

    prompt = f"""
Research a consumer product for a barcode lookup application.

Exact barcode to investigate: {barcode}
Existing exact-barcode database records (may be empty):
{json.dumps(database_records, ensure_ascii=False, default=str)}

Use Google Search. Be conservative:
- Do not infer a product solely from a similar barcode, product name, image, or search result.
- The product identity is confirmed only if a source explicitly displays this exact barcode
  ({barcode}) and associates it with the product. If you cannot find that evidence, set
  barcode_match_confirmed to false and do not provide guessed product details.
- A source that only shows the same product name or pack size does not confirm the barcode.
- For MRP, require a source that explicitly identifies the value as MRP / Maximum Retail Price
  for the matching pack. Retailer selling prices, discounted prices, and offer prices are not MRP.
- Prefer manufacturer/brand-owner sources for product details; retailer listings may be used
  as secondary evidence.
- Never invent facts, URLs, prices, or source quotations.
- If evidence is missing or ambiguous, use null.
- Do not claim that a product is genuine or counterfeit based on barcode lookup alone.

Return one JSON object only with these keys:
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

Only set barcode_match_confirmed to true when you find direct evidence linking the exact barcode
to the product. In barcode_evidence, briefly describe the direct evidence and where it appears.
Only return a numeric mrp when an explicit MRP source supports it. Otherwise mrp must be null.
Do not include URLs in JSON; the application collects Google Search grounding URLs separately.
"""
    try:
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
            ),
        )
        result = extract_json(response.text or "")
        sources = extract_grounding_sources(response)
        logger.info("Gemini web research completed for barcode %s", barcode)
        if not result:
            logger.warning("Gemini did not return parseable JSON for %s", barcode)
        return result, sources
    except Exception as exc:
        logger.exception("Gemini Google Search research failed: %s", exc)
        return {}, []


@app.get("/")
async def root():
    return {"message": "Product Barcode Lookup API is running", "docs": "/docs"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gemini_configured": gemini_client is not None,
        "model": GEMINI_MODEL,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
    }


@app.post("/api/product", response_model=ProductInfo)
async def get_product(request: BarcodeRequest):
    barcode = clean_barcode(request.barcode)
    if not is_valid_barcode(barcode):
        raise HTTPException(status_code=400, detail="Invalid barcode format or check digit.")

    cached = cache_get(barcode)
    if cached:
        logger.info("Returning cached product lookup for %s", barcode)
        return ProductInfo(**cached)

    try:
        records = await lookup_product_databases(barcode)
    except Exception as exc:
        logger.exception("Database lookup failed: %s", exc)
        records = []

    logger.info("Barcode %s: found %d exact database record(s)", barcode, len(records))

    # Research when no database record exists or MRP is missing.
    database_has_mrp = False  # OFF/OBF records do not provide a reliable printed-MRP field.
    research, web_sources = await research_with_google(barcode, records)

    # Never merge web details unless Gemini reports direct exact-barcode evidence.
    # Such a web result remains provisional; it is not equivalent to independent verification.
    web_identity_supported = (
        research.get("barcode_match_confirmed") is True
        and has_value(research.get("barcode_evidence"))
        and bool(web_sources)
    )
    usable_research = research if web_identity_supported else {}

    def database_value(key: str):
        for record in records:
            if has_value(record.get(key)):
                return record.get(key)
        return None

    product_name = first_value(database_value("product_name"), usable_research.get("product_name"))
    brand = first_value(database_value("brand"), usable_research.get("brand"))
    category = first_value(database_value("category"), usable_research.get("category"))

    mrp = parse_mrp(usable_research.get("mrp"))
    mrp_evidence = usable_research.get("mrp_evidence")
    if not has_value(mrp_evidence):
        mrp = None

    fields = {}
    for key in (
        "ingredients", "nutritional_info", "best_before", "instructions",
        "manufacturer", "country_of_origin", "net_weight", "allergens",
        "storage_instructions", "certifications",
    ):
        fields[key] = first_value(database_value(key), usable_research.get(key))

    notes = []
    if records:
        notes.append("Exact barcode record found in a supported public product database.")
    else:
        notes.append("No exact record was found in the supported public product databases.")

    if web_identity_supported:
        notes.append(
            "Web research reported direct exact-barcode evidence. This result remains provisional; "
            "review the cited pages and package label before relying on it."
        )
        notes.append(f"Reported barcode evidence: {research.get('barcode_evidence')}")
    elif research:
        notes.append(
            "Web research did not establish a sufficiently supported exact-barcode match, "
            "so web-derived product details and MRP were not accepted."
        )
    else:
        notes.append("No usable web research result was available.")

    if mrp is not None:
        notes.append(f"MRP candidate reported by research: {mrp_evidence}")
    else:
        notes.append("No adequately supported printed MRP was found. A retailer selling price is not necessarily MRP.")

    sources = []
    for record in records:
        if record.get("product_url"):
            sources.append(record["product_url"])
    sources.extend(web_sources)
    sources = list(dict.fromkeys(sources))

    # Database records are exact barcode records. Web-only records are explicitly provisional.
    found = bool(records) or bool(web_identity_supported and (product_name or brand))
    if records and web_identity_supported:
        verification_status = "database_and_web_researched"
    elif records:
        verification_status = "database_match"
    elif found:
        verification_status = "web_researched_unverified"
    else:
        verification_status = "not_found"

    response_data = ProductInfo(
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
        verification_status=verification_status,
        raw_response=json.dumps(
            {
                "database_records": records,
                "web_research": research,
                "web_identity_supported": web_identity_supported,
                "web_sources": web_sources,
            },
            ensure_ascii=False,
            default=str,
        ),
    )

    result = response_data.model_dump()
    cache_set(barcode, result)
    logger.info(
        "Lookup finished for %s: found=%s, mrp=%s, status=%s",
        barcode, response_data.found, response_data.mrp, response_data.verification_status,
    )
    return response_data
