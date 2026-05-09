"""
Handler pour l'intent QUALITE.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.query_service import ChatbotService


class QualiteHandler(IntentHandler):
    """Handler pour traiter les requÃªtes sur la qualitÃ©."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requÃªte de qualitÃ©."""
        query_start_date = query.start_date if query.explicit_period else None
        query_end_date = query.end_date if query.explicit_period else None
        
        result = self.service.get_qualite(query.huilerie, query_start_date, query_end_date, query.enterprise_id)
        rows = result.get("value") or []
        summary = result.get("summary", {})
        
        if not rows:
            text = f"Aucune donnÃ©e de qualitÃ© disponible."
            return IntentResult(text=text, data=result, structured_payload=None)
        
        parts = []
        for k in ("Bonne", "Moyenne", "Mauvaise", "Inconnue"):
            if summary.get(k, 0) > 0:
                parts.append(f"{k}: {summary[k]}")
        
        text = f"QualitÃ© des produits â€” " + ", ".join(parts)
        return IntentResult(text=text, data=result, structured_payload=None)

