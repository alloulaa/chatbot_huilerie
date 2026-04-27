import logging

from app.nlp.analyseur_llm import analyser_message_sync
from app.services.chatbot_service import ChatbotService


class ChatService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.chatbot_service = ChatbotService()

    def process_message(self, message: str, user_id: int, session_id: str):
        resultat = analyser_message_sync(message)
        intent = str(resultat.get("intention") or "inconnu")
        confidence = float(resultat.get("confiance") or 0.5)

        if intent == "stock":
            payload = self.chatbot_service.get_stock()
        elif intent == "production":
            payload = self.chatbot_service.get_production()
        elif intent == "machine":
            payload = self.chatbot_service.get_machines()
        elif intent == "rendement":
            payload = self.chatbot_service.get_rendement()
        else:
            self.logger.info("Intent non reconnue pour message: %s", message)
            payload = {"message": "Je n'ai pas compris la demande. Essayez avec stock, production, machine ou rendement.", "value": None}

        if "message" not in payload:
            payload["message"] = "Demande traitee"

        return {
            "intent": intent,
            "confidence": confidence,
            "entities": resultat,
            "response": payload["message"],
            "data": {"value": payload.get("value")},
            "applied_scope": None,
        }
