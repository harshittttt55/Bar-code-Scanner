"""
gemini_medicine.py — Gemini client for medicine assistant.
Used exclusively by medicine_router.py.
"""

import json
import logging
import os
import re

from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

client: genai.Client | None = None

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("Medicine Gemini client ready — model: %s", GEMINI_MODEL)
else:
    logger.warning("GEMINI_API_KEY not set — medicine Gemini calls will fail.")


def call_gemini(contents: str, system_prompt: str, temperature: float = 0.1) -> dict:
    """
    Call Gemini with JSON response mode for medicine queries.
    Tries GEMINI_MODEL first, falls back to gemini-2.5-flash on 503.
    Returns parsed dict or raises HTTPException.
    """
    if not client:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured.")

    models_to_try = [GEMINI_MODEL]
    if GEMINI_MODEL != "gemini-3.8-flash":
        models_to_try.append("gemini-3.8-flash")

    for model in models_to_try:
        for _attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        temperature=temperature,
                    ),
                )
                text = response.text.strip()
                text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
                text = re.sub(r"\s*```$", "", text)
                return json.loads(text)

            except json.JSONDecodeError as exc:
                logger.error("Medicine Gemini JSON parse error (model=%s): %s", model, exc)
                raise HTTPException(status_code=500, detail="Gemini returned malformed JSON.")

            except Exception as exc:
                if "503" in str(exc) or "UNAVAILABLE" in str(exc) or "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                    logger.warning("Model %s unavailable, trying next.", model)
                    break
                logger.error("Medicine Gemini API error (model=%s): %s", model, exc)
                raise HTTPException(status_code=502, detail=f"Gemini API error: {exc}")

    logger.warning("All Gemini models unavailable for medicine.")
    return {"found": False}
