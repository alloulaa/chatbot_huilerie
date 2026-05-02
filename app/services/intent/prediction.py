"""
Handler pour l'intent PREDICTION.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


def _fmt(value: float, decimals: int = 2) -> str:
    """Formater un nombre pour l'affichage."""
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}".replace(",", " ")
    return str(value)


class PredictionHandler(IntentHandler):
    """Handler pour traiter les requêtes de prédiction."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de prédiction."""
        result = self.service.get_prediction(query.huilerie, query.start_date, query.end_date, query.enterprise_id)
        rend = result.get("rendement_predit", 0)
        qte = result.get("quantite_estimee", 0)
        
        if rend <= 0 and qte <= 0:
            text = f"Aucune prédiction disponible."
            return IntentResult(text=text, data=result, structured_payload=None)
        
        text = (
            f"Prédiction : rendement prédit **{_fmt(rend, 1)} %**, "
            f"production estimée **{_fmt(qte)} litres**."
        )
        return IntentResult(text=text, data=result, structured_payload=None)
