"""
Handler pour l'intent CAMPAGNE.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


def _fmt(value: float, decimals: int = 2) -> str:
    """Formater un nombre pour l'affichage."""
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}".replace(",", " ")
    return str(value)


class CampagneHandler(IntentHandler):
    """Handler pour traiter les requêtes sur les campagnes."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de campagne."""
        annee = query.campagne_annee
        result = self.service.get_campagnes(query.huilerie, query.enterprise_id, annee)
        rows = result.get("value") or []
        
        if not rows:
            text = "Aucune campagne trouvée."
            return IntentResult(text=text, data=[], structured_payload=None)
        
        lines = []
        for r in rows:
            lines.append(
                f"- **{r.get('reference')}** ({r.get('annee')}) | "
                f"{r.get('huilerie_nom')} | "
                f"du {r.get('date_debut')} au {r.get('date_fin')} | "
                f"{r.get('nb_lots') or 0} lots | "
                f"{_fmt(r.get('total_olives_kg'))} kg"
            )
        
        text = "Campagnes :\n" + "\n".join(lines)
        return IntentResult(text=text, data=rows, structured_payload=None)
