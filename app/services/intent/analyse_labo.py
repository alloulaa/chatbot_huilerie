"""
Handler pour l'intent ANALYSE_LABO.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.query_service import ChatbotService


_ANOMALY_KEYWORDS = (
    "anormale",
    "anormales",
    "anomal",
    "anorm",
    "hors norme",
    "hors normes",
    "non conforme",
    "non conformes",
    "abnormal",
)


def _message_requests_anormales(message: str) -> bool:
    text = (message or "").lower()
    return any(keyword in text for keyword in _ANOMALY_KEYWORDS)


def _is_anormale_analysis(row: dict) -> bool:
    acidite = row.get("acidite_huile_pourcent")
    peroxyde = row.get("indice_peroxyde_meq_o2_kg")
    k270 = row.get("k270")
    k232 = row.get("k232")
    polyphenols = row.get("polyphenols_mg_kg")

    try:
        acidite = float(acidite)
    except (TypeError, ValueError):
        acidite = None
    try:
        peroxyde = float(peroxyde)
    except (TypeError, ValueError):
        peroxyde = None
    try:
        k270 = float(k270)
    except (TypeError, ValueError):
        k270 = None
    try:
        k232 = float(k232)
    except (TypeError, ValueError):
        k232 = None
    try:
        polyphenols = float(polyphenols)
    except (TypeError, ValueError):
        polyphenols = None

    if acidite is not None and acidite > 0.8:
        return True
    if peroxyde is not None and (peroxyde < 5.0 or peroxyde > 40.0):
        return True
    if k270 is not None and k270 > 0.22:
        return True
    if k232 is not None and (k232 < 1.5 or k232 > 3.5):
        return True
    if polyphenols is not None and (polyphenols < 100.0 or polyphenols > 800.0):
        return True
    return False


def _fmt(value: float, decimals: int = 2) -> str:
    """Formater un nombre pour l'affichage."""
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}".replace(",", " ")
    return str(value)


class AnalyseLaboHandler(IntentHandler):
    """Handler pour traiter les requêtes sur les analyses laboratoires."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête d'analyses laboratoires."""
        extra_context = getattr(query, "extra_context", {}) or {}
        lot_ref = (
            extra_context.get("lot_reference")
            or extra_context.get("reference_lot")
            or extra_context.get("code_lot")
            or getattr(query, "code_lot", None)
            or getattr(query, "reference_lot", None)
            or getattr(query, "lot_reference", None)
        )
        query_start_date = query.start_date if query.explicit_period else None
        query_end_date = query.end_date if query.explicit_period else None
        result = self.service.get_analyse_labo(query.huilerie, query_start_date, query_end_date, query.enterprise_id, lot_ref)
        rows = result.get("value") or []
        rows = [row for row in rows if _is_anormale_analysis(row)]
        
        if not rows:
            text = "Aucune analyse anormale disponible."
            return IntentResult(text=text, data=[], structured_payload=None)
        
        lines = []
        for r in rows[:8]:
            lines.append(
                f"- Lot **{r.get('lot_ref')}** ({r.get('date_analyse')}) – "
                f"acidité {_fmt(r.get('acidite_huile_pourcent'), 2)} %, "
                f"peroxyde {_fmt(r.get('indice_peroxyde_meq_o2_kg'), 1)}, "
                f"K270 {_fmt(r.get('k270'), 3)}"
            )
        
        extra = f" *(+{len(rows) - 8} autres)*" if len(rows) > 8 else ""
        text = f"Analyses laboratoires :\n" + "\n".join(lines) + extra
        
        labels = [r.get('lot_ref', 'Lot') for r in rows]
        structured_payload = {
            "labels": labels,
            "items": rows,
            "datasets": [{
                "label": "Acidité %",
                "data": [r.get('acidite_huile_pourcent', 0) for r in rows],
                "backgroundColor": "#FF5722"
            }]
        }
        
        return IntentResult(
            text=text,
            data=rows,
            structured_payload=structured_payload
        )

