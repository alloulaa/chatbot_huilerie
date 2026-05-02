"""
Handler pour l'intent DIAGNOSTIC.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


class DiagnosticHandler(IntentHandler):
    """Handler pour traiter les requêtes de diagnostic qualité."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de diagnostic."""
        result = self.service.diagnostic_qualite(query.huilerie, query.start_date, query.end_date, query.enterprise_id)
        issues = result.get("issues") or []
        rows = result.get("rows") or []
        
        if not rows:
            text = f"Aucune analyse disponible pour diagnostic."
            return IntentResult(text=text, data=result, structured_payload=None)
        
        if issues:
            text = (
                f"Qualité insuffisante — causes identifiées : "
                + ", ".join(f"**{i}**" for i in issues) + "."
            )
        else:
            text = f"Tous les paramètres sont conformes."
        
        return IntentResult(text=text, data=result, structured_payload=None)
