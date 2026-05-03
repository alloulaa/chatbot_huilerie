"""HTTP client for the external prediction service."""

from __future__ import annotations

import os
from typing import Any
import logging

import httpx


logger = logging.getLogger(__name__)


class PredictionClient:
    def __init__(self, base_url: str | None = None, timeout: float = 20.0):
        self.base_url = (base_url or os.getenv("PREDICTION_API_URL", "http://127.0.0.1:7500")).rstrip("/")
        self.timeout = timeout

    async def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            response = await client.post(f"{self.base_url}/predict", json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError:
                logger.warning(
                    "Prediction API validation/http error: status=%s body=%s",
                    response.status_code,
                    response.text,
                )
                raise
            return response.json()

    async def model_info(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            response = await client.get(f"{self.base_url}/model-info")
            response.raise_for_status()
            return response.json()
