"""
Handler pour l'intent MACHINE (état des machines).
"""
from app.services.intent.base import IntentHandler
from app.domain.chat import ChatQuery, IntentResult
from app.services.query_service import ChatbotService


_ETAT_ICONS = {
    "en_service":     "✅",
    "EN_SERVICE":     "✅",
    "en service":     "✅",
    "maintenance":    "🔧",
    "en maintenance": "🔧",
    "EN_MAINTENANCE": "🔧",
    "hors_service":   "❌",
    "HORS_SERVICE":   "❌",
    "hors service":   "❌",
}


def _icon(etat: str | None) -> str:
    return _ETAT_ICONS.get(str(etat or ""), "❓")


class MachineHandler(IntentHandler):
    """Handler pour traiter les requêtes sur l'état des machines."""

    def __init__(self, service: ChatbotService):
        self.service = service

    async def handle(self, query: ChatQuery) -> IntentResult:
        """Traiter une requete d'état de machines."""
        message_lower = query.message.lower()
        is_panne_request = any(word in message_lower for word in [
            "en panne", "panne", "hors service", "maintenance"
        ])
        is_list_request = (not is_panne_request) and any(word in message_lower for word in [
            "liste", "toutes", "tous", "toutes les", "tous les",
            "quelles machines", "machines disponibles", "inventaire machines"
        ])
        requested_status = "maintenance" if is_panne_request else None
        query_start_date = query.start_date if query.explicit_period else None
        query_end_date = query.end_date if query.explicit_period else None

        if is_list_request:
            result = self.service.get_all_machines(query.huilerie, query.enterprise_id)
            rows = result.get("value") or []

            if not rows:
                return IntentResult(text="Aucune machine trouvée.", data=[], structured_payload=None)

            if query.huilerie:
                items = "\n".join(
                    f"- {_icon(r.get('etatMachine'))} **{r.get('nomMachine')}** — {r.get('etatMachine')}"
                    for r in rows
                )
                text = f"🏭 Machines de **{query.huilerie}** ({len(rows)}) :\n{items}"
            else:
                huilerie_groups: dict = {}
                for r in rows:
                    h = r.get('huilerie', 'Huilerie inconnue')
                    huilerie_groups.setdefault(h, []).append(r)

                sections = []
                for h, machines in huilerie_groups.items():
                    items = "\n".join(
                        f"- {_icon(r.get('etatMachine'))} **{r.get('nomMachine')}** — {r.get('etatMachine')}"
                        for r in machines
                    )
                    sections.append(f"**🏭 {h}** ({len(machines)}) :\n{items}")

                text = "\n\n".join(sections)

            return IntentResult(text=text, data=rows, structured_payload=None)

        else:
            result = self.service.get_machines(
                query.huilerie,
                query_start_date,
                query_end_date,
                query.enterprise_id,
                status_filter=requested_status,
            )
            rows = result.get("value") or []

            if not rows:
                if requested_status:
                    return IntentResult(text="✅ Aucune machine en maintenance.", data=[], structured_payload=None)
                else:
                    return IntentResult(text="✅ Toutes les machines sont opérationnelles.", data=[], structured_payload=None)

            items = "\n".join(
                f"- {_icon(r.get('etatMachine') or r.get('etat_machine'))} "
                f"**{r.get('nomMachine') or r.get('nom_machine') or r.get('nom', 'Machine inconnue')}** — "
                f"{r.get('etatMachine') or r.get('etat_machine') or r.get('etat', 'INCONNU')}"
                for r in rows
            )

            if requested_status:
                text = f"🔧 Machines en panne ({len(rows)}) :\n{items}"
            else:
                text = f"🏭 Machines ({len(rows)}) :\n{items}"

            return IntentResult(text=text, data=rows, structured_payload=None)