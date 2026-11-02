"""
catalog.py — loads all Excel files into a barcode-keyed dict at startup.
"""

import glob
import logging
import os
import openpyxl

logger = logging.getLogger(__name__)

# Column indices for the original 10 FMCG catalog files
COL_BARCODE     = 1
COL_NAME        = 2
COL_BRAND       = 3
COL_CATEGORY    = 4
COL_SUBCATEGORY = 5
COL_WEIGHT      = 6
COL_MRP         = 7
COL_COUNTRY     = 8
COL_GS1         = 9
COL_INGREDIENTS = 10
HEADER_ROW      = 3  # 0-based; rows 0-3 are title/blank/header

# New dedicated files — handled by separate loaders
_FMCG_DB_FILE   = "Cleaned_Indian_FMCG_Database.xlsx"
_INVENTORY_FILE = "Cleaned_Inventory_and_Previous_Catalogue_Comparison.xlsx"
_DEDICATED_FILES = {_FMCG_DB_FILE, _INVENTORY_FILE}


def _load_file(path: str, catalog: dict) -> int:
    """Original loader for the 10 FMCG catalog Excels."""
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
            "product_name":      str(row[COL_NAME]).strip() if row[COL_NAME] else None,
            "brand":             str(row[COL_BRAND]).strip() if row[COL_BRAND] else None,
            "category":          str(row[COL_CATEGORY]).strip() if row[COL_CATEGORY] else None,
            "sub_category":      str(row[COL_SUBCATEGORY]).strip() if row[COL_SUBCATEGORY] else None,
            "net_weight":        str(row[COL_WEIGHT]).strip() if row[COL_WEIGHT] else None,
            "mrp":               str(row[COL_MRP]).strip() if row[COL_MRP] else None,
            "country_of_origin": str(row[COL_COUNTRY]).strip() if row[COL_COUNTRY] else None,
            "gs1_prefix":        str(row[COL_GS1]).strip() if row[COL_GS1] else None,
            "ingredients":       str(row[COL_INGREDIENTS]).strip() if row[COL_INGREDIENTS] else None,
        }
        count += 1
    wb.close()
    return count


def _load_inventory_catalog(path: str, catalog: dict) -> int:
    """
    Loader for Cleaned_Inventory_and_Previous_Catalogue_Comparison.xlsx
    Headers: Source Excel Row, NAME, BRAND, BARCODE, ..., MRP, ..., WEIGHT, ..., CATEGORY, SUB CATEGORY
    Uses dynamic column detection to be safe against column order changes.
    Overwrites existing entries — this file has richer data (brand, category, weight).
    """
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Cleaned_Products"]

    headers = []
    for row in ws.iter_rows(max_row=1, values_only=True):
        headers = [str(h).strip().upper() if h else "" for h in row]
        break

    def col(name):
        return headers.index(name) if name in headers else None

    c_name    = col("NAME")
    c_brand   = col("BRAND")
    c_barcode = col("BARCODE")
    c_mrp     = col("MRP")
    c_weight  = col("WEIGHT")
    c_cat     = col("CATEGORY")
    c_subcat  = col("SUB CATEGORY")

    if c_barcode is None:
        logger.error("BARCODE column not found in %s", path)
        wb.close()
        return 0

    count = 0
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        if not row or row[c_barcode] is None:
            continue
        barcode = str(row[c_barcode]).strip()
        if not barcode or not barcode.isdigit() or len(barcode) not in (8, 12, 13):
            continue
        mrp_val = row[c_mrp] if c_mrp is not None else None
        catalog[barcode] = {
            "product_name":      str(row[c_name]).strip() if c_name is not None and row[c_name] else None,
            "brand":             str(row[c_brand]).strip() if c_brand is not None and row[c_brand] else None,
            "category":          str(row[c_cat]).strip() if c_cat is not None and row[c_cat] else None,
            "sub_category":      str(row[c_subcat]).strip() if c_subcat is not None and row[c_subcat] else None,
            "net_weight":        str(row[c_weight]).strip() if c_weight is not None and row[c_weight] else None,
            "mrp":               str(mrp_val).strip() if mrp_val is not None else None,
            "country_of_origin": None,
            "gs1_prefix":        None,
            "ingredients":       None,
        }
        count += 1
    wb.close()
    return count


def _load_fmcg_database(path: str, catalog: dict) -> int:
    """
    Loader for Cleaned_Indian_FMCG_Database.xlsx
    Headers (row 0): Source Excel Row, Barcode, Item Name, Uom, MRP, OUR PRICE, ...
    Only fills gaps — does NOT overwrite entries already in catalog.
    """
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Cleaned_Products"]
    count = 0
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        if not row or row[1] is None:
            continue
        barcode = str(row[1]).strip()
        if not barcode or not barcode.isdigit():
            continue
        if barcode in catalog:
            continue  # already loaded from a richer source
        mrp_val = row[4]
        catalog[barcode] = {
            "product_name":      str(row[2]).strip() if row[2] else None,
            "brand":             None,
            "category":          None,
            "sub_category":      None,
            "net_weight":        None,
            "mrp":               str(mrp_val).strip() if mrp_val is not None else None,
            "country_of_origin": None,
            "gs1_prefix":        None,
            "ingredients":       None,
        }
        count += 1
    wb.close()
    return count


def load_catalog(folder: str = "backend") -> dict:
    catalog: dict = {}

    # 1. Original 10 FMCG catalog files (highest priority — most curated)
    files = sorted(glob.glob(os.path.join(folder, "*.xlsx")))
    for path in files:
        basename = os.path.basename(path)
        if basename in _DEDICATED_FILES:
            continue
        try:
            n = _load_file(path, catalog)
            logger.info("Loaded %d entries from %s", n, basename)
        except Exception as e:
            logger.error("Failed to load %s: %s", basename, e)

    # 2. Inventory catalog — richest data (brand, category, weight)
    inv_path = os.path.join(folder, _INVENTORY_FILE)
    if os.path.exists(inv_path):
        try:
            n = _load_inventory_catalog(inv_path, catalog)
            logger.info("Loaded %d entries from %s", n, _INVENTORY_FILE)
        except Exception as e:
            logger.error("Failed to load %s: %s", _INVENTORY_FILE, e)

    # 3. FMCG database — fills remaining gaps (name + MRP only)
    fmcg_path = os.path.join(folder, _FMCG_DB_FILE)
    if os.path.exists(fmcg_path):
        try:
            n = _load_fmcg_database(fmcg_path, catalog)
            logger.info("Loaded %d entries from %s", n, _FMCG_DB_FILE)
        except Exception as e:
            logger.error("Failed to load %s: %s", _FMCG_DB_FILE, e)

    logger.info("Catalog ready — %d total barcodes", len(catalog))
    return catalog


def lookup(catalog: dict, barcode: str) -> dict | None:
    """Return catalog entry for barcode, or None if not found."""
    return catalog.get(barcode)
