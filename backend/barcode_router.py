"""
barcode_router.py — Barcode lookup with validation.

Flow:
1. Validate barcode format
2. Check local catalog (Excel files) — confirmed product identity
3. If found in catalog → ask Gemini to enrich with ingredients/usage/shelf life by product name
4. If not in catalog → ask Gemini + cross-check Open Food Facts / UPCitemdb
5. Always return something
"""

import asyncio
import logging
import os
import re
from typing import Optional, List

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from catalog import load_catalog, lookup
from gemini_barcode import call_gemini

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Barcode Scanner"])

_CATALOG_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG = load_catalog(_CATALOG_DIR)

# Generic/meaningless values Gemini returns when it doesn't actually know the product
_GENERIC_NAMES = {
    "consumer packaged good", "consumer packaged goods", "general merchandise",
    "product", "unknown product", "unknown", "n/a", "na", "not available",
    "packaged food", "food product", "grocery item", "consumer product",
}


# ── Barcode validation ────────────────────────────────────────────────────────

def validate_barcode(barcode: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message). Validates format only, not checksum."""
    if not barcode.isdigit():
        return False, "Barcode must contain only digits."
    if len(barcode) not in (8, 12, 13, 14):
        return False, f"Invalid barcode length {len(barcode)}. Expected 8, 12, 13, or 14 digits."
    return True, ""


def normalize_barcode(value: str) -> str:
    barcode = str(value).strip()
    if re.fullmatch(r"\d+\.0", barcode):
        barcode = barcode[:-2]
    return re.sub(r"[\s\-]", "", barcode)


# ── Models ────────────────────────────────────────────────────────────────────

class BarcodeRequest(BaseModel):
    barcode: str
    country_context: Optional[str] = "India"


class ProductResponse(BaseModel):
    barcode: str
    product_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    mrp: Optional[str] = None
    net_weight: Optional[str] = None
    ingredients: Optional[str] = None
    nutritional_info: Optional[str] = None
    allergens: Optional[str] = None
    manufacturer: Optional[str] = None
    country_of_origin: Optional[str] = None
    storage_instructions: Optional[str] = None
    certifications: Optional[str] = None
    additional_info: Optional[str] = None
    found: bool = False
    sources: List[str] = Field(default_factory=list)
    verification_status: str = "not_found"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _str(val) -> Optional[str]:
    """Normalize Gemini fields — convert lists to comma-separated strings."""
    if val is None:
        return None
    if isinstance(val, list):
        return ", ".join(str(v) for v in val if v)
    s = str(val).strip()
    return s if s and s.lower() not in ("null", "none", "n/a", "na") else None


def _is_generic_response(result: dict) -> bool:
    """Return True if Gemini response looks like a generic non-answer."""
    name = (result.get("product_name") or "").strip().lower()
    brand = (result.get("brand") or "").strip().lower()
    if name in _GENERIC_NAMES:
        return True
    if brand in ("unknown", "n/a", "na", ""):
        if not name or name in _GENERIC_NAMES:
            return True
    return False


def _build_response(barcode: str, data: dict, sources: List[str], status: str) -> ProductResponse:
    return ProductResponse(
        barcode=barcode,
        product_name=_str(data.get("product_name")),
        brand=_str(data.get("brand")),
        category=_str(data.get("category")),
        mrp=_str(data.get("mrp")),
        net_weight=_str(data.get("net_weight")),
        ingredients=_str(data.get("ingredients")),
        nutritional_info=_str(data.get("nutritional_info")),
        allergens=_str(data.get("allergens")),
        manufacturer=_str(data.get("manufacturer")),
        country_of_origin=_str(data.get("country_of_origin")),
        storage_instructions=_str(data.get("storage_instructions")),
        certifications=_str(data.get("certifications")),
        additional_info=_str(data.get("additional_info")),
        found=bool(data.get("product_name") or data.get("brand")),
        sources=sources,
        verification_status=status,
    )


# ── External cross-check sources ──────────────────────────────────────────────

_OFF_URLS = [
    "https://world.openfoodfacts.org/api/v2/product/{barcode}.json",
    "https://in.openfoodfacts.org/api/v2/product/{barcode}.json",
    "https://world.openbeautyfacts.org/api/v2/product/{barcode}.json",
    "https://world.openproductsfacts.org/api/v2/product/{barcode}.json",
]


async def _lookup_open_facts(barcode: str) -> dict | None:
    timeout = httpx.Timeout(6.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout) as http:
        results = await asyncio.gather(
            *[http.get(u.format(barcode=barcode)) for u in _OFF_URLS],
            return_exceptions=True,
        )
    for r in results:
        if isinstance(r, Exception):
            continue
        try:
            if r.status_code != 200:
                continue
            data = r.json()
            p = data.get("product") or {}
            if data.get("status") == 1 and (p.get("product_name") or p.get("brands")):
                return {
                    "product_name": p.get("product_name_en") or p.get("product_name"),
                    "brand": p.get("brands"),
                    "category": (p.get("categories") or "").split(",")[0].strip() or None,
                    "net_weight": p.get("quantity"),
                    "ingredients": p.get("ingredients_text_en") or p.get("ingredients_text"),
                    "allergens": p.get("allergens"),
                    "manufacturer": p.get("manufacturing_places"),
                    "country_of_origin": p.get("origins") or p.get("countries"),
                    "certifications": p.get("labels"),
                }
        except Exception:
            pass
    return None


async def _lookup_upcitemdb(barcode: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=6.0) as http:
            r = await http.get(
                "https://api.upcitemdb.com/prod/trial/lookup",
                params={"upc": barcode},
                headers={"Accept": "application/json"},
            )
            if r.status_code != 200:
                return None
            items = r.json().get("items") or []
            if not items:
                return None
            item = items[0]
            if not item.get("title") and not item.get("brand"):
                return None
            return {
                "product_name": item.get("title"),
                "brand": item.get("brand"),
                "category": item.get("category"),
                "net_weight": item.get("size") or item.get("weight"),
                "ingredients": item.get("ingredients"),
                "manufacturer": item.get("brand"),
            }
    except Exception:
        logger.debug("UPCitemdb lookup failed.", exc_info=True)
    return None


async def _search_upcitemdb(query: str) -> dict | None:
    """Keyword search on UPCitemdb — works for Indian brand names."""
    try:
        async with httpx.AsyncClient(timeout=6.0) as http:
            r = await http.get(
                "https://api.upcitemdb.com/prod/trial/search",
                params={"s": query, "type": "product"},
                headers={"Accept": "application/json"},
            )
            if r.status_code != 200:
                return None
            items = r.json().get("items") or []
            if not items:
                return None
            item = items[0]
            if not item.get("title") and not item.get("brand"):
                return None
            return {
                "product_name": item.get("title"),
                "brand": item.get("brand"),
                "category": item.get("category"),
                "net_weight": item.get("size") or item.get("weight"),
                "ingredients": item.get("ingredients"),
                "manufacturer": item.get("brand"),
            }
    except Exception:
        logger.debug("UPCitemdb search failed.", exc_info=True)
    return None


async def _lookup_barcode_lookup_api(barcode: str) -> dict | None:
    import os
    api_key = os.getenv("BARCODE_LOOKUP_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=6.0) as http:
            r = await http.get(
                "https://api.barcodelookup.com/v3/products",
                params={"barcode": barcode, "key": api_key},
            )
            if r.status_code != 200:
                return None
            products = r.json().get("products") or []
            if not products:
                return None
            p = products[0]
            stores = p.get("stores") or []
            mrp = str(stores[0].get("price")) if stores and stores[0].get("price") else None
            return {
                "product_name": p.get("product_name") or p.get("title"),
                "brand": p.get("brand"),
                "category": p.get("category"),
                "net_weight": p.get("size"),
                "ingredients": p.get("ingredients"),
                "manufacturer": p.get("manufacturer") or p.get("brand"),
                "country_of_origin": p.get("country_of_origin_name"),
                "mrp": mrp,
                "certifications": ", ".join(p.get("certifications") or []) or None,
            }
    except Exception:
        logger.debug("Barcode Lookup API failed.", exc_info=True)
    return None


def _merge(gemini: dict, external: dict) -> dict:
    """Fill Gemini blanks with external data, prefer external for key fields."""
    merged = dict(gemini)
    for key in ("product_name", "brand", "category", "net_weight",
                "ingredients", "allergens", "manufacturer", "country_of_origin",
                "certifications", "mrp"):
        ext_val = external.get(key)
        if ext_val and not merged.get(key):
            merged[key] = ext_val
    return merged


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/product", response_model=ProductResponse)
async def get_product(request: BarcodeRequest):
    barcode = normalize_barcode(request.barcode)
    if not barcode:
        raise HTTPException(status_code=400, detail="Barcode cannot be empty.")

    valid, err = validate_barcode(barcode)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    logger.info("Barcode lookup: %s", barcode)

    # 1. Local catalog lookup (Excel files — confirmed identity)
    catalog_entry = lookup(CATALOG, barcode)

    if catalog_entry and (catalog_entry.get("product_name") or catalog_entry.get("brand")):
        product_name = catalog_entry.get("product_name") or ""
        brand = catalog_entry.get("brand") or ""
        logger.info("Barcode %s found in catalog: %s %s", barcode, brand, product_name)

        # Ask Gemini to enrich with details not in catalog (ingredients, usage, shelf life etc.)
        search_label = f"{brand} {product_name}".strip()
        enrich_prompt = (
            f"Provide detailed product information for '{search_label}' "
            f"which is an Indian consumer product (barcode: {barcode}).\n"
            f"Return JSON with: found (bool), product_name, brand, category, mrp, net_weight, "
            f"ingredients, nutritional_info, allergens, manufacturer, country_of_origin, "
            f"storage_instructions, certifications, additional_info.\n"
            f"Focus especially on: ingredients with quantities, usage instructions, shelf life, "
            f"allergens, nutritional info. Set found=true."
        )
        try:
            enriched = await asyncio.to_thread(
                call_gemini,
                contents=enrich_prompt,
                system_prompt=(
                    "You are a product information assistant with detailed knowledge of Indian "
                    "consumer products. Provide accurate ingredients, usage instructions, shelf life, "
                    "and nutritional information for the named product."
                ),
                temperature=0.1,
            )
        except Exception as exc:
            logger.warning("Gemini enrichment failed: %s", exc)
            enriched = {}

        # Merge: catalog data takes priority for identity fields, Gemini fills details
        merged = {
            "product_name":      catalog_entry.get("product_name") or _str(enriched.get("product_name")),
            "brand":             catalog_entry.get("brand") or _str(enriched.get("brand")),
            "category":          catalog_entry.get("category") or _str(enriched.get("category")),
            "sub_category":      catalog_entry.get("sub_category"),
            "net_weight":        catalog_entry.get("net_weight") or _str(enriched.get("net_weight")),
            "mrp":               catalog_entry.get("mrp") or _str(enriched.get("mrp")),
            "country_of_origin": catalog_entry.get("country_of_origin") or _str(enriched.get("country_of_origin")),
            "ingredients":       catalog_entry.get("ingredients") or _str(enriched.get("ingredients")),
            "nutritional_info":  _str(enriched.get("nutritional_info")),
            "allergens":         _str(enriched.get("allergens")),
            "manufacturer":      _str(enriched.get("manufacturer")),
            "storage_instructions": _str(enriched.get("storage_instructions")),
            "certifications":    _str(enriched.get("certifications")),
            "additional_info":   _str(enriched.get("additional_info")),
        }
        cat_str = merged["category"]
        sub = merged.get("sub_category")
        if cat_str and sub:
            cat_str = f"{cat_str} — {sub}"
        return ProductResponse(
            barcode=barcode,
            product_name=merged["product_name"],
            brand=merged["brand"],
            category=cat_str,
            mrp=merged["mrp"],
            net_weight=merged["net_weight"],
            ingredients=merged["ingredients"],
            nutritional_info=merged["nutritional_info"],
            allergens=merged["allergens"],
            manufacturer=merged["manufacturer"],
            country_of_origin=merged["country_of_origin"],
            storage_instructions=merged["storage_instructions"],
            certifications=merged["certifications"],
            additional_info=merged["additional_info"],
            found=True,
            sources=["Local Catalog", "Gemini AI"],
            verification_status="verified",
        )

    # 2. Not in catalog — ask Gemini + cross-check external sources
    logger.info("Barcode %s not in catalog, trying external sources.", barcode)

    gemini_task = asyncio.to_thread(
        call_gemini,
        contents=(
            f"What product has barcode {barcode}? "
            f"This is likely an Indian product (country context: {request.country_context}). "
            f"Return a JSON object with: found (bool), product_name, brand, category, mrp, net_weight, "
            f"ingredients, nutritional_info, allergens, manufacturer, country_of_origin, "
            f"storage_instructions, certifications, additional_info. "
            f"Fill every field you can. Set found=true."
        ),
        system_prompt=(
            "You are a product information assistant with broad knowledge of Indian and global "
            "consumer products. When given a barcode, provide all product details you know. "
            "Always return found=true and fill every field you can."
        ),
        temperature=0.2,
    )

    gemini_result, off_result, bcl_result = await asyncio.gather(
        gemini_task,
        _lookup_open_facts(barcode),
        _lookup_barcode_lookup_api(barcode),
        return_exceptions=True,
    )

    if isinstance(gemini_result, Exception):
        raise HTTPException(status_code=502, detail=f"Gemini error: {gemini_result}")
    if isinstance(off_result, Exception):
        off_result = None
    if isinstance(bcl_result, Exception):
        bcl_result = None

    # UPCitemdb keyword search using Gemini's identified product name
    upc_result = None
    search_query = f"{_str(gemini_result.get('brand')) or ''} {_str(gemini_result.get('product_name')) or ''}".strip()
    if search_query and search_query.lower() not in ("unknown", "n/a", ""):
        upc_result = await _search_upcitemdb(search_query)

    external = bcl_result or off_result or upc_result

    if external:
        merged = _merge(gemini_result, external)
        sources = ["Gemini AI"]
        if bcl_result:
            sources.append("Barcode Lookup API")
        if off_result:
            sources.append("Open Food Facts")
        if upc_result:
            sources.append("UPC Item DB")
        return _build_response(barcode, merged, sources, "verified")

    # No external source — return Gemini as-is
    return _build_response(barcode, gemini_result, ["Gemini AI"], "gemini_unverified")

