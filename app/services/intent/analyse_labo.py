"""
Handler pour l'intent ANALYSE_LABO.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


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
        lot_ref = query.code_lot or query.reference_lot or query.lot_reference
        result = self.service.get_analyse_labo(query.huilerie, query.start_date, query.end_date, query.enterprise_id, lot_ref)
        rows = result.get("value") or []
        
        if not rows:
            text = f"Aucune analyse laboratoire disponible."
            return IntentResult(text=text, data=[], structured_payload=None)
        
        lines = []
        for r in rows[:8]:
            lines.append(
                f"- Lot **{r.get('lot_ref')}** ({r.get('date_analyse')}) — "
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
