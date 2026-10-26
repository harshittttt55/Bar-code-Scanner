import os
import re
import json
import logging
import asyncio
from typing import Optional, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini client initialized with model: %s", GEMINI_MODEL)
    except Exception as exc:
        logger.error("Gemini init failed: %s", exc)
else:
    logger.error("GEMINI_API_KEY not set.")

app = FastAPI(title="Barcode Product Lookup API", version="3.0.0")

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
    mrp: Optional[str] = None
    net_weight: Optional[str] = None
    ingredients: Optional[str] = None
    nutritional_info: Optional[str] = None
    allergens: Optional[str] = None
    best_before: Optional[str] = None
    manufacturer: Optional[str] = None
    country_of_origin: Optional[str] = None
    storage_instructions: Optional[str] = None
    certifications: Optional[str] = None
    additional_info: Optional[str] = None
    found: bool = False
    sources: list[str] = Field(default_factory=list)
    verification_status: str = "not_found"


def clean_barcode(value: str) -> str:
    return re.sub(r"[\s\-]", "", value.strip())


def extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", (text or "").strip(), flags=re.I)
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


def extract_sources(response) -> list[str]:
    urls = []
    try:
        for candidate in response.candidates or []:
            metadata = getattr(candidate, "grounding_metadata", None)
            if not metadata:
                continue
            for chunk in getattr(metadata, "grounding_chunks", None) or []:
                web = getattr(chunk, "web", None)
                uri = getattr(web, "uri", None) if web else None
                if uri and uri.startswith(("http://", "https://")):
                    urls.append(uri)
    except Exception:
        pass
    return list(dict.fromkeys(urls))


async def lookup_with_gemini(barcode: str) -> tuple[dict, list[str]]:
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API key not configured.")

    retry_delays = [5, 15]  # seconds to wait before retrying on 429
    last_exc = None

    for attempt, delay in enumerate([0] + retry_delays):
        if delay:
            logger.warning("Rate limited, retrying in %ss (attempt %d)...", delay, attempt + 1)
            await asyncio.sleep(delay)
        try:
            return await _call_gemini(barcode)
        except Exception as exc:
            err = str(exc).lower()
            if "429" in err or "quota" in err or "resource_exhausted" in err:
                last_exc = exc
                continue
            raise

    raise HTTPException(status_code=429, detail="Rate limit hit. Please wait a moment and try again.")


async def _call_gemini(barcode: str) -> tuple[dict, list[str]]:
    prompt = f"""Search Google for the product with barcode {barcode}.

Search for: "{barcode}", "{barcode} product India", "{barcode} MRP ingredients"

Find the exact product this barcode belongs to and return every detail you can find.

Return ONLY a JSON object (no extra text) with these fields (null if not found):
{{
  "product_name": null,
  "brand": null,
  "category": null,
  "mrp": null,
  "net_weight": null,
  "ingredients": null,
  "nutritional_info": null,
  "allergens": null,
  "best_before": null,
  "manufacturer": null,
  "country_of_origin": null,
  "storage_instructions": null,
  "certifications": null,
  "additional_info": null
}}"""

    response = await asyncio.to_thread(
        gemini_client.models.generate_content,
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.1,
        ),
    )

    data = extract_json(response.text or "")
    sources = extract_sources(response)
    logger.info("Gemini result for barcode %s: %s", barcode, data)
    return data, sources





class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=200)
    history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    barcode: Optional[str] = None


BARCODE_RE = re.compile(r"\b\d{8,14}\b")


