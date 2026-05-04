from dotenv import load_dotenv

load_dotenv()

import base64
import json
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_FILE = BASE_DIR / "frontend" / "index.html"

app = FastAPI(title="AI Crop Disease Detector", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FALLBACK_DISEASES: dict[str, dict[str, str]] = {
    "Tomato Late Blight": {"type": "Fungal disease", "pesticide": "Mancozeb"},
    "Potato Early Blight": {"type": "Fungal disease", "pesticide": "Chlorothalonil"},
    "Corn Common Rust": {"type": "Fungal disease", "pesticide": "Propiconazole"},
    "Apple Scab": {"type": "Fungal disease", "pesticide": "Captan"},
    "Wheat Rust": {"type": "Fungal disease", "pesticide": "Tebuconazole"},
}


class AnalysisResponse(BaseModel):
    disease_name: str
    confidence: float
    severity: str
    treatment_english: str
    treatment_urdu: str
    pesticide: str
    prevention_tips: str
    diagnosis_source: str
    recommendation_source: str
    message: Optional[str] = None


def _confidence_to_severity(confidence: float) -> str:
    if confidence >= 80:
        return "High"
    if confidence >= 50:
        return "Medium"
    return "Low"


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _normalize_label(label: str) -> str:
    cleaned = label.replace("_", " ").replace("-", " ").strip()
    return " ".join([word.capitalize() for word in cleaned.split()])


def _fallback_diagnosis(filename: str) -> tuple[str, float, str]:
    lower_name = (filename or "").lower()
    for disease in FALLBACK_DISEASES:
        key = disease.lower()
        if any(token in lower_name for token in key.split()):
            return disease, 55.0, "filename-fallback"
    first_key = next(iter(FALLBACK_DISEASES.keys()))
    return first_key, 35.0, "default-fallback"


def _fallback_recommendation(disease_name: str, confidence: float) -> AnalysisResponse:
    details = FALLBACK_DISEASES.get(
        disease_name, {"type": "Possible crop disease", "pesticide": "Mancozeb"}
    )
    disease_type = details["type"]
    pesticide = details["pesticide"]
    severity = _confidence_to_severity(confidence)
    return AnalysisResponse(
        disease_name=disease_name,
        confidence=round(confidence, 2),
        severity=severity,
        treatment_english=(
            f"{disease_type} suspected. Remove heavily infected leaves, keep field dry, "
            "and spray as per label instructions."
        ),
        treatment_urdu=(
            "ممکنہ فنگس بیماری ہے۔ زیادہ متاثرہ پتے ہٹا دیں، کھیت میں نمی کم رکھیں، "
            "اور لیبل کے مطابق سپرے کریں۔"
        ),
        pesticide=pesticide,
        prevention_tips=(
            "Use disease-free seed, avoid over-irrigation, rotate crops, and inspect leaves weekly."
        ),
        diagnosis_source="fallback",
        recommendation_source="fallback",
        message="Fallback guidance used due to model/API issue.",
    )


def _groq_client() -> Optional[Any]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from groq import Groq

        return Groq(api_key=api_key)
    except Exception:
        return None


def _json_from_text(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _analyze_with_groq_vision(image_bytes: bytes, mime_type: str = "image/jpeg") -> Optional[dict[str, Any]]:
    client = _groq_client()
    if client is None:
        return None
    try:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt = (
            "You are an expert agricultural advisor for Pakistan. Analyze this crop image and return only JSON. "
            "Identify likely disease and provide confidence plus treatment guidance in simple language for farmers. "
            "Return ONLY valid JSON with keys: disease_name, confidence_percent, treatment_english, treatment_urdu, "
            "pesticide, prevention_tips. Confidence must be a number from 0 to 100."
        )
        completion = client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            temperature=0.2,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{img_b64}"},
                        },
                    ],
                }
            ],
        )
        content = completion.choices[0].message.content or ""
        data = _json_from_text(content)
        if not data:
            return None

        disease_name = _normalize_label(str(data.get("disease_name", "")).strip()) or "Unknown Disease"
        confidence = _safe_float(data.get("confidence_percent", 40.0), 40.0)
        result = {
            "disease_name": disease_name,
            "confidence": max(0.0, min(100.0, confidence)),
            "treatment_english": str(data.get("treatment_english", "")).strip(),
            "treatment_urdu": str(data.get("treatment_urdu", "")).strip(),
            "pesticide": str(data.get("pesticide", "")).strip(),
            "prevention_tips": str(data.get("prevention_tips", "")).strip(),
        }
        if not result["disease_name"]:
            return None
        return result
    except Exception:
        return None


@app.get("/")
async def root() -> FileResponse:
    if not FRONTEND_FILE.exists():
        raise HTTPException(status_code=404, detail="Frontend not found.")
    return FileResponse(str(FRONTEND_FILE))


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "vision_model": GROQ_VISION_MODEL,
        "groq_api_key_set": bool(os.getenv("GROQ_API_KEY", "").strip()),
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_crop(file: UploadFile = File(...)) -> AnalysisResponse:
    image_bytes = b""
    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise ValueError("Empty file")
    except Exception:
        return _fallback_recommendation("Tomato Late Blight", 30.0)

    try:
        vision_result = _analyze_with_groq_vision(image_bytes, file.content_type or "image/jpeg")
        if vision_result is not None:
            confidence = _safe_float(vision_result.get("confidence", 40.0), 40.0)
            severity = _confidence_to_severity(confidence)
            return AnalysisResponse(
                disease_name=str(vision_result.get("disease_name", "Unknown Disease")),
                confidence=round(confidence, 2),
                severity=severity,
                treatment_english=str(vision_result.get("treatment_english") or "").strip()
                or "Remove infected leaves, improve air flow, and spray according to label directions.",
                treatment_urdu=str(vision_result.get("treatment_urdu") or "").strip()
                or "متاثرہ پتے ہٹا دیں، ہوا کی آمدورفت بہتر کریں، اور لیبل کے مطابق سپرے کریں۔",
                pesticide=str(vision_result.get("pesticide") or "").strip() or "Consult local agri store",
                prevention_tips=str(vision_result.get("prevention_tips") or "").strip()
                or "Inspect crop weekly, avoid over-irrigation, and keep field sanitation.",
                diagnosis_source="groq-vision",
                recommendation_source="groq-vision",
            )
    except Exception:
        pass

    disease_name, confidence, _ = _fallback_diagnosis(file.filename or "")
    fallback = _fallback_recommendation(disease_name, confidence)
    fallback.diagnosis_source = "fallback"
    fallback.recommendation_source = "fallback"
    return fallback
