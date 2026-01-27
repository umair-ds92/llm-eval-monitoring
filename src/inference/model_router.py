# src.inference.model_router

# Production relevance:
# A real enterprise LLM system frequently routes between multiple models/providers
# based on cost, latency, safety, or capability. Centralizing routing keeps the
# rest of the evaluation + monitoring pipeline stable and provider-agnostic.

# This module provides:
# - MockProvider: deterministic offline responses (good for tests/CI)
# - OpenAIHTTPProvider: optional provider using HTTP via `requests` (no SDK required)
# - ModelRouter: selects provider + model based on config


from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from src.common.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ModelResponse:
    provider: str
    model_name: str
    text: str
    usage: Optional[Dict[str, Any]] = None  # e.g., {"prompt_tokens":..., "completion_tokens":..., "total_tokens":...}
    raw: Optional[Dict[str, Any]] = None    # raw provider payload for debugging


class BaseProvider:
    name: str

    def generate(self, prompt: str, model: str, timeout_s: int = 30, **kwargs: Any) -> ModelResponse:
        raise NotImplementedError


class MockProvider(BaseProvider):
    name = "mock"

    def generate(self, prompt: str, model: str, timeout_s: int = 30, **kwargs: Any) -> ModelResponse:
        # Deterministic, fast, CI-friendly output
        text = f"[mock:{model}] {prompt}"
        return ModelResponse(provider=self.name, model_name=model, text=text, usage={"total_tokens": None}, raw=None)


class OpenAIHTTPProvider(BaseProvider):
    """
    Optional provider that calls OpenAI-compatible Chat Completions endpoint over HTTP.

    Notes:
    - This avoids relying on the OpenAI Python SDK.
    - You must set OPENAI_API_KEY in your environment.
    - Endpoint is configurable for future compatibility (base_url).
    """
    name = "openai"

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt: str, model: str, timeout_s: int = 30, **kwargs: Any) -> ModelResponse:
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Optional knobs (kept minimal)
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        t0 = time.perf_counter()
        r = requests.post(url, json=payload, headers=headers, timeout=timeout_s)
        dt_ms = (time.perf_counter() - t0) * 1000.0

        if r.status_code >= 400:
            raise RuntimeError(f"OpenAI HTTP error {r.status_code}: {r.text[:400]}")

        data = r.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage")

        logger.info("OpenAI response received (%.1f ms)", dt_ms)

        return ModelResponse(
            provider=self.name,
            model_name=model,
            text=text,
            usage=usage,
            raw=data,
        )


class ModelRouter:
    """
    Routes prompts to the configured provider/model.

    Config expected (configs/dev.yaml):
      inference:
        provider: openai|mock
        default_model: gpt-4o-mini
        timeout_s: 30
        max_retries: 2
        base_url: https://api.openai.com/v1   (optional)
    """

    def __init__(self, cfg: Dict[str, Any]) -> None:
        inference_cfg = (cfg or {}).get("inference", {}) or {}

        self.provider_name = str(inference_cfg.get("provider", "mock")).lower()
        self.default_model = str(inference_cfg.get("default_model", "mock-mini"))
        self.timeout_s = int(inference_cfg.get("timeout_s", 30))
        self.max_retries = int(inference_cfg.get("max_retries", 1))
        self.base_url = str(inference_cfg.get("base_url", "https://api.openai.com/v1"))

        self._provider = self._build_provider()

    def _build_provider(self) -> BaseProvider:
        if self.provider_name == "mock":
            return MockProvider()

        if self.provider_name == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not api_key:
                raise EnvironmentError("OPENAI_API_KEY not set. Set it or switch inference.provider to 'mock'.")
            return OpenAIHTTPProvider(api_key=api_key, base_url=self.base_url)

        raise ValueError(f"Unknown provider '{self.provider_name}'. Use 'mock' or 'openai'.")

    def generate(self, prompt: str, model: Optional[str] = None, **kwargs: Any) -> ModelResponse:
        model_name = model or self.default_model

        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 2):
            try:
                return self._provider.generate(prompt=prompt, model=model_name, timeout_s=self.timeout_s, **kwargs)
            except Exception as e:
                last_err = e
                logger.warning("Inference failed (attempt %d): %s", attempt, str(e)[:200])

        assert last_err is not None
        raise last_err
