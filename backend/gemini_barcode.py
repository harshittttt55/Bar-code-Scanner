"""
gemini_barcode.py — Gemini client with 429 rate-limit handling.
Used exclusively by barcode_router.py.
"""

import json
import logging
import os
import re
import time

from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = "gemini-3.5-flash-lite"
# gemini-2.0-flash has higher quotas and better search grounding support
GEMINI_GROUNDED_MODEL = os.getenv("GEMINI_GROUNDED_MODEL", "gemini-3.8-flash")


client: genai.Client | None = None

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("Barcode Gemini client ready — model: %s", GEMINI_MODEL)
else:
    logger.warning("GEMINI_API_KEY not set — barcode Gemini calls will fail.")


def _retry_loop(fn, max_retries: int, label: str) -> dict:
    """Shared retry loop with exponential backoff for 429 errors."""
    backoff_delay = 2
    for attempt in range(max_retries):
        try:
            return fn()
        except json.JSONDecodeError as exc:
            logger.error("%s JSON parse error: %s", label, exc)
            raise HTTPException(status_code=500, detail="Gemini returned malformed JSON.")
        except Exception as exc:
            error_str = str(exc)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries - 1:
                    logger.warning(
                        "Rate limit hit (429) on %s attempt %d/%d. Retrying in %ds...",
                        label, attempt + 1, max_retries, backoff_delay,
                    )
                    time.sleep(backoff_delay)
                    backoff_delay *= 2
                    continue
                raise HTTPException(
                    status_code=429,
                    detail="Gemini API rate limit exceeded (429). Please try again shortly.",
                )
            logger.error("%s API error: %s", label, exc)
            raise HTTPException(status_code=502, detail=f"Gemini API error: {exc}")
    return {"found": False}


def call_gemini(
    contents: str,
    system_prompt: str,
    temperature: float = 0.1,
    max_retries: int = 3,
) -> dict:
    """Call Gemini with JSON response mode (no grounding)."""
    if not client:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured.")

    def _call():
        response = client.models.generate_content(
            model=GEMINI_MODEL,
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

    return _retry_loop(_call, max_retries, "Gemini")


def call_gemini_grounded(
    contents: str,
    system_prompt: str,
    temperature: float = 0.1,
    max_retries: int = 3,
) -> dict:
    """
    Call Gemini with Google Search grounding enabled.
    Uses gemini-2.0-flash for higher quotas.
    Cannot use response_mime_type=application/json with grounding,
    so JSON is extracted from plain text response.
    """
    if not client:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured.")

    def _call():
        response = client.models.generate_content(
            model=GEMINI_GROUNDED_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        text = response.text.strip()
        json_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text, re.I)
        if json_match:
            text = json_match.group(1)
        else:
            obj_match = re.search(r"\{[\s\S]+\}", text)
            if obj_match:
                text = obj_match.group(0)
        return json.loads(text)

    return _retry_loop(_call, max_retries, "Gemini-Grounded")
