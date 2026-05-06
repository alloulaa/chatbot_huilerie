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
        message_lower = query.message.lower()
        
        # Check if asking for machines with poor performance/low yield
        is_poor_performance = any(word in message_lower for word in [
            "mauvais rendement", "rendement faible", "moins performant", 
            "performance faible", "efficacite faible", "moins utilisees",
            "moins utilisées", "sous-utilisees", "sous-utilisées"
        ])
        
        if is_poor_performance:
            # Get machines with poor performance (low usage or low yield)
            result = self.service.get_machines_utilisees(
                query.huilerie,
                query.start_date if query.explicit_period else None,
                query.end_date if query.explicit_period else None,
                query.enterprise_id
            )
            rows = result.get("value") or []
            
            if not rows:
                text = f"Aucune donnée de performance machines trouvée."
                return IntentResult(text=text, data=[], structured_payload=None)
            
            # Sort by lowest usage and lowest yield
            sorted_rows = sorted(rows, key=lambda x: (
                x.get('nbExecutions', 0), 
                x.get('rendementMoyen', 0)
            ))[:5]  # Bottom 5
            
            lines = []
            for r in sorted_rows:
                nom = r.get('nomMachine') or r.get('nom_machine') or r.get('nom', 'Machine inconnue')
                nb = r.get('nbExecutions') or r.get('nb_executions') or 0
                rend = r.get('rendementMoyen') or r.get('rendement_moyen') or 0.0
                lines.append(
                    f"- **{nom}** — {nb} exécution(s), "
                    f"rendement {_fmt(rend, 1)} %"
                )
            
            text = f"Machines avec les performances les plus faibles :\n" + "\n".join(lines)
            
            return IntentResult(text=text, data=sorted_rows, structured_payload=None)
        else:
            # Original behavior: most used machines
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