async def chat_with_gemini(message: str, history: list[dict]) -> tuple[str, Optional[str]]:
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API key not configured.")

    barcode_match = BARCODE_RE.search(message)
    barcode = barcode_match.group(0) if barcode_match else None

    if barcode:
        prompt = f"""You are a helpful product assistant. The user has provided barcode {barcode}.

Search Google for this barcode and find the product details. Then reply in a friendly, conversational way as a chatbot would.

Include key info like: product name, brand, category, MRP, net weight, ingredients summary, manufacturer, country of origin.

If you cannot find the product, say so clearly and suggest the user double-check the barcode.

Keep the response concise and easy to read. Use simple formatting (no JSON, no code blocks)."""
    else:
        history_text = ""
        for msg in history[-6:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role}: {msg.get('content', '')}\n"

        prompt = f"""You are a helpful product and barcode assistant. You help users look up product information by barcode number.

{history_text}User: {message}

Reply helpfully. If the user asks about a product, remind them they can share a barcode number (8–14 digits) and you'll look it up."""

    retry_delays = [5, 15]
    last_exc = None

    for attempt, delay in enumerate([0] + retry_delays):
        if delay:
            await asyncio.sleep(delay)
        try:
            # Try with Google Search grounding for barcodes, plain otherwise
            if barcode:
                try:
                    config = types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.2,
                    )
                    response = await asyncio.to_thread(
                        gemini_client.models.generate_content,
                        model=GEMINI_MODEL,
                        contents=prompt,
                        config=config,
                    )
                except Exception as search_exc:
                    err = str(search_exc).lower()
                    if "429" in err or "quota" in err or "resource_exhausted" in err:
                        raise
                    # Grounding not available on this tier — fall back to plain
                    logger.warning("Google Search grounding failed (%s), retrying without it.", search_exc)
                    config = types.GenerateContentConfig(temperature=0.2)
                    response = await asyncio.to_thread(
                        gemini_client.models.generate_content,
                        model=GEMINI_MODEL,
                        contents=prompt,
                        config=config,
                    )
            else:
                config = types.GenerateContentConfig(temperature=0.7)
                response = await asyncio.to_thread(
                    gemini_client.models.generate_content,
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=config,
                )
            return (response.text or "Sorry, I couldn't get a response."), barcode
        except Exception as exc:
            err = str(exc).lower()
            if "429" in err or "quota" in err or "resource_exhausted" in err:
                last_exc = exc
                continue
            raise

    raise HTTPException(status_code=429, detail="Rate limit hit. Please wait a moment and try again.")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        reply, barcode = await chat_with_gemini(request.message, request.history)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chat failed")
        raise HTTPException(status_code=502, detail=str(exc))
    return ChatResponse(reply=reply, barcode=barcode)


@app.get("/")
async def root():
    return {"message": "Barcode Lookup API running", "docs": "/docs"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "gemini_ready": gemini_client is not None,
        "model": GEMINI_MODEL,
    }


@app.post("/api/product", response_model=ProductInfo)
async def get_product(request: BarcodeRequest):
    barcode = clean_barcode(request.barcode)

    try:
        data, sources = await lookup_with_gemini(barcode)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Gemini lookup failed for %s", barcode)
        err = str(exc).lower()
        if "429" in err or "quota" in err or "resource_exhausted" in err:
            raise HTTPException(status_code=429, detail="Rate limit hit. Try again in a moment.")
        raise HTTPException(status_code=502, detail=f"Lookup failed: {type(exc).__name__}")

    found = bool(data.get("product_name") or data.get("brand"))

    return ProductInfo(
        barcode=barcode,
        product_name=data.get("product_name"),
        brand=data.get("brand"),
        category=data.get("category"),
        mrp=str(data["mrp"]) if data.get("mrp") is not None else None,
        net_weight=data.get("net_weight"),
        ingredients=data.get("ingredients"),
        nutritional_info=str(data["nutritional_info"]) if data.get("nutritional_info") else None,
        allergens=data.get("allergens"),
        best_before=data.get("best_before"),
        manufacturer=data.get("manufacturer"),
        country_of_origin=data.get("country_of_origin"),
        storage_instructions=data.get("storage_instructions"),
        certifications=data.get("certifications"),
        additional_info=data.get("additional_info"),
        found=found,
        sources=sources,
        verification_status="found_via_ai" if found else "not_found",
    )
