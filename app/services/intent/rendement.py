"""
Handler pour l'intent RENDEMENT.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


def _fmt(value: float, decimals: int = 2) -> str:
    """Formater un nombre pour l'affichage."""
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}".replace(",", " ")
    return str(value)


class RendementHandler(IntentHandler):
    """Handler pour traiter les requêtes sur le rendement."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de rendement."""
        query_start_date = query.start_date if query.explicit_period else None
        query_end_date = query.end_date if query.explicit_period else None
        
        result = self.service.get_rendement(query.huilerie, query_start_date, query_end_date, query.enterprise_id)
        rend = result.get("value", 0)
        
        if rend <= 0:
            text = f"Aucune donnée de rendement disponible."
            return IntentResult(text=text, data=result, structured_payload=None)
        
        text = f"Rendement moyen : **{_fmt(rend, 1)} %**."
        return IntentResult(text=text, data=result, structured_payload=None)
