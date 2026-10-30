"""
medicine_router.py — Medicine Assistant feature.
Routes:
  POST /api/medicine         — general Q&A
  POST /api/medicine/compare — structured two-medicine comparison
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from gemini_client import call_gemini

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Models ────────────────────────────────────────────────────────────────────

class MedicineRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


class MedicineResponse(BaseModel):
    answer: str
    mode: str
    med_a: dict | None = None
    med_b: dict | None = None
    key_differences: str | None = None
    substitutability: dict | None = None
    disclaimer: str = (
        "This information is for educational purposes only. "
        "Always consult a qualified healthcare professional before making any medical decisions."
    )


class CompareRequest(BaseModel):
    medicine_a: str = Field(..., min_length=1, max_length=200)
    medicine_b: str = Field(..., min_length=1, max_length=200)


# ── Prompts ───────────────────────────────────────────────────────────────────

_MEDICINE_PROMPT = """You are a knowledgeable Indian pharmaceutical assistant with access to Indian drug \
databases (CDSCO, 1mg, PharmEasy, MedlinePlus) and international clinical references.

RULES:
- Never invent drug names, dosages, or prices. If unsure, say so explicitly.
- Always include a note to consult a doctor before changing any medication.
- Cite sources where applicable (1mg, PharmEasy, CDSCO, WHO, etc.).
- Never recommend replacing a prescribed medicine without professional advice.
- Identify clearly when data is missing or conflicting.

RESPONSE FORMAT — choose based on the user's query:

1. NORMAL QUESTION (uses, side effects, dosage, precautions):
   { "mode": "info", "answer": "<markdown with sections ## Uses, ## Side Effects, ## Precautions, ## Sources>" }

2. COMPARISON REQUEST (user asks to compare two or more medicines):
   Return a markdown table: Feature | Medicine A | Medicine B
   Rows: Generic Name, Active Ingredients, Strength, Dosage Form, Manufacturer, MRP (approx),
         Uses, Side Effects, Warnings, Drug Interactions
   { "mode": "comparison", "answer": "<markdown table>" }

3. ALTERNATIVES REQUEST (user asks for alternatives):
   Two sections — Same Ingredient Alternatives and Therapeutic Alternatives.
   { "mode": "alternatives", "answer": "<markdown formatted text>" }

4. MEDICINE INFO LOOKUP (brand or generic name):
   Brand Name, Generic Name, Active Ingredients, Strength, Dosage Form, Manufacturer,
   Pack Sizes, Verified MRP (if available), Uses, Side Effects, Warnings.
   { "mode": "info", "answer": "<markdown formatted text>" }

Always respond with ONLY a valid JSON object — no extra text outside the JSON."""


_COMPARE_PROMPT = """You are an Indian pharmaceutical expert. Compare two medicines and return structured data.

RULES:
- Never invent data. Use "Data not available" for unknown fields.
- Be precise about strengths, dosage forms, and manufacturers.
- Always note substitution requires a doctor's advice.

Return ONLY this exact JSON structure (no extra text):
{
  "mode": "comparison",
  "med_a": {
    "generic_name": "...",
    "brand_name": "...",
    "active_ingredients": "...",
    "strength": "...",
    "dosage_form": "...",
    "manufacturer": "...",
    "mrp": "...",
    "uses": "...",
    "common_dosage": "...",
    "mechanism": "...",
    "side_effects": "...",
    "suitable_for": "...",
    "drug_interactions": "...",
    "prescription_required": "...",
    "warnings": "..."
  },
  "med_b": {
    "generic_name": "...",
    "brand_name": "...",
    "active_ingredients": "...",
    "strength": "...",
    "dosage_form": "...",
    "manufacturer": "...",
    "mrp": "...",
    "uses": "...",
    "common_dosage": "...",
    "mechanism": "...",
    "side_effects": "...",
    "suitable_for": "...",
    "drug_interactions": "...",
    "prescription_required": "...",
    "warnings": "..."
  },
  "key_differences": "...",
  "substitutability": {
    "verdict": "yes" | "partial" | "no",
    "summary": "One clear sentence answering: can Product A be replaced by Product B? e.g. 'Yes, Dolo 650 can generally replace Calpol 500 as both contain Paracetamol, but the strength differs.'",
    "reason": "Detailed explanation — same/different active ingredient, mechanism, strength differences, and any clinical conditions where substitution is or isn't safe.",
    "conditions": "Specific conditions, dosage adjustments, or patient groups where substitution changes (e.g. not for children, requires dose adjustment, only for short-term use).",
    "caution": "Safety warnings specific to switching between these two medicines. Always end with: Always consult your doctor or pharmacist before switching medicines."
  },
  "answer": ""
}"""""


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/medicine", response_model=MedicineResponse)
async def medicine_assistant(request: MedicineRequest):
    logger.info("Medicine query: %s", request.query[:80])
    data = call_gemini(request.query, _MEDICINE_PROMPT, temperature=0.2)
    return MedicineResponse(
        answer=data.get("answer", "No response generated."),
        mode=data.get("mode", "info"),
    )


@router.post("/medicine/compare", response_model=MedicineResponse)
async def medicine_compare(request: CompareRequest):
    logger.info("Medicine compare: %s vs %s", request.medicine_a, request.medicine_b)
    query = f"Compare {request.medicine_a} vs {request.medicine_b}"
    data = call_gemini(query, _COMPARE_PROMPT, temperature=0.1)
    return MedicineResponse(
        answer=data.get("answer", ""),
        mode="comparison",
        med_a=data.get("med_a"),
        med_b=data.get("med_b"),
        key_differences=data.get("key_differences"),
        substitutability=data.get("substitutability"),
    )
