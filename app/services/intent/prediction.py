"""
Handler pour l'intent PREDICTION.
"""
import logging
from typing import Any

import httpx

from app.domain.chat import ChatQuery, IntentResult
from app.services.intent.base import IntentHandler
from app.services.prediction_client import PredictionClient

logger = logging.getLogger(__name__)

_BOOL_INT_FIELDS = {
    "presence_ajout_eau",
    "presence_presse",
    "presence_separateur",
}


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normaliser quelques champs ambigus venant du frontend."""
    normalized = dict(payload)
    for field in _BOOL_INT_FIELDS:
        value = normalized.get(field)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"oui", "yes", "true"}:
                normalized[field] = 1
            elif lowered in {"non", "no", "false"}:
                normalized[field] = 0
    return normalized


def _extract_422_errors(response: httpx.Response) -> tuple[list[str], list[str]]:
    """Extraire les champs manquants et mal typés depuis une 422 FastAPI."""
    missing_fields: list[str] = []
    type_fields: list[str] = []

    try:
        body = response.json()
    except ValueError:
        return missing_fields, type_fields

    details = body.get("detail", []) if isinstance(body, dict) else []
    for item in details:
        if not isinstance(item, dict):
            continue

        loc = item.get("loc", [])
        field_name = loc[-1] if isinstance(loc, list) and loc else None
        if not field_name:
            continue

        item_type = item.get("type", "")
        if item_type == "missing":
            missing_fields.append(str(field_name))
        elif "parsing" in str(item_type) or "type" in str(item_type):
            type_fields.append(str(field_name))

    return sorted(set(missing_fields)), sorted(set(type_fields))


def _fmt(value: float, decimals: int = 2) -> str:
    """Formater un nombre pour l'affichage."""
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}".replace(",", " ")
    return str(value)


class PredictionHandler(IntentHandler):
    """Handler pour traiter les requêtes de prédiction."""
    
    def __init__(self, client: PredictionClient | None = None):
        self.client = client or PredictionClient()
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de prédiction via le microservice IA."""
        payload = (query.extra_context or {}).get("prediction_payload")

        if not isinstance(payload, dict) or not payload:
            text = (
                "Pour lancer une prédiction, j'ai besoin des paramètres de production "
                "(variété, région, poids des olives, maturité, type de machine, etc.)."
            )
            return IntentResult(text=text, data={"missing_payload": True}, structured_payload=None)

        payload = _normalize_payload(payload)

        # Détecte le mode de prédiction selon la présence des paramètres de labo
        lab_fields = ['acidite_huile_pourcent', 'indice_peroxyde_meq_o2_kg', 'k270']
        has_lab_analysis = all(
            field in payload and payload[field] is not None 
            for field in lab_fields
        )
        detected_mode = "with_lab" if has_lab_analysis else "no_lab"
        logger.info(f"Prediction mode detected: {detected_mode} (has_lab={has_lab_analysis})")

        try:
            result = await self.client.predict(payload)
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 422:
                missing_fields, type_fields = _extract_422_errors(e.response)
                parts: list[str] = []
                if missing_fields:
                    parts.append("champs manquants: " + ", ".join(missing_fields))
                if type_fields:
                    parts.append("types invalides: " + ", ".join(type_fields))

                details = " ; ".join(parts) if parts else "format des champs invalide"
                text = f"Le payload de prédiction est invalide ({details})."
                return IntentResult(
                    text=text,
                    data={
                        "service_available": True,
                        "validation_error": True,
                        "status_code": 422,
                        "missing_fields": missing_fields,
                        "type_fields": type_fields,
                    },
                    structured_payload=None,
                )

            logger.error(f"Prediction service HTTP error ({detected_mode}): {type(e).__name__}: {e}", exc_info=True)
            text = "Le service de prédiction a renvoyé une erreur HTTP."
            return IntentResult(text=text, data={"service_available": False}, structured_payload=None)
        except httpx.ReadTimeout:
            logger.error("Prediction service timeout (%s)", detected_mode, exc_info=True)
            text = "Le service de prédiction est trop lent actuellement (timeout)."
            return IntentResult(text=text, data={"service_available": False, "timeout": True}, structured_payload=None)
        except Exception as e:
            logger.error(f"Prediction service error ({detected_mode}): {type(e).__name__}: {e}", exc_info=True)
            # Fallback conservateur si le microservice est indisponible.
            text = "Le service de prédiction est temporairement indisponible."
            return IntentResult(text=text, data={"service_available": False}, structured_payload=None)

        # ✨ Utilise notre détection locale comme source de vérité (pas celle du service)
        mode = detected_mode
        qualite = result.get("qualite_predite", "inconnue")
        proba = result.get("probabilite_qualite")
        rend = result.get("rendement_predit_pourcent", 0)
        qte = result.get("quantite_huile_recalculee_litres", 0)

        text = (
            f"Prédiction ({mode}) : qualité **{qualite}**, "
            f"rendement **{_fmt(rend, 1)} %**, "
            f"huile estimée **{_fmt(qte, 2)} litres**."
        )
        if proba is not None:
            text += f" Confiance qualité : **{_fmt(float(proba) * 100, 1)} %**."

        return IntentResult(text=text, data=result, structured_payload=None)
