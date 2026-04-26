import logging

from fastapi import APIRouter

from app.models import ChatRequest, ChatResponse
from app.nlp.intent_detector import detect_intent
from app.services.chatbot_service import ChatbotService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])
service = ChatbotService()


@router.post("/ask", response_model=ChatResponse)
def ask_chatbot(payload: ChatRequest):
    intent, confidence = detect_intent(payload.message)

    if intent == "stock":
        result = service.get_stock()
    elif intent == "production":
        result = service.get_production()
    elif intent == "machines":
        result = service.get_machines()
    elif intent == "rendement":
        result = service.get_rendement()
    else:
        logger.info("Intent non reconnue pour le message: %s", payload.message)
        result = {"message": "Je n'ai pas compris la demande. Essayez avec stock, production, machine ou rendement.", "value": None}

    return ChatResponse(
        intent=intent,
        confidence=confidence,
        entities={},
        response=result["message"],
        data={"value": result.get("value")},
        applied_scope=None,
    )
