"""
Handler pour l'intent MACHINE (état des machines).
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


class MachineHandler(IntentHandler):
    """Handler pour traiter les requêtes sur l'état des machines."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête d'état de machines."""
        result = self.service.get_machines(query.huilerie, query.start_date, query.end_date, query.enterprise_id)
        rows = result.get("value") or []
        
        if not rows:
            text = f"Toutes les machines sont opérationnelles."
            return IntentResult(text=text, data=[], structured_payload=None)
        
        lines = [
            f"- **{r.get('nomMachine') or r.get('nom_machine') or r.get('nom', 'Machine inconnue')}** : "
            f"{r.get('etatMachine') or r.get('etat_machine') or r.get('etat', 'INCONNU')}"
            for r in rows
        ]
        text = f"Machines nécessitant attention :\n" + "\n".join(lines)
        
        return IntentResult(text=text, data=rows, structured_payload=None)
