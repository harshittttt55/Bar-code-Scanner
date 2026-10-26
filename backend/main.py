import os
import re
import json
import logging
import asyncio
import time

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from catalog import load_catalog, lookup, confirm

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("Gemini client ready — model: %s", GEMINI_MODEL)
else:
    logger.warning("GEMINI_API_KEY not set.")

# Load Excel catalog at startup — used as ground truth confirmer
CATALOG = load_catalog("backend")

app = FastAPI(title="Barcode Lookup API — Gemini + Catalog")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────

class ProductRequest(BaseModel):
    barcode: str = Field(..., min_length=1, max_length=50)


class ProductResponse(BaseModel):
    barcode: str
    product_name: str | None = None
    brand: str | None = None
    category: str | None = None
    mrp: str | None = None
    net_weight: str | None = None
    ingredients: str | None = None
    nutritional_info: str | None = None
    allergens: str | None = None
    manufacturer: str | None = None
    country_of_origin: str | None = None
    storage_instructions: str | None = None
    certifications: str | None = None
    additional_info: str | None = None
    found: bool = False
    sources: list[str] = []
    verification_status: str = "not_found"


# ── Catalog-based response builder ────────────────────────────────────────────

def from_catalog(entry: dict, barcode: str, extra: dict | None = None) -> ProductResponse:
    """Build a ProductResponse from a catalog entry.
    Optionally merge extra fields (e.g. nutritional_info, allergens) from Gemini
    when Gemini was confirmed correct.
    """
    mrp_raw = entry.get("mrp")
    mrp = f"₹{mrp_raw}" if mrp_raw and not str(mrp_raw).startswith("₹") else mrp_raw

    cat = entry.get("category") or ""
    sub = entry.get("sub_category") or ""
    category_str = f"{cat} — {sub}" if cat and sub else (cat or sub or None)

    return ProductResponse(
        barcode=barcode,
        product_name=entry.get("product_name"),
        brand=entry.get("brand"),
        category=category_str,
        mrp=mrp,
        net_weight=entry.get("net_weight"),
        ingredients=entry.get("ingredients"),
        nutritional_info=extra.get("nutritional_info") if extra else None,
        allergens=extra.get("allergens") if extra else None,
        manufacturer=extra.get("manufacturer") if extra else None,
        country_of_origin=entry.get("country_of_origin"),
        storage_instructions=extra.get("storage_instructions") if extra else None,
        certifications=extra.get("certifications") if extra else None,
        additional_info=extra.get("additional_info") if extra else None,
        found=True,
        sources=["FMCG Catalog (verified)"],
        verification_status="confirmed_via_catalog",
    )


# ── Open Food Facts fallback ──────────────────────────────────────────────────

OPEN_FACTS_URLS = [
    "https://in.openfoodfacts.org/api/v2/product/{barcode}.json",
    "https://world.openfoodfacts.org/api/v2/product/{barcode}.json",
]

