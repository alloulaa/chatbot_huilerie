import logging

from app.nlp.intent_detector import detect_intent
from app.services.chatbot_service import ChatbotService


class ChatService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.chatbot_service = ChatbotService()

    def process_message(self, message: str, user_id: int, session_id: str):
        intent, confidence = detect_intent(message)

        if intent == "stock":
            payload = self.chatbot_service.get_stock()
        elif intent == "production":
            payload = self.chatbot_service.get_production()
        elif intent == "machines":
            payload = self.chatbot_service.get_machines()
        elif intent == "rendement":
            payload = self.chatbot_service.get_rendement()
        else:
            self.logger.info("Intent non reconnue pour message: %s", message)
            payload = {"message": "Je n'ai pas compris la demande. Essayez avec stock, production, machine ou rendement.", "value": None}

        return {
            "intent": intent,
            "confidence": confidence,
            "entities": {},
            "response": payload["message"],
            "data": {"value": payload.get("value")},
            "applied_scope": None,
        }
