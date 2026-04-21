from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from css_data_synthesis_test.punctuation_service import PunctuationService


app = FastAPI(title="Local Punctuation API")
local_punctuation_service = PunctuationService(backend="local")


class PunctuationRequest(BaseModel):
    text: str


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "backend": "local",
        "available": bool(local_punctuation_service.available()),
        "model_dir": str(local_punctuation_service.model_dir),
    }


@app.post("/predict")
def predict(req: PunctuationRequest) -> dict[str, object]:
    normalized = str(req.text or "").strip()
    if not normalized:
        return {
            "ok": True,
            "input_text": "",
            "punctuated_text": "",
        }
    try:
        punctuated_text = local_punctuation_service.punctuate(normalized)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"local punctuation failed: {exc}") from exc
    return {
        "ok": True,
        "input_text": normalized,
        "punctuated_text": punctuated_text,
    }
