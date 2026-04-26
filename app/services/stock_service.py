from app.services.chatbot_service import ChatbotService


class StockService:
    def __init__(self):
        self.chatbot = ChatbotService()

    def current_stock(self, huilerie: str | None = None, type_huile: str | None = None):
        result = self.chatbot.get_stock()
        return {
            "text": result["message"],
            "data": {"metric": "stock", "value": result.get("value"), "unit": "L"},
        }
