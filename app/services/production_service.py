from app.services.chatbot_service import ChatbotService


class ProductionService:
    def __init__(self):
        self.chatbot = ChatbotService()

    def total_production(self, start_date: str, end_date: str, period_text: str, huilerie: str | None = None):
        result = self.chatbot.get_production()
        return {
            "text": result["message"],
            "data": {"metric": "production", "value": result.get("value"), "unit": "L"},
        }

    def average_yield(self, start_date: str, end_date: str, period_text: str, huilerie: str | None = None):
        result = self.chatbot.get_rendement()
        return {
            "text": result["message"],
            "data": {"metric": "rendement", "value": result.get("value"), "unit": "%"},
        }

    def quality_distribution(self, start_date: str, end_date: str, period_text: str, huilerie: str | None = None):
        return {"text": "Fonction non disponible dans cette version connectee aux vues SQL.", "data": []}

    def non_compliant_lots(self, start_date: str, end_date: str, period_text: str, huilerie: str | None = None):
        return {"text": "Fonction non disponible dans cette version connectee aux vues SQL.", "data": []}

    def global_kpis(self, start_date: str, end_date: str, period_text: str, huilerie: str | None = None):
        production = self.chatbot.get_production().get("value")
        rendement = self.chatbot.get_rendement().get("value")
        return {
            "text": f"KPI globaux: production {production} L, rendement moyen {rendement} %.",
            "data": {
                "production_totale": production,
                "rendement_moyen": rendement,
                "nb_lots": 0,
                "nb_extra": 0,
            },
        }
