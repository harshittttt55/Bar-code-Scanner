import os
import re
import json
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

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

gemini_client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is not configured.")

app = FastAPI(
    title="Product Barcode Lookup API",
    description="Database-first barcode lookup with Gemini web research fallback.",
    version="2.0.0",
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
    """Validate common EAN/UPC/GTIN lengths and check digit."""
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


async def fetch_json(
    client: httpx.AsyncClient,
    url: str,
) -> Optional[dict]:
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
    """Search public product databases before using web research."""
    headers = {
        "User-Agent": "BarcodeProductLookup/2.0 (product research application)"
    }

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
        timeout=12.0,
        headers=headers,
        follow_redirects=True,
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

        # Only accept the exact barcode returned by the database.
        if clean_barcode(str(product.get("code") or "")) != barcode:
            continue

        records.append({
            "source": source_name,
            "barcode": barcode,
            "product_name": product.get("product_name"),
            "brand": product.get("brands"),
            "category": product.get("categories"),
            "net_weight": product.get("quantity"),
            "ingredients": product.get("ingredients_text"),
            "nutritional_info": product.get("nutriments"),
            "allergens": product.get("allergens"),
            "manufacturer": product.get("manufacturing_places"),
            "country_of_origin": product.get("origins"),
            "instructions": product.get("preparation"),
            "storage_instructions": (
                product.get("conservation")
                or product.get("storage_conditions")
            ),
            "certifications": product.get("labels"),
            "image_url": product.get("image_front_url") or product.get("image_url"),
            "product_url": product_url,
        })

    return records


def extract_json(text: str) -> dict:
    """Parse a JSON object from the model response."""
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
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
    """Extract web URLs returned by Gemini Search grounding."""
    found_urls = []

    try:
        for candidate in response.candidates or []:
            metadata = getattr(candidate, "grounding_metadata", None)
            if not metadata:
                continue

            for chunk in getattr(metadata, "grounding_chunks", None) or []:
                web_item = getattr(chunk, "web", None)
                uri = getattr(web_item, "uri", None) if web_item else None

                if uri and uri.startswith(("https://", "http://")):
                    found_urls.append(uri)
    except Exception:
        logger.exception("Could not extract Gemini grounding sources.")

    return list(dict.fromkeys(found_urls))


def parse_mrp(value: Any) -> Optional[float]:
    """Accept a numeric MRP or a clearly formatted currency value."""
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        number = float(value)
        return number if 0 < number < 10_000_000 else None

    text = str(value).strip()

    # Don't interpret a range or vague phrase as an exact MRP.
    if not text or re.search(r"\b(from|starting|approx|around|between)\b", text, re.I):
        return None

    match = re.search(
        r"(?:₹|INR\s*)\s*(\d[\d,]*(?:\.\d{1,2})?)"
        r"|(\d[\d,]*(?:\.\d{1,2})?)\s*(?:INR|rupees?)\b",
        text,
        re.I,
    )

    if not match:
        return None

    raw_number = (match.group(1) or match.group(2)).replace(",", "")

    try:
        number = float(raw_number)
        return number if 0 < number < 10_000_000 else None
    except ValueError:
        return None


def has_value(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


async def research_with_google(
    barcode: str,
    database_records: list[dict],
) -> tuple[dict, list[str]]:
    """
    Search the web through Gemini when a product is unknown or important
    details (especially MRP) are missing from database records.
    """
    if not gemini_client:
        return {}, []

    prompt = f"""
You are researching a consumer product for a barcode lookup application.

Barcode to investigate: {barcode}

Existing database records, if any:
{json.dumps(database_records, ensure_ascii=False, default=str)}

Use Google Search to research this exact barcode and product.

Research goals:
- Identify the exact product, brand, variant and package size.
- Find the printed Maximum Retail Price (MRP) for the exact package.
- Find ingredients, usage instructions, manufacturer, country of origin,
  category, net quantity, expiry or shelf-life information, certifications,
  allergens and storage information when available.
- Prefer manufacturer or brand-owner sources for product specifications.
- For MRP, prefer a source that explicitly says MRP or maximum retail price.
- Distinguish MRP from a discounted selling price, offer price or marketplace price.
- Check that the pack size and product variant match the barcode.
- Use the existing database records as clues, not as proof of missing details.
- Never invent facts, source URLs, dates, or prices.
- If a field cannot be substantiated, return null for that field.
- Do not assume a product is counterfeit just because it cannot be found.

Return one JSON object only with exactly these keys:
{{
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

Rules for mrp:
- Return a number only when a source explicitly identifies the value as MRP
  or maximum retail price for the matching product/pack.
- Otherwise return null.
- In mrp_evidence, briefly describe the evidence and the matching pack size.
- Do not treat a selling price or discount price as MRP.
- Do not put source URLs into the JSON; the application separately collects
  Google Search grounding source URLs.
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

        text = response.text or ""
        logger.info("Gemini web research completed for barcode %s", barcode)

        result = extract_json(text)
        if not result:
            logger.warning("Gemini did not return parseable JSON for %s", barcode)
            logger.info("Gemini response: %s", text[:2000])

        sources = extract_grounding_sources(response)
        return result, sources

    except Exception as exc:
        logger.exception("Gemini Google Search research failed: %s", exc)
        return {}, []


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


@app.get("/")
async def root():
    return {
        "message": "Product Barcode Lookup API is running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gemini_configured": gemini_client is not None,
        "model": GEMINI_MODEL,
    }


@app.post("/api/product", response_model=ProductInfo)
async def get_product(request: BarcodeRequest):
    barcode = clean_barcode(request.barcode)

    if not is_valid_barcode(barcode):
        raise HTTPException(
            status_code=400,
            detail="Invalid barcode format or check digit.",
        )

    try:
        # Step 1: Search databases first.
        records = await lookup_product_databases(barcode)
    except Exception as exc:
        logger.exception("Database lookup failed: %s", exc)
        records = []

    logger.info(
        "Barcode %s: found %d exact database record(s)",
        barcode,
        len(records),
    )

    # Step 2: Search the web if the product is unknown OR MRP/important
    # information is missing. This also gives known products an MRP fallback.
    has_database_product = bool(records)

    database_name = next(
        (r.get("product_name") for r in records if has_value(r.get("product_name"))),
        None,
    )
    database_brand = next(
        (r.get("brand") for r in records if has_value(r.get("brand"))),
        None,
    )

    # Public product databases commonly omit MRP, so research it even when
    # the basic product identity was found.
    needs_web_research = (
        not has_database_product
        or not has_value(database_name)
        or not has_value(database_brand)
        or not any(has_value(r.get("ingredients")) for r in records)
        or True  # Always try to find MRP and other missing details.
    )

    research = {}
    web_sources = []

    if needs_web_research:
        research, web_sources = await research_with_google(barcode, records)

    # Prefer database information, using grounded web research to fill gaps.
    def database_value(key: str):
        for record in records:
            value = record.get(key)
            if has_value(value):
                return value
        return None

    product_name = first_value(
        database_value("product_name"),
        research.get("product_name"),
    )

    brand = first_value(
        database_value("brand"),
        research.get("brand"),
    )

    category = first_value(
        database_value("category"),
        research.get("category"),
    )

    mrp = parse_mrp(research.get("mrp"))

    # These public databases do not reliably provide printed MRP.
    # Only use a price when the web research returns an explicit MRP value.
    ingredients = first_value(
        database_value("ingredients"),
        research.get("ingredients"),
    )

    nutritional_info = first_value(
        database_value("nutritional_info"),
        research.get("nutritional_info"),
    )

    best_before = research.get("best_before")

    instructions = first_value(
        database_value("instructions"),
        research.get("instructions"),
    )

    manufacturer = first_value(
        database_value("manufacturer"),
        research.get("manufacturer"),
    )

    country_of_origin = first_value(
        database_value("country_of_origin"),
        research.get("country_of_origin"),
    )

    net_weight = first_value(
        database_value("net_weight"),
        research.get("net_weight"),
    )

    allergens = first_value(
        database_value("allergens"),
        research.get("allergens"),
    )

    storage_instructions = first_value(
        database_value("storage_instructions"),
        research.get("storage_instructions"),
    )

    certifications = first_value(
        database_value("certifications"),
        research.get("certifications"),
    )

    research_notes = research.get("additional_info")
    mrp_evidence = research.get("mrp_evidence")

    notes = []

    if has_database_product:
        notes.append("Product information was checked against public product databases.")
    else:
        notes.append("No exact record was found in the supported product databases.")

    if has_value(research):
        notes.append("Gemini Google Search research was attempted to identify the product and fill missing details.")

    if mrp is not None:
        notes.append(
            "An MRP candidate was found through web research. "
            "Check the cited source and the exact package label before relying on it."
        )
        if has_value(mrp_evidence):
            notes.append(f"MRP evidence reported by research: {mrp_evidence}")
    else:
        notes.append(
            "No adequately supported printed MRP was found. "
            "A retailer's selling price is not necessarily the MRP."
        )

    if has_value(research_notes):
        notes.append(str(research_notes))

    sources = []
    for record in records:
        if record.get("product_url"):
            sources.append(record["product_url"])
    sources.extend(web_sources)
    sources = list(dict.fromkeys(sources))

    found = bool(product_name or brand)

    if has_database_product and has_value(research):
        verification_status = "database_and_web_researched"
    elif has_database_product:
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
        ingredients=text_value(ingredients),
        nutritional_info=nutritional_info,
        best_before=text_value(best_before),
        instructions=text_value(instructions),
        manufacturer=text_value(manufacturer),
        country_of_origin=text_value(country_of_origin),
        net_weight=text_value(net_weight),
        allergens=text_value(allergens),
        storage_instructions=text_value(storage_instructions),
        certifications=text_value(certifications),
        additional_info=" ".join(notes),
        found=found,
        sources=sources,
        verification_status=verification_status,
        raw_response=json.dumps(
            {
                "database_records": records,
                "web_research": research,
                "web_sources": web_sources,
            },
            ensure_ascii=False,
            default=str,
        ),
    )

    logger.info(
        "Lookup finished for %s: found=%s, mrp=%s, status=%s",
        barcode,
        response_data.found,
        response_data.mrp,
        response_data.verification_status,
    )

    return response_data
