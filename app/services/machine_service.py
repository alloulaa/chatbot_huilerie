from app.services.chatbot_service import ChatbotService


class MachineService:
    def __init__(self):
        self.chatbot = ChatbotService()

    def top_failed_machine(self, start_date: str, end_date: str, period_text: str, huilerie: str | None = None):
        result = self.chatbot.get_machines()
        return {"text": result["message"], "data": result.get("value")}

    def machine_state(self, code: str):
        result = self.chatbot.get_machines()
        data = result.get("value") or []
        for row in data:
            if str(row.get("machine", "")).upper() == code.upper():
                probleme = row.get("probleme") or "Aucun probleme signale"
                return {
                    "text": f"La machine {code} necessite attention: {probleme}.",
                    "data": row,
                }
        return {"text": f"Aucune machine trouvee avec le code {code}.", "data": None}
