    """
    barcode_router.py — Barcode / product lookup feature.
    Routes: POST /api/product
    """

    import re
    import logging
    import asyncio
    import os

    import httpx
    from fastapi import APIRouter
    from pydantic import BaseModel, Field

    from catalog import load_catalog, lookup, confirm
    from gemini_client import call_gemini

    logger = logging.getLogger(__name__)

    router = APIRouter()

    # Resolve catalog folder relative to this file so it works regardless of cwd
    _CATALOG_DIR = os.path.join(os.path.dirname(__file__))

    # Load Excel catalog once at import time — used as ground-truth confirmer
    CATALOG = load_catalog(_CATALOG_DIR)


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


    # ── Gemini prompt ─────────────────────────────────────────────────────────────

    _BARCODE_PROMPT = """You are a barcode lookup assistant for Indian FMCG products.

    IMPORTANT RULES:
    - Only return product details if you are CERTAIN about this exact barcode number.
    - Barcodes are unique identifiers — do NOT guess or infer based on brand/category patterns.
    - If you are not 100% sure about this specific barcode, set found to false and all other fields to null.
    - Do NOT hallucinate product names, brands, or details for barcodes you don't recognise.

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

    # Relaxed fallback prompt — used only when all other sources fail
    _BARCODE_PROMPT_RELAXED = """You are an Indian FMCG product expert. A barcode was scanned but not found in any database.

    Use your best knowledge to identify this product. Indian barcodes starting with 890 are GS1 India registered.
    Decode what you can from the barcode prefix (manufacturer/company) even if you don't know the exact SKU.

    Be honest about confidence. If you can identify the brand or manufacturer from the prefix, say so.
    If you truly have no information, set found to false.

    Respond ONLY with a valid JSON object with these fields:
    - product_name: product name if known, otherwise null
    - brand: brand name if known or inferable from prefix, otherwise null
    - category: category if known, otherwise null
    - mrp: MRP if known, otherwise null
    - net_weight: weight/volume if known, otherwise null
    - ingredients: ingredients if known, otherwise null
    - nutritional_info: nutritional facts if known, otherwise null
    - allergens: allergens if known, otherwise null
    - manufacturer: manufacturer name if known or inferable, otherwise null
    - country_of_origin: country (for 890 prefix always "India")
    - storage_instructions: null unless known
    - certifications: null unless known
    - additional_info: any useful information about the barcode prefix or likely product range
    - found: true if you can provide at least product name or brand with reasonable confidence"""


    # ── Helpers ───────────────────────────────────────────────────────────────────

    def _from_catalog(entry: dict, barcode: str, extra: dict | None = None) -> ProductResponse:
        """Build ProductResponse from catalog entry, optionally enriched with Gemini extras."""
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


    _OPEN_FACTS_URLS = [
        "https://world.openfoodfacts.org/api/v2/product/{barcode}.json",
        "https://in.openfoodfacts.org/api/v2/product/{barcode}.json",
        "https://world.openbeautyfacts.org/api/v2/product/{barcode}.json",
        "https://world.openproductsfacts.org/api/v2/product/{barcode}.json",
        "https://world.openpetfoodfacts.org/api/v2/product/{barcode}.json",
    ]


    async def _lookup_open_facts(barcode: str) -> dict | None:
        async with httpx.AsyncClient(timeout=8) as http:
            tasks = [http.get(url.format(barcode=barcode)) for url in _OPEN_FACTS_URLS]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    continue
                try:
                    data = r.json()
                    if data.get("status") == 1:
                        p = data.get("product", {})
                        if p.get("product_name") or p.get("product_name_en") or p.get("brands"):
                            return p
                except Exception:
                    continue
        return None


    async def _lookup_upcitemdb(barcode: str) -> dict | None:
        """upcitemdb.com — free tier, no key needed, 100 lookups/day."""
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                r = await http.get(
                    f"https://api.upcitemdb.com/prod/trial/lookup",
                    params={"upc": barcode},
                    headers={"Accept": "application/json"},
                )
                data = r.json()
                items = data.get("items", [])
                if items:
                    item = items[0]
                    return {
                        "product_name": item.get("title"),
                        "brand":        item.get("brand"),
                        "category":     item.get("category"),
                        "net_weight":   item.get("size") or item.get("weight"),
                        "ingredients":  item.get("ingredients"),
                        "description":  item.get("description"),
                        "manufacturer": item.get("brand"),
                        "country_of_origin": None,
                    }
        except Exception as e:
            logger.warning("upcitemdb lookup failed: %s", e)
        return None


    # ── Route ─────────────────────────────────────────────────────────────────────

    @router.post("/product", response_model=ProductResponse)
    async def get_product(request: ProductRequest):
        barcode = re.sub(r"[\s\-]", "", request.barcode.strip())
        logger.info("Barcode lookup: %s", barcode)

        # 1. Ask Gemini
        gemini_data = call_gemini(f"Barcode: {barcode}", _BARCODE_PROMPT, temperature=0.1)
        gemini_found = bool(
            gemini_data.get("found") is True and
            (gemini_data.get("product_name") or gemini_data.get("brand"))
        )

        # 2. Check catalog (ground truth)
        catalog_entry = lookup(CATALOG, barcode)

        if catalog_entry:
            matched, reason = confirm(catalog_entry, gemini_data)
            if matched:
                logger.info("Catalog CONFIRMED Gemini for %s (%s)", barcode, reason)
                return _from_catalog(catalog_entry, barcode, extra=gemini_data)
            else:
                logger.warning("Catalog OVERRIDING Gemini for %s (%s)", barcode, reason)
                return _from_catalog(catalog_entry, barcode, extra=None)

        # 3. Not in catalog — use Gemini if it's confident
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

        # 4. Open Food Facts (all databases in parallel)
        off_product = await _lookup_open_facts(barcode)
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

        # 5. upcitemdb.com free API
        upc_product = await _lookup_upcitemdb(barcode)
        if upc_product and (upc_product.get("product_name") or upc_product.get("brand")):
            logger.info("Found via upcitemdb: %s", barcode)
            return ProductResponse(
                barcode=barcode,
                product_name=upc_product.get("product_name"),
                brand=upc_product.get("brand"),
                category=upc_product.get("category"),
                net_weight=upc_product.get("net_weight"),
                ingredients=upc_product.get("ingredients"),
                manufacturer=upc_product.get("manufacturer"),
                additional_info=upc_product.get("description"),
                found=True,
                sources=["UPC Item DB"],
                verification_status="found_via_database",
            )

        # 5. Relaxed Gemini fallback — extract what can be inferred from barcode prefix
        logger.info("Trying relaxed Gemini fallback for %s", barcode)
        relaxed_data = call_gemini(f"Barcode: {barcode}", _BARCODE_PROMPT_RELAXED, temperature=0.2)
        relaxed_found = bool(
            relaxed_data.get("found") is True and
            (relaxed_data.get("product_name") or relaxed_data.get("brand") or relaxed_data.get("manufacturer"))
        )

        if relaxed_found:
            logger.info("Relaxed Gemini found partial info for %s", barcode)
            return ProductResponse(
                barcode=barcode,
                product_name=relaxed_data.get("product_name"),
                brand=relaxed_data.get("brand"),
                category=relaxed_data.get("category"),
                mrp=relaxed_data.get("mrp"),
                net_weight=relaxed_data.get("net_weight"),
                ingredients=relaxed_data.get("ingredients"),
                nutritional_info=relaxed_data.get("nutritional_info"),
                allergens=relaxed_data.get("allergens"),
                manufacturer=relaxed_data.get("manufacturer"),
                country_of_origin=relaxed_data.get("country_of_origin"),
                storage_instructions=relaxed_data.get("storage_instructions"),
                certifications=relaxed_data.get("certifications"),
                additional_info=relaxed_data.get("additional_info"),
                found=True,
                sources=["Google Gemini AI (partial)"],
                verification_status="found_via_ai",
            )

        return ProductResponse(barcode=barcode, found=False, verification_status="not_found")
