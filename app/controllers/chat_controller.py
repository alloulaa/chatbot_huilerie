import logging
from typing import Annotated

from fastapi import APIRouter, Header

from app.models import ChatRequest, ChatResponse
from app.nlp.normalizer import resolve_period
from app.services.chat_service import ChatService
from app.services.auth_helper import resolve_auth
from app.services.session_service import SessionService
from app.services.response_builder import build_chat_response
from app.services.permission_service import is_huilerie_allowed

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter(prefix="/chat", tags=["chat"])


def _huilerie_belongs_to_enterprise(
    huilerie_name: str | None, enterprise_id: int | None
) -> bool:
    """Check if a huilerie name belongs to a given enterprise.

    Returns True if validation passes or cannot be performed.
    Returns False if huilerie explicitly does NOT belong to enterprise.
    """
    if not huilerie_name or not enterprise_id:
        return True

    # Use the permission service validator
    return is_huilerie_allowed(huilerie_name, enterprise_id, jwt_token=None)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/ask", response_model=ChatResponse)
async def ask_chatbot(
    payload: ChatRequest,
    authorization: Annotated[str | None, Header()] = None,
):
    # â”€â”€ Auth â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip() or None

    jwt = payload.jwt_token or payload.token or bearer
    auth = resolve_auth(jwt)

    if auth.error:
        return ChatResponse(
            type="text",
            message=auth.error,
            intent="unknown",
            confidence=0.0,
            entities={},
            response=auth.error,
            data=None,
            applied_scope={},
            applied_permissions=None,
        )

    user_is_admin = auth.is_admin
    user_huilerie = auth.huilerie
    user_enterprise_id = auth.enterprise_id
    applied_perms = auth.permissions
    auth_available = auth.auth_available

    # â”€â”€ Session setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    session_service = SessionService()

    # â”€â”€ ChatService orchestration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    chat_service = ChatService()
    service_result = await chat_service.process_message(
        message=payload.message,
        session_id=payload.session_id,
        huilerie=None,  # ChatService extracts from NLP
        enterprise_id=user_enterprise_id,
        permissions=auth.permissions,
        user_is_admin=user_is_admin,
        extra_context={
            "prediction_payload": getattr(payload, "prediction_payload", None)
        },
        auth_available=auth_available,
    )

    # â”€â”€ Check for service errors â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if service_result.get("error"):
        return ChatResponse(
            type="text",
            message=service_result["text"],
            intent=service_result["intent"],
            confidence=service_result["confidence"],
            entities=service_result.get("entities", {}),
            response=service_result["text"],
            data=None,
            applied_scope={},
            applied_permissions=applied_perms,
        )

    # â”€â”€ Validation: explicit huilerie must belong to enterprise â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    explicit_huilerie = service_result["entities"].get("huilerie")
    if explicit_huilerie and user_enterprise_id:
        if not _huilerie_belongs_to_enterprise(explicit_huilerie, user_enterprise_id):
            return ChatResponse(
                type="text",
                message=f"L'huilerie '{explicit_huilerie}' n'appartient pas Ã  votre entreprise ou n'existe pas.",
                intent=service_result["intent"],
                confidence=service_result["confidence"],
                entities=service_result.get("entities", {}),
                response=f"L'huilerie '{explicit_huilerie}' n'appartient pas Ã  votre entreprise ou n'existe pas.",
                data=None,
                applied_scope={},
                applied_permissions=applied_perms,
            )

    # â”€â”€ Update session context â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ctx = session_service.get(payload.session_id)
    resolved_huilerie = explicit_huilerie or ctx.get("last_huilerie") or None
    if user_huilerie and not user_is_admin:
        resolved_huilerie = user_huilerie

    period_label = (
        service_result["entities"].get("period_label")
        or ctx.get("last_period")
        or "aujourd_hui"
    )
    session_service.update(
        payload.session_id,
        {
            "last_huilerie": resolved_huilerie or "",
            "last_period": period_label,
        },
    )

    # â”€â”€ Build applied_scope â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    start_date, end_date, _ = resolve_period(period_label)
    applied_scope = {
        "huilerie": resolved_huilerie,
        "enterprise_id": user_enterprise_id,
        "period_label": period_label,
        "start_date": start_date,
        "end_date": end_date,
    }

    # â”€â”€ Build ChatResponse â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    return build_chat_response(
        session_service=session_service,
        session_id=payload.session_id,
        payload_message=payload.message,
        intent=service_result["intent"],
        confidence=service_result["confidence"],
        entities=service_result.get("entities", {}),
        response_text=service_result["text"],
        response_data=service_result["data"],
        applied_scope=applied_scope,
        applied_permissions=applied_perms,
    )
