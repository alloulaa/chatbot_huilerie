"""
Handler pour l'intent MOUVEMENT_STOCK.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


class MouvementStockHandler(IntentHandler):
    """Handler pour traiter les requêtes sur les mouvements de stock."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de mouvement de stock."""
        result = self.service.get_mouvements_stock(query.huilerie, query.start_date, query.end_date, query.enterprise_id)
        rows = result.get("value") or []
        
        if not rows:
            text = f"Aucun mouvement de stock disponible."
            return IntentResult(text=text, data=[], structured_payload=None)
        
        lines = [
            f"- **{r.get('type_mouvement')}** | lot {r.get('lot_ref')} | "
            f"{r.get('date_mouvement')} — {r.get('commentaire') or ''}"
            for r in rows[:8]
        ]
        
        extra = f" *(+{len(rows) - 8} autres)*" if len(rows) > 8 else ""
        text = f"Mouvements de stock :\n" + "\n".join(lines) + extra
        
        return IntentResult(text=text, data=rows, structured_payload=None)
