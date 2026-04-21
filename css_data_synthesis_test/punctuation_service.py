from __future__ import annotations

import io
import logging
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from threading import Lock
from typing import Any, Literal

import requests


logger = logging.getLogger(__name__)
PunctuationBackend = Literal["remote", "local"]

DEFAULT_PUNCT_API_URL = os.getenv(
    "PUNCT_API_URL",
    "https://aimpapi.midea.com/t-aigc/aimp-customer-punc/punc_completion",
).strip()
DEFAULT_PUNCT_API_KEY = os.getenv(
    "PUNCT_API_KEY",
    "msk-0ed73bc8a5e3e76f3fa2c7ac1c82f3aabbe3edda6973e5382dc7e926571aa22f",
).strip()
DEFAULT_PUNCT_TIMEOUT_SECONDS = float(os.getenv("PUNCT_API_TIMEOUT_SECONDS", "15") or "15")
DEFAULT_PUNCT_BACKEND: PunctuationBackend = str(os.getenv("PUNCT_BACKEND", "local") or "local").strip().lower()  # type: ignore[assignment]
DEFAULT_LOCAL_PUNCT_MODEL_DIR = os.getenv("PUNCT_MODEL_DIR", "").strip()
PROJECT_LOCAL_PUNCT_MODEL_DIR = str(
    Path(__file__).resolve().parent.parent
    / "models"
    / "punc_ct-transformer_zh-cn-common-vocab272727-pytorch"
)
LEGACY_LOCAL_PUNCT_MODEL_DIR = (
    "/Users/gj/Documents/vsfile/customer-data-process/models/"
    "punc_ct-transformer_zh-cn-common-vocab272727-pytorch"
)


def _extract_punctuated_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload.strip()
    if isinstance(payload, list):
        for item in payload:
            extracted = _extract_punctuated_text(item)
            if extracted:
                return extracted
        return ""
    if not isinstance(payload, dict):
        return ""

    direct_keys = ("text", "result", "output", "content", "sentence", "punctuated_text")
    for key in direct_keys:
        value = payload.get(key)
        extracted = _extract_punctuated_text(value)
        if extracted:
            return extracted

    nested_keys = ("data", "results", "choices", "querys")
    for key in nested_keys:
        value = payload.get(key)
        extracted = _extract_punctuated_text(value)
        if extracted:
            return extracted
    return ""


class PunctuationService:
    def __init__(
        self,
        *,
        backend: PunctuationBackend = DEFAULT_PUNCT_BACKEND,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = DEFAULT_PUNCT_TIMEOUT_SECONDS,
        model_dir: str | Path | None = None,
    ) -> None:
        normalized_backend = str(backend or "remote").strip().lower()
        self.backend: PunctuationBackend = "local" if normalized_backend == "local" else "remote"
        self.api_url = str(api_url or DEFAULT_PUNCT_API_URL).strip()
        self.api_key = str(api_key or DEFAULT_PUNCT_API_KEY).strip()
        self.timeout_seconds = max(float(timeout_seconds or DEFAULT_PUNCT_TIMEOUT_SECONDS), 1.0)
        resolved_model_dir = str(model_dir or DEFAULT_LOCAL_PUNCT_MODEL_DIR).strip()
        if not resolved_model_dir:
            if Path(PROJECT_LOCAL_PUNCT_MODEL_DIR).exists():
                resolved_model_dir = PROJECT_LOCAL_PUNCT_MODEL_DIR
            else:
                resolved_model_dir = LEGACY_LOCAL_PUNCT_MODEL_DIR
        self.model_dir = Path(resolved_model_dir).expanduser()
        self._model = None
        self._model_lock = Lock()

    def available(self) -> bool:
        if self.backend == "remote":
            return bool(self.api_url and self.api_key)
        return self.model_dir.exists()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "AIGC-USER": "guojian34",
        }

    @staticmethod
    def _build_payload(text: str) -> dict[str, Any]:
        return {"querys": [text]}

    def _punctuate_remote(self, text: str) -> str:
        response = requests.post(
            self.api_url,
            headers=self._headers(),
            json=self._build_payload(text),
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"status={response.status_code}, body={response.text[:300]}")
        parsed = response.json()
        punctuated = _extract_punctuated_text(parsed)
        if punctuated:
            return punctuated
        raise RuntimeError(f"empty punctuated text, body={response.text[:300]}")

    def _load_local_model(self):
        try:
            from funasr import AutoModel
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("funasr is not installed") from exc
        if not self.model_dir.exists():
            raise RuntimeError(f"local punctuation model not found: {self.model_dir}")
        with self._model_lock:
            if self._model is None:
                logger.info("loading local punctuation model from %s", self.model_dir)
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self._model = AutoModel(
                        model=str(self.model_dir),
                        disable_update=True,
                    )
        return self._model

    def _punctuate_local(self, text: str) -> str:
        model = self._load_local_model()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = model.generate(input=text)
        punctuated = _extract_punctuated_text(result)
        if punctuated:
            return punctuated
        raise RuntimeError("local punctuation model returned empty text")

    def punctuate(self, text: str) -> str:
        normalized = str(text or "").strip()
        if not normalized:
            return ""
        if not self.available():
            if self.backend == "remote":
                raise RuntimeError("punctuation api configuration missing")
            raise RuntimeError(f"local punctuation backend unavailable: {self.model_dir}")
        if self.backend == "local":
            return self._punctuate_local(normalized)
        return self._punctuate_remote(normalized)


_punctuation_service = PunctuationService()


def configure_punctuation_service(
    *,
    backend: PunctuationBackend | str | None = None,
    api_url: str | None = None,
    api_key: str | None = None,
    timeout_seconds: float | None = None,
    model_dir: str | Path | None = None,
) -> PunctuationService:
    global _punctuation_service
    _punctuation_service = PunctuationService(
        backend=(backend or DEFAULT_PUNCT_BACKEND),
        api_url=api_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds or DEFAULT_PUNCT_TIMEOUT_SECONDS,
        model_dir=model_dir,
    )
    return _punctuation_service


def get_punctuation_service() -> PunctuationService:
    return _punctuation_service


def punctuate_text(text: str) -> str:
    return _punctuation_service.punctuate(text)


if __name__ == "__main__":
    res = punctuate_text("你好")
    print(res)
