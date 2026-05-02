"""
Handler pour l'intent STOCK.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


def _fmt(value: float, decimals: int = 2) -> str:
    """Formater un nombre pour l'affichage."""
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}".replace(",", " ")
    return str(value)


class StockHandler(IntentHandler):
    """Handler pour traiter les requêtes sur le stock."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de stock."""
        # Stock ne prend jamais de filtres de date
        result = self.service.get_stock(
            query.huilerie,
            None,  # pas de start_date
            None,  # pas de end_date
            query.enterprise_id
        )
        rows = result.get("value") or []
        
        if not rows:
            scope_part = f" pour l'huilerie **{query.huilerie}**" if query.huilerie else ""
            text = f"Aucune donnée de stock disponible{scope_part}."
            return IntentResult(text=text, data=[], structured_payload=None)
        
        # Texte résumé
        lines = []
        for r in rows:
            ref  = r.get("reference_stock") or "N/D"
            var  = r.get("variete") or "Inconnue"
            qte  = r.get("quantite_disponible") or r.get("total_stock") or 0
            lot  = r.get("lot_reference") or ""
            lot_part = f" | lot : **{lot}**" if lot else ""
            lines.append(f"- **{ref}** | {var} | **{_fmt(qte)} kg**{lot_part}")
        
        scope_part = f" de l'huilerie **{query.huilerie}**" if query.huilerie else ""
        text = f"Stock{scope_part} :\n" + "\n".join(lines)
        
        # Payload structuré pour graphique
        labels = [item.get("reference_stock", "N/D") for item in rows]
        structured_payload = {
            "labels": labels,
            "items": rows,
            "value": rows,
            "datasets": [{
                "label": "Quantité disponible (kg)",
                "data": [item.get("quantite_disponible", 0) for item in rows],
                "backgroundColor": "#4CAF50",
                "borderColor": "#2E7D32",
                "borderWidth": 1
            }]
        }
        
        return IntentResult(
            text=text,
            data=rows,
            structured_payload=structured_payload
        )
