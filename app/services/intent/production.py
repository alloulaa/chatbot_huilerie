"""
Handler pour l'intent PRODUCTION.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


def _fmt(value: float, decimals: int = 2) -> str:
    """Formater un nombre pour l'affichage."""
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}".replace(",", " ")
    return str(value)


class ProductionHandler(IntentHandler):
    """Handler pour traiter les requêtes sur la production."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de production."""
        query_start_date = query.start_date if query.explicit_period else None
        query_end_date = query.end_date if query.explicit_period else None
        
        result = self.service.get_production(query.huilerie, query_start_date, query_end_date, query.enterprise_id)
        total = result.get("value", 0)
        
        if total <= 0:
            text = f"Aucune production enregistrée."
            return IntentResult(text=text, data=result, structured_payload=None)
        
        text = f"Production : **{_fmt(total)} litres** d'huile."
        return IntentResult(text=text, data=result, structured_payload=None)
