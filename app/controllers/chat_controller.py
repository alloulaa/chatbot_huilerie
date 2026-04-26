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
        rows = result.get("value") or []
        if not rows:
            response_text = "Le stock d'olives est vide"
        else:
            details = []
            for row in rows:
                variete = row.get("variete") or "Inconnue"
                quantite = row.get("total_stock", 0)
                details.append(f"- {variete} : {quantite} kg")
            response_text = "Stock actuel des olives :\n" + "\n".join(details)
        response_data = rows
    elif intent == "production":
        result = service.get_production()
        total = result.get("value", 0)
        response_text = f"La quantite d'huile produite est de {total} litres"
        response_data = {"total_production": total}
    elif intent == "machine":
        result = service.get_machines()
        rows = result.get("value") or []
        if not rows:
            response_text = "Toutes les machines sont en bon etat"
        else:
            details = [f"{row.get('nom_machine')} ({row.get('etat_machine')})" for row in rows]
            response_text = "Machines necessitant attention : " + ", ".join(details)
        response_data = rows
    elif intent == "rendement":
        result = service.get_rendement()
        rendement = result.get("value", 0)
        response_text = f"Le rendement moyen reel est de {rendement} %"
        response_data = {"rendement_moyen": rendement}
    elif intent == "prediction":
        result = service.get_prediction()
        rendement = result.get("rendement_predit", 0)
        quantite = result.get("quantite_estimee", 0)
        response_text = f"Le rendement predit est de {rendement} % avec une production estimee de {quantite} litres"
        response_data = result
    elif intent == "qualite":
        result = service.get_qualite()
        rows = result.get("value") or []
        summary = result.get("summary") or {}

        bonne = int(summary.get("Bonne", 0))
        moyenne = int(summary.get("Moyenne", 0))
        mauvaise = int(summary.get("Mauvaise", 0))
        inconnue = int(summary.get("Inconnue", 0))

        response_text = (
            f"Repartition qualite : Bonne ({bonne}), Moyenne ({moyenne}), Mauvaise ({mauvaise})"
        )
        if inconnue > 0:
            response_text += f", Inconnue ({inconnue})"

        response_data = {
            "details": rows,
            "summary": summary,
        }
    elif intent == "diagnostic":
        result = service.diagnostic_qualite()
        issues = result.get("issues") or []
        if issues:
            response_text = "La qualite est faible en raison de : " + ", ".join(issues)
        else:
            response_text = "Tous les parametres sont conformes"
        response_data = result
    else:
        logger.info("Intent non reconnue pour le message: %s", payload.message)
        response_text = "Je n'ai pas compris la demande. Essayez avec stock, production, machine, rendement, prediction, qualite ou diagnostic."
        response_data = None

    return ChatResponse(
        intent=intent,
        confidence=confidence,
        entities={},
        response=response_text,
        data=response_data,
        applied_scope=None,
    )
