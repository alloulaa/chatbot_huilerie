"""
Handler pour l'intent FOURNISSEUR.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


def _fmt(value: float, decimals: int = 2) -> str:
    """Formater un nombre pour l'affichage."""
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}".replace(",", " ")
    return str(value)


class FournisseurHandler(IntentHandler):
    """Handler pour traiter les requêtes sur les fournisseurs."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de fournisseurs."""
        # Appliquer dates seulement si période explicite
        query_start_date = query.start_date if query.explicit_period else None
        query_end_date = query.end_date if query.explicit_period else None
        
        result = self.service.get_meilleur_fournisseur(
            query.huilerie,
            query_start_date,
            query_end_date,
            query.enterprise_id
        )
        rows = result.get("value") or []
        
        if not rows:
            text = f"Aucune donnée fournisseur disponible."
            return IntentResult(text=text, data=[], structured_payload=None)
        
        lines = []
        for i, r in enumerate(rows[:8], 1):
            acid_flag = " ⚠️" if r.get("acidite_status") == "out of range" else ""
            rend_flag = " ⚠️" if r.get("rendement_status") == "out of range" else ""
            lines.append(
                f"{i}. **{r.get('fournisseur_nom', 'Fournisseur')}** — {r.get('lots', 0)} lot(s), "
                f"{_fmt(r.get('kg', 0))} kg, rendement {_fmt(r.get('rendement', 0), 1)} %{rend_flag}, "
                f"acidité {_fmt(r.get('acidity', 0), 2)} %{acid_flag}"
            )
        
        extra = f" *(+{len(rows) - 8} autres)*" if len(rows) > 8 else ""
        text = f"Classement fournisseurs :\n" + "\n".join(lines) + extra
        
        # Payload structuré
        labels = [r.get('fournisseur_nom', 'Fournisseur') for r in rows]
        structured_payload = {
            "labels": labels,
            "items": rows,
            "datasets": [
                {
                    "label": "Kg livrés",
                    "data": [r.get('kg', 0) for r in rows],
                    "backgroundColor": "#4CAF50"
                },
                {
                    "label": "Acidité %",
                    "data": [r.get('acidity', 0) for r in rows],
                    "backgroundColor": "#FF5722"
                }
            ]
        }
        
        return IntentResult(
            text=text,
            data=rows,
            structured_payload=structured_payload
        )
