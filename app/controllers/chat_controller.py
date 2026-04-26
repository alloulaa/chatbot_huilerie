import logging
from typing import Annotated

from fastapi import APIRouter, Header

from app.models import ChatRequest, ChatResponse
from app.nlp.entity_extractor import EntityExtractor
from app.nlp.intent_detector import detect_intent
from app.nlp.normalizer import resolve_period
from app.services.chatbot_service import ChatbotService
from app.services.permission_service import (
    get_user_enterprise_id,
    get_user_huilerie,
    get_user_permissions,
    is_admin,
    is_intent_allowed,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])
service = ChatbotService()
extractor = EntityExtractor()
SESSION_CONTEXT: dict[str, dict[str, str]] = {}


def _fmt_number(value: float | int | None, decimals: int = 0) -> str:
    number = float(value or 0)
    if decimals == 0:
        return f"{number:,.0f}".replace(",", " ")
    return f"{number:,.{decimals}f}".replace(",", " ")


def _build_scope_text(huilerie: str | None, period_text: str, enterprise_scoped: bool = False) -> str:
    if huilerie:
        return f"de l'huilerie {huilerie} pour {period_text}"
    if enterprise_scoped:
        return f"pour {period_text} (huileries de votre entreprise)"
    return f"pour {period_text} (toutes huileries)"


