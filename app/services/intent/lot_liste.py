"""
Handler pour l'intent LOT_LISTE.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


def _fmt(value: float, decimals: int = 2) -> str:
    """Formater un nombre pour l'affichage."""
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}".replace(",", " ")
    return str(value)


class LotListeHandler(IntentHandler):
    """Handler pour traiter les requêtes sur la liste des lots."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de liste de lots."""
        query_start_date = query.start_date if query.explicit_period else None
        query_end_date = query.end_date if query.explicit_period else None
        
        non_conf = any(kw in query.message.lower() for kw in ["non conforme", "lampante", "mauvaise"])
        result = self.service.get_lot_liste(
            query.huilerie, query_start_date, query_end_date, query.enterprise_id,
            variete=None,
            non_conformes_only=non_conf,
        )
        rows = result.get("value") or []
        
        if not rows:
            label = "lots non conformes" if non_conf else "lots"
            text = f"Aucun {label} trouvé."
            return IntentResult(text=text, data=[], structured_payload=None)
        
        lines = []
        for r in rows[:8]:
            lines.append(
                f"- **{r.get('reference')}** | {r.get('variete')} | "
                f"{r.get('fournisseur_nom')} | {_fmt(r.get('quantite_initiale'))} kg | "
                f"qualité : {r.get('qualite_huile') or 'N/D'}"
            )
        
        extra = f" *(+{len(rows) - 8} autres)*" if len(rows) > 8 else ""
        text = f"Lots :\n" + "\n".join(lines) + extra
        
        # Payload structuré
        labels = [r.get('reference', 'Lot') for r in rows]
        structured_payload = {
            "labels": labels,
            "items": rows,
            "datasets": [{
                "label": "Quantité initiale (kg)",
                "data": [r.get('quantite_initiale', 0) for r in rows],
                "backgroundColor": "#FF9800"
            }]
        }
        
        return IntentResult(
            text=text,
            data=rows,
            structured_payload=structured_payload
        )
