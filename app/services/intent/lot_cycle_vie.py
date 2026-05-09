"""
Handler pour l'intent LOT_CYCLE_VIE.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.query_service import ChatbotService


class LotCycleVieHandler(IntentHandler):
    """Handler pour traiter les requÃªtes sur le cycle de vie d'un lot."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requÃªte de cycle de vie d'un lot."""
        extra_context = getattr(query, "extra_context", {}) or {}
        lot_ref = (
            extra_context.get("lot_reference")
            or extra_context.get("reference_lot")
            or extra_context.get("code_lot")
            or getattr(query, "code_lot", None)
            or getattr(query, "reference_lot", None)
            or getattr(query, "lot_reference", None)
        )
        
        if not lot_ref:
            text = (
                "PrÃ©cisez la rÃ©fÃ©rence du lot. Exemple : "
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
        history_text = " â†’ ".join(remaining_steps) if remaining_steps else "aucune Ã©tape supplÃ©mentaire"
        text = (
            f"Cycle de vie du lot **{lot_ref}** "
            f"({lot_info.get('variete', '?')}, fournisseur : {lot_info.get('fournisseur_nom', '?')}) :\n"
            f"{nb} Ã©tape(s) retracÃ©e(s) â€” rÃ©ception â†’ {history_text}."
        )
        
        return IntentResult(text=text, data=result, structured_payload=None)

