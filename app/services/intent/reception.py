"""
Handler pour l'intent RECEPTION.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


def _fmt(value: float, decimals: int = 2) -> str:
    """Formater un nombre pour l'affichage."""
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}".replace(",", " ")
    return str(value)


class ReceptionHandler(IntentHandler):
    """Handler pour traiter les requêtes sur les réceptions."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de réception."""
        result = self.service.get_reception(query.huilerie, query.start_date, query.end_date, query.enterprise_id)
        rows = result.get("value") or []
        total = result.get("total_kg", 0)
        
        if not rows:
            text = f"Aucune réception enregistrée."
            return IntentResult(text=text, data=result, structured_payload=None)
        
        lines = [
            f"- Lot **{r.get('reference')}** | {r.get('variete')} | "
            f"{r.get('fournisseur_nom')} | {_fmt(r.get('quantite_initiale'))} kg | "
            f"{r.get('date_reception')}"
            for r in rows[:8]
        ]
        
        extra = f" *(+{len(rows) - 8} autres)*" if len(rows) > 8 else ""
        text = (
            f"Réceptions — total **{_fmt(total)} kg** :\n"
            + "\n".join(lines) + extra
        )
        
        return IntentResult(text=text, data=result, structured_payload=None)
