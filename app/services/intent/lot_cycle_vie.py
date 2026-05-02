"""
Handler pour l'intent LOT_CYCLE_VIE.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


class LotCycleVieHandler(IntentHandler):
    """Handler pour traiter les requêtes sur le cycle de vie d'un lot."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de cycle de vie d'un lot."""
        lot_ref = query.code_lot or query.reference_lot or query.lot_reference
        
        if not lot_ref:
            text = (
                "Précisez la référence du lot. Exemple : "
                "\"cycle de vie du lot LO07\" ou \"donne-moi le cycle de vie de lot15\"."
            )
            return IntentResult(text=text, data=None, structured_payload=None)
        
        result = self.service.get_lot_cycle_vie(lot_reference=lot_ref)
        if result.get("error"):
            return IntentResult(text=result["error"], data=None, structured_payload=None)
        
        lot_info = result["lot"]
        steps = result["steps"]
        nb = len(steps)
        remaining_steps = [step.get("etape") for step in steps[1:] if step.get("etape")]
        history_text = " → ".join(remaining_steps) if remaining_steps else "aucune étape supplémentaire"
        text = (
            f"Cycle de vie du lot **{lot_ref}** "
            f"({lot_info.get('variete', '?')}, fournisseur : {lot_info.get('fournisseur_nom', '?')}) :\n"
            f"{nb} étape(s) retracée(s) — réception → {history_text}."
        )
        
        return IntentResult(text=text, data=result, structured_payload=None)
