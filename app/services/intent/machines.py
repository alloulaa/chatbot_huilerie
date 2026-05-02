"""
Handler pour l'intent MACHINES_UTILISEES.
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.chatbot_service import ChatbotService


def _fmt(value: float, decimals: int = 2) -> str:
    """Formater un nombre pour l'affichage."""
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}".replace(",", " ")
    return str(value)


class MachinesHandler(IntentHandler):
    """Handler pour traiter les requêtes sur les machines utilisées."""
    
    def __init__(self, service: ChatbotService):
        self.service = service
    
    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requête de machines utilisées."""
        # Appliquer dates seulement si période explicite
        query_start_date = query.start_date if query.explicit_period else None
        query_end_date = query.end_date if query.explicit_period else None
        
        result = self.service.get_machines_utilisees(
            query.huilerie,
            query_start_date,
            query_end_date,
            query.enterprise_id
        )
        rows = result.get("value") or []
        
        if not rows:
            text = f"Aucune donnée d'utilisation machines trouvée."
            return IntentResult(text=text, data=[], structured_payload=None)
        
        lines = []
        for r in rows[:5]:
            nom = r.get('nomMachine') or r.get('nom_machine') or r.get('nom', 'Machine inconnue')
            nb = r.get('nbExecutions') or r.get('nb_executions') or 0
            rend = r.get('rendementMoyen') or r.get('rendement_moyen') or 0.0
            total = r.get('totalProduit') or r.get('total_produit') or 0.0
            lines.append(
                f"- **{nom}** — {nb} exécution(s), "
                f"rendement {_fmt(rend, 1)} %, {_fmt(total)} L produits"
            )
        
        extra = f" *(+{len(rows) - 5} autres)*" if len(rows) > 5 else ""
        text = f"Machines les plus utilisées :\n" + "\n".join(lines) + extra
        
        # Payload structuré
        labels = [r.get('nomMachine') or r.get('nom_machine') or "Machine" for r in rows]
        structured_payload = {
            "labels": labels,
            "items": rows,
            "datasets": [
                {
                    "label": "Exécutions",
                    "data": [r.get('nbExecutions', 0) or r.get('nb_executions', 0) for r in rows],
                    "backgroundColor": "#2196F3"
                },
                {
                    "label": "Litre produits",
                    "data": [r.get('totalProduit', 0) or r.get('total_produit', 0) for r in rows],
                    "backgroundColor": "#FF9800"
                }
            ]
        }
        
        return IntentResult(
            text=text,
            data=rows,
            structured_payload=structured_payload
        )