@router.post("/ask", response_model=ChatResponse)
def ask_chatbot(
    payload: ChatRequest,
    authorization: Annotated[str | None, Header()] = None,
):
    bearer_token = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip() or None

    effective_jwt = payload.jwt_token or payload.token or bearer_token
    auth_data = None
    user_is_admin = False
    user_huilerie = None
    user_enterprise_id = None
    applied_permissions = None

    if effective_jwt:
        auth_data = get_user_permissions(effective_jwt)

        if auth_data is None:
            return ChatResponse(
                intent="unknown",
                confidence=0.0,
                entities={},
                response="Token invalide ou expire",
                data=None,
                applied_scope=None,
                applied_permissions=None,
            )

        user_is_admin = is_admin(auth_data)
        user_huilerie = get_user_huilerie(auth_data, effective_jwt)
        user_enterprise_id = get_user_enterprise_id(auth_data)
        applied_permissions = auth_data.get("permissions", [])

    intent, confidence = detect_intent(payload.message)
    entities = extractor.extract(payload.message)

    if effective_jwt and auth_data and not user_is_admin and not auth_data.get("_auth_unavailable"):
        permissions = auth_data.get("permissions", [])
        if not is_intent_allowed(intent, permissions):
            return ChatResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                response="Acces refuse",
                data=None,
                applied_scope=None,
                applied_permissions=permissions,
            )

    session_ctx = SESSION_CONTEXT.get(payload.session_id, {})
    explicit_huilerie = entities.get("huilerie")
    explicit_period = entities.get("period_label")

    huilerie = explicit_huilerie or session_ctx.get("last_huilerie")
    period_label = explicit_period or session_ctx.get("last_period") or "today"

    if user_huilerie and not user_is_admin:
        huilerie = user_huilerie

    used_context_huilerie = explicit_huilerie is None and bool(session_ctx.get("last_huilerie"))
    used_context_period = explicit_period is None and bool(session_ctx.get("last_period"))

    start_date, end_date, period_text = resolve_period(period_label)

    SESSION_CONTEXT[payload.session_id] = {
        "last_huilerie": huilerie or "",
        "last_period": period_label,
    }

    context_note = ""
    if used_context_huilerie or used_context_period:
        huilerie_ctx = huilerie if huilerie else "toutes huileries"
        context_note = f" (contexte : huilerie {huilerie_ctx}, {period_text})"

    enterprise_scoped = bool(auth_data and user_enterprise_id is not None)
    scope_text = _build_scope_text(huilerie, period_text, enterprise_scoped)

    if intent == "stock":
        result = service.get_stock(huilerie, start_date, end_date, user_enterprise_id)
        rows = result.get("value") or []
        if not rows:
            response_text = f"Aucune donnee pour {period_text}.{context_note}"
        else:
            details = []
            for row in rows:
                variete = row.get("variete") or "Inconnue"
                quantite = row.get("total_stock", 0)
                details.append(f"- {variete} : {_fmt_number(quantite, 0)} kg")
            response_text = f"Stock {scope_text} :\n" + "\n".join(details) + context_note
        response_data = rows
    elif intent == "production":
        result = service.get_production(huilerie, start_date, end_date, user_enterprise_id)
        total = result.get("value", 0)
        if total <= 0:
            response_text = f"Aucune donnee pour {period_text}.{context_note}"
        else:
            response_text = f"La quantite d'huile produite {scope_text} est de {_fmt_number(total, 0)} litres{context_note}"
        response_data = {"total_production": total}
    elif intent == "machine":
        result = service.get_machines(huilerie, start_date, end_date, user_enterprise_id)
        rows = result.get("value") or []
        if not rows:
            response_text = f"Toutes les machines sont en bon etat {scope_text}{context_note}"
        else:
            details = [f"{row.get('nom_machine')} ({row.get('etat_machine')})" for row in rows]
            response_text = f"Machines necessitant attention {scope_text} : " + ", ".join(details) + context_note
        response_data = rows
    elif intent == "rendement":
        result = service.get_rendement(huilerie, start_date, end_date, user_enterprise_id)
        rendement = result.get("value", 0)
        if rendement <= 0:
            response_text = f"Aucune donnee pour {period_text}.{context_note}"
        else:
            response_text = f"Le rendement moyen reel {scope_text} est de {_fmt_number(rendement, 1)} %{context_note}"
        response_data = {"rendement_moyen": rendement}
    elif intent == "prediction":
        result = service.get_prediction(huilerie, start_date, end_date, user_enterprise_id)
        rendement = result.get("rendement_predit", 0)
        quantite = result.get("quantite_estimee", 0)
        if rendement <= 0 and quantite <= 0:
            response_text = f"Aucune donnee pour {period_text}.{context_note}"
        else:
            response_text = (
                f"Le rendement predit {scope_text} est de {_fmt_number(rendement, 1)} % "
                f"avec une production estimee de {_fmt_number(quantite, 0)} litres{context_note}"
            )
        response_data = result
    elif intent == "qualite":
        result = service.get_qualite(huilerie, start_date, end_date, user_enterprise_id)
        rows = result.get("value") or []
        summary = result.get("summary") or {}

        if not rows:
            response_text = f"Aucune donnee pour {period_text}.{context_note}"
            response_data = {"details": rows, "summary": summary}
            return ChatResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                response=response_text,
                data=response_data,
                applied_scope={"huilerie": huilerie, "enterprise_id": user_enterprise_id, "period_label": period_label, "start_date": start_date, "end_date": end_date},
                applied_permissions=applied_permissions,
            )

        bonne = int(summary.get("Bonne", 0))
        moyenne = int(summary.get("Moyenne", 0))
        mauvaise = int(summary.get("Mauvaise", 0))
        inconnue = int(summary.get("Inconnue", 0))

        response_text = (
            f"Qualite {scope_text} : Bonne ({bonne}), Moyenne ({moyenne}), Mauvaise ({mauvaise})"
        )
        if inconnue > 0:
            response_text += f", Inconnue ({inconnue})"
        response_text += context_note

        response_data = {
            "details": rows,
            "summary": summary,
        }
    elif intent == "diagnostic":
        result = service.diagnostic_qualite(huilerie, start_date, end_date, user_enterprise_id)
        issues = result.get("issues") or []
        rows = result.get("rows") or []
        if not rows:
            response_text = f"Aucune donnee pour {period_text}.{context_note}"
            response_data = result
            return ChatResponse(
                intent=intent,
                confidence=confidence,
                entities=entities,
                response=response_text,
                data=response_data,
                applied_scope={"huilerie": huilerie, "enterprise_id": user_enterprise_id, "period_label": period_label, "start_date": start_date, "end_date": end_date},
                applied_permissions=applied_permissions,
            )
        if issues:
            response_text = f"La qualite est faible {scope_text} en raison de : " + ", ".join(issues) + context_note
        else:
            response_text = f"Tous les parametres sont conformes {scope_text}{context_note}"
        response_data = result
    else:
        logger.info("Intent non reconnue pour le message: %s", payload.message)
        response_text = "Je n'ai pas compris la demande. Essayez avec stock, production, machine, rendement, prediction, qualite ou diagnostic."
        response_data = None

    return ChatResponse(
        intent=intent,
        confidence=confidence,
        entities=entities,
        response=response_text,
        data=response_data,
        applied_scope={"huilerie": huilerie, "enterprise_id": user_enterprise_id, "period_label": period_label, "start_date": start_date, "end_date": end_date},
        applied_permissions=applied_permissions,
    )
