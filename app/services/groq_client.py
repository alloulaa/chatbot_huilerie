"""
Client pour l'API Groq.
Gère la communication avec Groq pour les analyses d'explications.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", os.getenv("GROK_API_KEY", ""))


class GroqClient:
    """Client API pour Groq."""

    def __init__(self):
        self.api_key = GROQ_API_KEY

    async def explain(self, prompt: str) -> str | None:
        """
        Appelle l'API Groq pour générer une explication intelligente.
        
        Args:
            prompt: Texte du prompt à envoyer à Groq
        
        Returns:
            str : Texte généré par Groq, ou None si l'API est indisponible.
        """
        if not self.api_key:
            logger.info("GROQ_API_KEY not set — skipping AI explanation")
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "max_tokens": 2000,
                        "temperature": 0.7,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                    },
                )
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices", [])
                if choices and isinstance(choices, list):
                    return choices[0].get("message", {}).get("content", "")
                return None
        except httpx.ReadTimeout:
            logger.warning("Groq API timeout for explanation")
            return None
        except Exception as exc:
            logger.warning("Groq API call failed: %s", exc)
            return None
