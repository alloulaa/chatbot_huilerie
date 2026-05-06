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
        # Check if user is asking for a complete list vs status/issues
        message_lower = query.message.lower()
        is_list_request = any(word in message_lower for word in [
            "liste", "toutes", "tous", "toutes les", "tous les", 
            "quelles machines", "machines disponibles", "inventaire machines"
        ])
        is_panne_request = any(word in message_lower for word in [
            "en panne", "panne", "hors service"
        ])
        requested_status = "maintenance" if is_panne_request else None
        
        if is_list_request:
            # Return complete list of machines
            result = self.service.get_all_machines(query.huilerie, query.enterprise_id)
            rows = result.get("value") or []
            
            if not rows:
                text = f"Aucune machine trouvée."
                return IntentResult(text=text, data=[], structured_payload=None)
            
            # Group by huilerie if admin, otherwise just list
            if query.huilerie:
                # Single huilerie
                lines = [
                    f"- **{r.get('nomMachine')}** : {r.get('etatMachine')}"
                    for r in rows
                ]
                text = f"Machines de l'huilerie {query.huilerie} :\n" + "\n".join(lines)
            else:
                # Multiple huileries - group by huilerie
                huilerie_groups = {}
                for r in rows:
                    huilerie = r.get('huilerie', 'Huilerie inconnue')
                    if huilerie not in huilerie_groups:
                        huilerie_groups[huilerie] = []
                    huilerie_groups[huilerie].append(r)
                
                sections = []
                for huilerie, machines in huilerie_groups.items():
                    section_lines = [f"**{huilerie}**:"]
                    section_lines.extend([
                        f"  - {r.get('nomMachine')} : {r.get('etatMachine')}"
                        for r in machines
                    ])
                    sections.append("\n".join(section_lines))
                
                text = "Liste des machines :\n\n" + "\n\n".join(sections)
            
            return IntentResult(text=text, data=rows, structured_payload=None)
        else:
            # Return machines with issues (original behavior)
            result = self.service.get_machines(
                query.huilerie,
                query.start_date,
                query.end_date,
                query.enterprise_id,
                status_filter=requested_status,
            )
            rows = result.get("value") or []
            
            if not rows:
                if requested_status:
                    text = f"Aucune machine en maintenance trouvée."
                else:
                    text = f"Toutes les machines sont opérationnelles."
                return IntentResult(text=text, data=[], structured_payload=None)
            
            lines = [
                f"- **{r.get('nomMachine') or r.get('nom_machine') or r.get('nom', 'Machine inconnue')}** : "
                f"{r.get('etatMachine') or r.get('etat_machine') or r.get('etat', 'INCONNU')}"
                for r in rows
            ]
            if requested_status:
                text = f"Machines en panne (état maintenance) :\n" + "\n".join(lines)
            else:
                text = f"Machines nécessitant attention :\n" + "\n".join(lines)
            
            return IntentResult(text=text, data=rows, structured_payload=None)
