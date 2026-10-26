"""
catalog.py — loads all Excel files into a barcode-keyed dict at startup.
Used as the ground-truth confirmer for Gemini responses.
"""

import glob
import logging
import os
import openpyxl

logger = logging.getLogger(__name__)

# Column indices (0-based) matching the header row
COL_BARCODE     = 1   # EAN-13 Barcode
COL_NAME        = 2   # Product Name
COL_BRAND       = 3   # Brand
COL_CATEGORY    = 4   # Category
COL_SUBCATEGORY = 5   # Sub-Category
COL_WEIGHT      = 6   # Net Weight / Volume
COL_MRP         = 7   # MRP (₹)
COL_COUNTRY     = 8   # Country of Origin
COL_GS1         = 9   # GS1 Prefix
COL_INGREDIENTS = 10  # Primary Ingredients / Description

HEADER_ROW = 3  # 0-based index — row 4 in Excel (rows 1-3 are title/blank)


def _load_file(path: str, catalog: dict) -> int:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    count = 0
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i <= HEADER_ROW:
            continue
        if not row or row[COL_BARCODE] is None:
            continue
        barcode = str(row[COL_BARCODE]).strip()
        if not barcode or barcode == "EAN-13 Barcode":
            continue
        catalog[barcode] = {
            "product_name": str(row[COL_NAME]).strip() if row[COL_NAME] else None,
            "brand":        str(row[COL_BRAND]).strip() if row[COL_BRAND] else None,
            "category":     str(row[COL_CATEGORY]).strip() if row[COL_CATEGORY] else None,
            "sub_category": str(row[COL_SUBCATEGORY]).strip() if row[COL_SUBCATEGORY] else None,
            "net_weight":   str(row[COL_WEIGHT]).strip() if row[COL_WEIGHT] else None,
            "mrp":          str(row[COL_MRP]).strip() if row[COL_MRP] else None,
            "country_of_origin": str(row[COL_COUNTRY]).strip() if row[COL_COUNTRY] else None,
            "gs1_prefix":   str(row[COL_GS1]).strip() if row[COL_GS1] else None,
            "ingredients":  str(row[COL_INGREDIENTS]).strip() if row[COL_INGREDIENTS] else None,
        }
        count += 1
    wb.close()
    return count


def load_catalog(folder: str = "backend") -> dict:
    catalog: dict = {}
    files = sorted(glob.glob(os.path.join(folder, "*.xlsx")))
    for path in files:
        try:
            n = _load_file(path, catalog)
            logger.info("Loaded %d entries from %s", n, os.path.basename(path))
        except Exception as e:
            logger.error("Failed to load %s: %s", path, e)
    logger.info("Catalog ready — %d total barcodes", len(catalog))
    return catalog


def lookup(catalog: dict, barcode: str) -> dict | None:
    """Return catalog entry for barcode, or None if not found."""
    return catalog.get(barcode)


def _normalize(s: str | None) -> str:
    """Lowercase, strip punctuation for fuzzy comparison."""
    if not s:
        return ""
    return s.lower().strip().replace(".", "").replace(",", "").replace("-", " ")


def confirm(catalog_entry: dict, gemini_data: dict) -> tuple[bool, str]:
    """
    Compare Gemini response against catalog entry.
    Returns (matches: bool, reason: str).
    Matches if product_name OR brand are reasonably close.
    """
    cat_name  = _normalize(catalog_entry.get("product_name"))
    cat_brand = _normalize(catalog_entry.get("brand"))
    gem_name  = _normalize(gemini_data.get("product_name"))
    gem_brand = _normalize(gemini_data.get("brand"))

    # Brand match — exact or one contains the other
    brand_ok = bool(
        cat_brand and gem_brand and (
            cat_brand == gem_brand or
            cat_brand in gem_brand or
            gem_brand in cat_brand
        )
    )

    # Name match — at least 2 words overlap
    cat_words = set(cat_name.split())
    gem_words = set(gem_name.split())
    shared    = cat_words & gem_words
    name_ok   = len(shared) >= 2

    if brand_ok and name_ok:
        return True, "brand and name match"
    if brand_ok:
        return True, "brand match"
    if name_ok:
        return True, "name match"

    return False, f"mismatch (catalog: '{catalog_entry.get('product_name')} / {catalog_entry.get('brand')}', gemini: '{gemini_data.get('product_name')} / {gemini_data.get('brand')}')"