async def lookup_open_facts(barcode: str) -> dict | None:
    async with httpx.AsyncClient(timeout=6) as http:
        tasks = [http.get(url.format(barcode=barcode)) for url in OPEN_FACTS_URLS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                continue
            try:
                data = r.json()
                if data.get("status") == 1:
                    return data.get("product", {})
            except Exception:
                continue
    return None


# ── Gemini lookup (with retry + model fallback) ───────────────────────────────

SYSTEM_PROMPT = """You are a barcode lookup assistant for Indian FMCG products.

IMPORTANT RULES:
- Only return product details if you are CERTAIN about this exact barcode number
- Barcodes are unique identifiers — do NOT guess or infer based on brand/category patterns
- If you are not 100% sure about this specific barcode, set found to false and all other fields to null
- Do NOT hallucinate product names, brands, or details for barcodes you don't recognise

Respond ONLY with a valid JSON object with these fields:
- product_name: exact product name (string or null)
- brand: brand name (string or null)
- category: product category (string or null)
- mrp: Indian MRP e.g. "Rs.10" (string or null)
- net_weight: weight/volume e.g. "70g" (string or null)
- ingredients: ingredient list (string or null)
- nutritional_info: key nutritional facts (string or null)
- allergens: allergen warnings (string or null)
- manufacturer: manufacturer name (string or null)
- country_of_origin: country (string or null)
- storage_instructions: storage info (string or null)
- certifications: FSSAI, ISO etc. (string or null)
- additional_info: other relevant detail (string or null)
- found: true ONLY if you are certain about this exact barcode, otherwise false"""


def ask_gemini(barcode: str) -> dict:
    if not client:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured.")

    models_to_try = [GEMINI_MODEL]
    if GEMINI_MODEL != "gemini-2.5-flash":
        models_to_try.append("gemini-2.5-flash")

    for model in models_to_try:
        for attempt in range(2):  # max 2 attempts per model
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=f"Barcode: {barcode}",
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                text = response.text.strip()
                text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
                text = re.sub(r"\s*```$", "", text)
                data = json.loads(text)
                logger.info("Gemini success — model: %s, barcode: %s | name=%s | brand=%s | found=%s",
                            model, barcode, data.get("product_name"), data.get("brand"), data.get("found"))
                return data
            except json.JSONDecodeError as e:
                logger.error("Gemini JSON parse error: %s", e)
                raise HTTPException(status_code=500, detail="Gemini returned malformed JSON.")
            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    logger.warning("Model %s unavailable (attempt %d/2), trying next...", model, attempt + 1)
                    break  # immediately try next model, no sleep
                else:
                    logger.error("Gemini API error: %s", e)
                    raise HTTPException(status_code=502, detail=f"Gemini API error: {e}")

    # All models failed — return empty rather than hang
    logger.warning("All Gemini models unavailable for barcode %s", barcode)
    return {"found": False}


# ── Main endpoint ─────────────────────────────────────────────────────────────

@app.post("/api/product", response_model=ProductResponse)
async def get_product(request: ProductRequest):
    barcode = re.sub(r"[\s\-]", "", request.barcode.strip())
    logger.info("Barcode lookup: %s", barcode)

    # ── Step 1: Ask Gemini ────────────────────────────────────────────────────
    gemini_data = ask_gemini(barcode)
    gemini_found = bool(
        gemini_data.get("found") is True and
        (gemini_data.get("product_name") or gemini_data.get("brand"))
    )

    # ── Step 2: Check catalog (ground truth) ─────────────────────────────────
    catalog_entry = lookup(CATALOG, barcode)

    if catalog_entry:
        matched, reason = confirm(catalog_entry, gemini_data)
        if matched:
            # Gemini confirmed — use catalog data as base, enrich with Gemini extras
            logger.info("Catalog CONFIRMED Gemini for %s (%s)", barcode, reason)
            return from_catalog(catalog_entry, barcode, extra=gemini_data)
        else:
            # Gemini was wrong — use catalog data only
            logger.warning("Catalog OVERRIDING Gemini for %s (%s)", barcode, reason)
            return from_catalog(catalog_entry, barcode, extra=None)

    # ── Step 3: Not in catalog — use Gemini as-is (or Open Food Facts) ───────
    logger.info("Barcode %s not in catalog, using Gemini/OFF", barcode)

    if gemini_found:
        return ProductResponse(
            barcode=barcode,
            product_name=gemini_data.get("product_name"),
            brand=gemini_data.get("brand"),
            category=gemini_data.get("category"),
            mrp=gemini_data.get("mrp"),
            net_weight=gemini_data.get("net_weight"),
            ingredients=gemini_data.get("ingredients"),
            nutritional_info=gemini_data.get("nutritional_info"),
            allergens=gemini_data.get("allergens"),
            manufacturer=gemini_data.get("manufacturer"),
            country_of_origin=gemini_data.get("country_of_origin"),
            storage_instructions=gemini_data.get("storage_instructions"),
            certifications=gemini_data.get("certifications"),
            additional_info=gemini_data.get("additional_info"),
            found=True,
            sources=["Google Gemini AI"],
            verification_status="found_via_ai",
        )

    # ── Step 4: Gemini also didn't know — try Open Food Facts ────────────────
    off_product = await lookup_open_facts(barcode)
    if off_product:
        name  = off_product.get("product_name_en") or off_product.get("product_name")
        brand = off_product.get("brands")
        if name or brand:
            return ProductResponse(
                barcode=barcode,
                product_name=name,
                brand=brand,
                category=(off_product.get("categories") or "").split(",")[0].strip() or None,
                net_weight=off_product.get("quantity"),
                ingredients=off_product.get("ingredients_text_en") or off_product.get("ingredients_text"),
                country_of_origin=off_product.get("countries"),
                certifications=off_product.get("labels"),
                found=True,
                sources=["Open Food Facts"],
                verification_status="found_via_database",
            )

    return ProductResponse(barcode=barcode, found=False, verification_status="not_found")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gemini": "configured" if client else "not configured",
        "model": GEMINI_MODEL,
        "catalog_size": len(CATALOG),
    }
