"""
Handler pour l'intent COMPARAISON.

Gère les questions comparatives qui ne sont pas couvertes par les intents existants :
  - Comparer des campagnes entre elles (notamment par production litres, un champ
    absent du get_campagnes() existant)
  - Comparer des périodes pour une même métrique
  - Comparer des huileries entre elles

NOTE : La comparaison fournisseurs est déjà couverte à 100% par l'intent "fournisseur"
existant (get_meilleur_fournisseur retourne un ranking par kg DESC + rendement DESC,
et _build_fournisseur_payload produit les chart datasets). Le présent handler ne duplique
pas cette logique. Si l'utilisateur demande "quel fournisseur est le meilleur ?",
le NLP doit router vers "fournisseur".
"""
from __future__ import annotations

import logging
from typing import Any

from app.database import get_db_connection
from app.domain.chat import ChatQuery, IntentResult
from app.services.intent.base import IntentHandler
from app.services.chatbot_service import ChatbotService

logger = logging.getLogger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _fmt(value: Any, decimals: int = 0) -> str:
    try:
        n = float(value or 0)
        return f"{n:,.{decimals}f}".replace(",", " ")
    except (TypeError, ValueError):
        return str(value or "N/D")


def _medal(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")


class _CampaignComparator:
    """Compare les campagnes entre elles."""

    def __init__(self, service: ChatbotService):
        self.service = service

    @staticmethod
    def _detect_metric(message: str) -> tuple[str, str, str]:
        m = message.lower()
        if any(kw in m for kw in ["production", "huile", "litre", "produit"]):
            return "production_litres", "production (litres d'huile)", "L"
        if any(kw in m for kw in ["rendement", "performance", "taux", "extraction"]):
            return "rendement", "rendement moyen (%)", "%"
        if any(kw in m for kw in ["lot", "nombre de lot"]):
            return "nb_lots", "nombre de lots", "lots"
        return "total_olives_kg", "olives reçues (kg)", "kg"

    def run(self, query: ChatQuery) -> IntentResult:
        result = self.service.get_campagnes(
            huilerie=query.huilerie,
            enterprise_id=query.enterprise_id,
            annee=None,
        )
        rows: list[dict] = result.get("value") or []

        if not rows:
            return IntentResult(
                text="Aucune campagne trouvée pour effectuer une comparaison.",
                data=[],
                structured_payload=None,
            )

        metric_key, metric_label, unit = self._detect_metric(query.message)

        if metric_key == "production_litres":
            for row in rows:
                prod = self.service.get_production(
                    huilerie=row.get("huilerie_nom"),
                    start_date=str(row["date_debut"]) if row.get("date_debut") else None,
                    end_date=str(row["date_fin"]) if row.get("date_fin") else None,
                    enterprise_id=query.enterprise_id,
                )
                row["production_litres"] = _safe_float(prod.get("value"), 0.0)
        
        elif metric_key == "rendement":
            for row in rows:
                rend = self.service.get_rendement(
                    huilerie=row.get("huilerie_nom"),
                    start_date=str(row["date_debut"]) if row.get("date_debut") else None,
                    end_date=str(row["date_fin"]) if row.get("date_fin") else None,
                    enterprise_id=query.enterprise_id,
                )
                row["rendement"] = _safe_float(rend.get("value"), 0.0)

        sorted_rows = sorted(rows, key=lambda r: _safe_float(r.get(metric_key), 0.0), reverse=True)
        best = sorted_rows[0]
        best_val = _safe_float(best.get(metric_key), 0.0)

        lines = []
        for i, r in enumerate(sorted_rows, 1):
            val = _safe_float(r.get(metric_key), 0.0)
            dec = 0 if unit in ("kg", "L", "lots") else 1
            lines.append(
                f"{_medal(i)} **{r.get('reference', '?')}** ({r.get('annee', '?')}) "
                f"— {r.get('huilerie_nom', '?')} : **{_fmt(val, dec)} {unit}** "
                f"| {r.get('nb_lots', 0)} lot(s) | {r.get('date_debut')} → {r.get('date_fin')}"
            )

        text = (
            f"**Comparaison des campagnes — {metric_label}** :\n\n"
            + "\n".join(lines)
            + f"\n\n📊 **Meilleure campagne** : {best.get('reference')} ({best.get('annee')}) "
            f"avec **{_fmt(best_val, 0)} {unit}**."
        )

        if len(sorted_rows) > 1:
            worst = sorted_rows[-1]
            worst_val = _safe_float(worst.get(metric_key), 0.0)
            diff = best_val - worst_val
            text += (
                f"\n📉 **Moins performante** : {worst.get('reference')} ({worst.get('annee')}) "
                f"avec **{_fmt(worst_val, 0)} {unit}** "
                f"(écart de **{_fmt(diff, 0)} {unit}**)."
            )

        labels = [f"{r.get('reference')} ({r.get('annee')})" for r in sorted_rows]
        datasets = [
            {
                "label": metric_label,
                "data": [_safe_float(r.get(metric_key), 0.0) for r in sorted_rows],
                "type": "bar",
            },
            {
                "label": "Nb lots",
                "data": [_safe_float(r.get("nb_lots"), 0.0) for r in sorted_rows],
                "type": "line",
            },
        ]

        return IntentResult(
            text=text,
            data=sorted_rows,
            structured_payload={"labels": labels, "datasets": datasets, "items": sorted_rows},
        )


class _PeriodComparator:
    """Compare deux périodes pour une même métrique."""

    def __init__(self, service: ChatbotService):
        self.service = service

    @staticmethod
    def _detect_metric(message: str) -> tuple[str, str]:
        m = message.lower()
        if any(kw in m for kw in ["production", "huile", "litre"]):
            return "production", "production (litres)"
        if any(kw in m for kw in ["rendement", "performance"]):
            return "rendement", "rendement moyen (%)"
        if any(kw in m for kw in ["stock"]):
            return "stock", "stock (kg)"
        if any(kw in m for kw in ["reception", "livraison", "arrivage"]):
            return "reception", "réceptions (kg)"
        return "production", "production (litres)"

    @staticmethod
    def _resolve_two_periods(message: str) -> list[tuple[str, str, str]]:
        from app.nlp.normalizer import resolve_period

        m = message.lower()
        periods = []

        period_map = [
            (["aujourd", "auj", "ce jour"], "aujourd_hui"),
            (["hier"], "hier"),
            (["cette semaine", "semaine en cours"], "cette_semaine"),
            (["semaine derniere", "semaine passee", "semaine précédente"], "semaine_derniere"),
            (["ce mois", "mois en cours", "mois-ci"], "ce_mois"),
            (["mois dernier", "mois passé", "mois précédent"], "mois_dernier"),
            (["2026"], "annee_2026"),
            (["2025"], "annee_2025"),
        ]

        for keywords, label in period_map:
            if any(kw in m for kw in keywords):
                start, end, text = resolve_period(label)
                periods.append((text, start, end))
            if len(periods) == 2:
                break

        return periods

    def run(self, query: ChatQuery) -> IntentResult:
        from app.nlp.normalizer import resolve_period

        metric, metric_label = self._detect_metric(query.message)
        periods = self._resolve_two_periods(query.message)

        if len(periods) < 2:
            s1, e1, l1 = resolve_period("ce_mois")
            s2, e2, l2 = resolve_period("mois_dernier")
            periods = [(l1, s1, e1), (l2, s2, e2)]

        results = []
        for label, start, end in periods[:2]:
            if metric == "production":
                r = self.service.get_production(query.huilerie, start, end, query.enterprise_id)
                val = _safe_float(r.get("value"), 0.0)
                unit = "L"
            elif metric == "rendement":
                r = self.service.get_rendement(query.huilerie, start, end, query.enterprise_id)
                val = _safe_float(r.get("value"), 0.0)
                unit = "%"
            elif metric == "stock":
                r = self.service.get_stock(query.huilerie, start, end, query.enterprise_id)
                rows = r.get("value") or []
                val = sum(_safe_float(row.get("total_stock"), 0.0) for row in rows)
                unit = "kg"
            else:
                r = self.service.get_reception(query.huilerie, start, end, query.enterprise_id)
                val = _safe_float(r.get("total_kg"), 0.0)
                unit = "kg"
            results.append({"label": label, "value": val, "unit": unit, "start": start, "end": end})

        if not results:
            return IntentResult(
                text="Impossible de comparer les périodes demandées.",
                data=[],
                structured_payload=None,
            )

        p1, p2 = results[0], results[1]
        v1, v2 = p1["value"], p2["value"]
        diff = v1 - v2
        pct = (diff / v2 * 100) if v2 > 0 else 0

        winner = p1["label"] if v1 >= v2 else p2["label"]
        direction = "📈 hausse" if diff >= 0 else "📉 baisse"

        text = (
            f"**Comparaison {metric_label}** :\n\n"
            f"• **{p1['label']}** : {_fmt(v1, 1)} {unit}\n"
            f"• **{p2['label']}** : {_fmt(v2, 1)} {unit}\n\n"
            f"{direction} de **{_fmt(abs(diff), 1)} {unit}** "
            f"({_fmt(abs(pct), 1)} %) — "
            f"**{winner}** est la meilleure période."
        )

        labels = [p1["label"], p2["label"]]
        datasets = [{"label": metric_label, "data": [v1, v2], "type": "bar"}]

        return IntentResult(
            text=text,
            data=results,
            structured_payload={"labels": labels, "datasets": datasets, "items": results},
        )


class _HuilerieComparator:
    """Compare les huileries de l'entreprise entre elles."""

    def __init__(self, service: ChatbotService):
        self.service = service

    @staticmethod
    def _detect_metric(message: str) -> tuple[str, str, str]:
        m = message.lower()
        if any(kw in m for kw in ["rendement"]):
            return "rendement", "rendement moyen (%)", "%"
        if any(kw in m for kw in ["stock"]):
            return "stock", "stock total (kg)", "kg"
        return "production", "production (litres)", "L"

    def _list_huileries(self, enterprise_id: int | None) -> list[str]:
        connection = cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            q = "SELECT nom FROM huilerie WHERE 1=1"
            params: list[Any] = []
            if enterprise_id:
                q += " AND entreprise_id = %s"
                params.append(enterprise_id)
            q += " ORDER BY nom"
            cursor.execute(q, params)
            return [row["nom"] for row in (cursor.fetchall() or [])]
        except Exception as exc:
            logger.warning("Failed to list huileries: %s", exc)
            return []
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def run(self, query: ChatQuery) -> IntentResult:
        huileries = self._list_huileries(query.enterprise_id)

        if not huileries:
            return IntentResult(
                text="Aucune huilerie trouvée pour effectuer une comparaison.",
                data=[],
                structured_payload=None,
            )

        metric, metric_label, unit = self._detect_metric(query.message)
        rows_data = []

        for nom in huileries:
            if metric == "production":
                # For huilerie comparison, use full history (no date filter) to show total production capability
                r = self.service.get_production(nom, None, None, query.enterprise_id)
                val = _safe_float(r.get("value"), 0.0)
            elif metric == "rendement":
                # For rendement comparison, use full history (no date filter)
                r = self.service.get_rendement(nom, None, None, query.enterprise_id)
                val = _safe_float(r.get("value"), 0.0)
            else:
                r = self.service.get_stock(nom, None, None, query.enterprise_id)
                stock_rows = r.get("value") or []
                val = sum(_safe_float(row.get("total_stock"), 0.0) for row in stock_rows)

            rows_data.append({"huilerie": nom, "value": val, "metric": metric})

        sorted_rows = sorted(rows_data, key=lambda r: r["value"], reverse=True)
        best = sorted_rows[0]

        lines = []
        for i, r in enumerate(sorted_rows, 1):
            dec = 1 if unit == "%" else 0
            lines.append(f"{_medal(i)} **{r['huilerie']}** : {_fmt(r['value'], dec)} {unit}")

        text = (
            f"**Comparaison des huileries — {metric_label}** :\n\n"
            + "\n".join(lines)
            + f"\n\n🏆 **Meilleure** : **{best['huilerie']}** avec {_fmt(best['value'], 0)} {unit}."
        )

        labels = [r["huilerie"] for r in sorted_rows]
        datasets = [{"label": metric_label, "data": [r["value"] for r in sorted_rows], "type": "bar"}]

        return IntentResult(
            text=text,
            data=sorted_rows,
            structured_payload={"labels": labels, "datasets": datasets, "items": sorted_rows},
        )


class ComparaisonHandler(IntentHandler):
    """Dispatcher pour toutes les comparaisons."""

    def __init__(self, service: ChatbotService):
        self.service = service
        self._campaign = _CampaignComparator(service)
        self._period = _PeriodComparator(service)
        self._huilerie = _HuilerieComparator(service)

    @staticmethod
    def _detect_subject(message: str) -> str:
        m = message.lower()
        if any(kw in m for kw in ["campagne", "saison", "récolte", "recolte"]):
            return "campagne"
        if any(kw in m for kw in ["huilerie", "moulin", "site", "usine"]):
            return "huilerie"
        if any(kw in m for kw in [
            " vs ", " versus ", "par rapport", "ce mois", "mois dernier",
            "cette semaine", "semaine derniere", "2025", "2026",
            "hier", "aujourd", "cette annee", "annee derniere"
        ]):
            return "periode"
        return "campagne"

    async def handle(self, query: ChatQuery) -> IntentResult:
        subject = self._detect_subject(query.message)

        if subject == "campagne":
            return self._campaign.run(query)
        if subject == "huilerie":
            return self._huilerie.run(query)
        if subject == "periode":
            return self._period.run(query)

        return self._campaign.run(query)
