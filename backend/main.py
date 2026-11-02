"""
main.py — FastAPI app entry point.
Initialises the app, registers CORS, and mounts feature routers.
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gemini_barcode import client as barcode_client, GEMINI_MODEL
from gemini_medicine import client as medicine_client
from catalog import load_catalog
from barcode_router import router as barcode_router
from medicine_router import router as medicine_router

load_dotenv()

logging.basicConfig(level=logging.INFO)

CATALOG = load_catalog(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="BarcodeAI + Medicine Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(barcode_router, prefix="/api")
app.include_router(medicine_router, prefix="/api")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gemini_barcode": "configured" if barcode_client else "not configured",
        "gemini_medicine": "configured" if medicine_client else "not configured",
        "model": GEMINI_MODEL,
        "catalog_size": len(CATALOG),
    }
