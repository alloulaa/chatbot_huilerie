"""
Handler pour l'intent EXPLICATION — API intelligente avec fallback rule-based.

Version intelligente : collecte TOUTES les données disponibles sur le lot
(réception, conditions des olives, étapes de production, machines, analyses labo,
mouvements stock, données agronomiques) et appelle Groq pour
générer une explication causale riche et contextuelle.

Fallback : analyse rule-based enrichie si l'API est indisponible.
"""
from __future__ import annotations

import logging

from app.domain.chat import ChatQuery, IntentResult
from app.services.intent.base import IntentHandler
from app.services.query_service import ChatbotService

from app.utils.lot_helpers import _normalize_lot_reference, _safe_float, _fmt
from app.domain.oleiculture import _grade_huile
from app.services.groq_client import GroqClient
from app.services.explication.data_collector import _collect_all_lot_data
from app.services.explication.prompt_builder import _build_expert_prompt
from app.services.explication.rule_based import _rule_based_explanation

logger = logging.getLogger(__name__)


def _humanize_explanation_text(text: str) -> str:
    """Remove the metadata-heavy opening so the answer reads like an analysis, not a dump."""
    if not text:
        return text

    blocked_prefixes = (
        "## Analyse experte du lot",
        "**Variété** :",
        "**Région** :",
        "**Quantité** :",
        "**Fournisseur** :",
        "**Huilerie** :",
        "**Réception** :",
        "**Méthode récolte** :",
        "- Référence :",
        "- Variété d'olive :",
        "- Fournisseur :",
        "- Huilerie :",
        "- Région fournisseur :",
        "- Région du lot/verger :",
        "- Type de sol :",
        "- Altitude :",
        "- Méthode de récolte :",
        "- Date de récolte :",
        "- Date de réception à l'huilerie :",
        "- Quantité initiale :",
        "- Quantité restante :",
        "- Acidité des olives à la réception :",
        "- Indice de maturité :",
        "- Humidité des olives :",
        "- Taux d'impuretés :",
        "- Température de stockage avant trituration :",
        "- Observations sur le lot :",
        "### 1. Informations du lot",
    )

    cleaned_lines: list[str] = []
    skip_blank = False
    for line in text.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in blocked_prefixes):
            skip_blank = True
            continue
        if skip_blank and not stripped:
            continue
        skip_blank = False
        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines).strip()
    return cleaned_text or text


class ExplicationHandler(IntentHandler):
    """Handler intelligent pour expliquer la qualité/rendement d'un lot spécifique.

    1. Collecte TOUTES les données disponibles (lot, production, labo, stock, benchmark).
    2. Appelle Groq pour une analyse causale profonde.
    3. Fallback vers analyse rule-based enrichie si l'API est indisponible.
    """

    def __init__(self, service: ChatbotService):
        self.service = service
        self.groq = GroqClient()

    async def handle(self, query: ChatQuery) -> IntentResult:
        # ── Extraction de la référence lot ────────────────────────────────
        lot_ref = (
            query.extra_context.get("lot_reference")
            or query.extra_context.get("reference_lot")
            or query.extra_context.get("code_lot")
            or getattr(query, "lot_reference", None)
            or getattr(query, "reference_lot", None)
            or getattr(query, "code_lot", None)
        )

        if not lot_ref and query.extra_context.get("entities"):
            entities = query.extra_context["entities"]
            lot_ref = (entities.get("lot_reference") or entities.get("reference_lot")
                       or entities.get("code_lot"))

        if not lot_ref:
            return IntentResult(
                text=(
                    "Précisez la référence du lot pour que je puisse l'analyser en détail. "
                    "Exemple : *\"pourquoi la qualité du lot LO01 était mauvaise ?\"*"
                ),
                data=None,
                structured_payload=None,
            )

        normalized_ref = _normalize_lot_reference(lot_ref)
        if not normalized_ref:
            return IntentResult(
                text=f"Référence de lot invalide : **{lot_ref}**.",
                data=None, structured_payload=None,
            )

        # ── Collecte des données ──────────────────────────────────────────
        lot_data = _collect_all_lot_data(normalized_ref, query.enterprise_id)

        if lot_data.get("error"):
            return IntentResult(
                text=f"Impossible de récupérer les données du lot **{normalized_ref}** : {lot_data['error']}",
                data=None, structured_payload=None,
            )

        if not lot_data.get("lot"):
            return IntentResult(
                text=f"Aucun lot trouvé pour la référence **{normalized_ref}**.",
                data=None, structured_payload=None,
            )

        # ── Génération de l'explication ───────────────────────────────────
        user_question = query.message or f"Explique la qualité du lot {normalized_ref}"

        # Tentative appel Groq API
        prompt = _build_expert_prompt(lot_data, user_question)
        ai_explanation = await self.groq.explain(prompt)

        if ai_explanation and len(ai_explanation.strip()) > 100:
            explanation_text = _humanize_explanation_text(ai_explanation)
            logger.info("AI explanation generated for lot %s (%d chars)", normalized_ref, len(ai_explanation))
        else:
            # Fallback rule-based enrichi
            explanation_text = _humanize_explanation_text(_rule_based_explanation(lot_data, user_question))
            logger.info("Rule-based fallback explanation for lot %s", normalized_ref)

        # ── Payload chart (paramètres labo vs seuils) ─────────────────────
        structured_payload = None
        analyses = lot_data.get("analyses") or []
        if analyses:
            a = analyses[0]
            acid = _safe_float(a.get("acidite_huile_pourcent"))
            perox = _safe_float(a.get("indice_peroxyde_meq_o2_kg"))
            k270 = _safe_float(a.get("k270"))
            k232 = _safe_float(a.get("k232"))
            poly = _safe_float(a.get("polphenols_mg_kg"))

            benchmark = lot_data.get("benchmark") or {}
            chart_labels = ["Acidité (%)", "Peroxyde (meq O₂/kg)", "K270", "K232"]
            chart_lot = [acid, perox / 20 * 100, k270 / 0.22 * 100, k232 / 2.5 * 100]  # normalisé %
            chart_seuil = [100, 100, 100, 100]

            structured_payload = {
                "labels": chart_labels,
                "datasets": [
                    {
                        "label": f"Lot {normalized_ref} (% du seuil)",
                        "data": [round(v, 1) for v in chart_lot],
                        "type": "bar",
                        "backgroundColor": [
                            "#FF5722" if chart_lot[i] > 100 else "#4CAF50"
                            for i in range(len(chart_lot))
                        ],
                    },
                    {
                        "label": "Seuil vierge extra (100%)",
                        "data": chart_seuil,
                        "type": "line",
                        "borderColor": "#FF9800",
                        "borderDash": [5, 5],
                    },
                ],
                "raw_values": {
                    "acidite": acid, "peroxyde": perox,
                    "k270": k270, "k232": k232, "polphenols": poly,
                },
                "grade": _grade_huile(acid, perox, k270),
                "benchmark": benchmark,
            }

        return IntentResult(
            text=explanation_text,
            data={
                "lot": lot_data.get("lot"),
                "executions": lot_data.get("executions"),
                "analyses": analyses,
                "benchmark": lot_data.get("benchmark"),
            },
            structured_payload=structured_payload,
        )
