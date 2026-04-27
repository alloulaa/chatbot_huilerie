import logging
from typing import Annotated

from fastapi import APIRouter, Header

from app.models import ChatRequest, ChatResponse
from app.nlp.analyseur_llm import analyser_message_sync
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
CONTEXTE_SESSION: dict[str, dict] = {}


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

    resultat = analyser_message_sync(payload.message)
    intention = str(resultat.get("intention") or "inconnu").strip().lower()
    try:
        confiance = float(resultat.get("confiance", 0.5))
    except (TypeError, ValueError):
        confiance = 0.5
    confiance = max(0.0, min(1.0, confiance))

    huilerie = resultat.get("huilerie")
    label_periode = resultat.get("periode")
    type_huile = resultat.get("type_huile")
    variete = resultat.get("variete")
    code_lot = resultat.get("code_lot")

    contexte = CONTEXTE_SESSION.get(payload.session_id, {})
    if not huilerie and contexte.get("derniere_huilerie"):
        huilerie = contexte["derniere_huilerie"]
    if not label_periode and contexte.get("derniere_periode"):
        label_periode = contexte["derniere_periode"]

    if user_huilerie and not user_is_admin:
        huilerie = user_huilerie

    date_debut, date_fin, texte_periode = resolve_period(label_periode)

    CONTEXTE_SESSION[payload.session_id] = {
        "derniere_huilerie": huilerie,
        "derniere_periode": label_periode,
    }

    entites = {
        "huilerie": huilerie,
        "periode": label_periode,
        "type_huile": type_huile,
        "variete": variete,
        "code_lot": code_lot,
    }

    if effective_jwt and auth_data and not user_is_admin and not auth_data.get("_auth_unavailable"):
        permissions = auth_data.get("permissions", [])
        if not is_intent_allowed(intention, permissions):
            return ChatResponse(
                intent=intention,
                confidence=confiance,
                entities=entites,
                response="Acces refuse",
                data=None,
                applied_scope=None,
                applied_permissions=permissions,
            )

    note_contexte = ""
    if contexte:
        huilerie_contexte = huilerie if huilerie else "toutes huileries"
        note_contexte = f" (contexte: huilerie {huilerie_contexte}, {texte_periode})"

    enterprise_scoped = bool(auth_data and user_enterprise_id is not None)
    scope_text = _build_scope_text(huilerie, texte_periode, enterprise_scoped)

    if intention == "stock":
        result = service.get_stock(huilerie=huilerie, start_date=date_debut, end_date=date_fin, enterprise_id=user_enterprise_id)
        rows = result.get("value") or []
        if not rows:
            response_text = f"Aucune donnee pour {texte_periode}.{note_contexte}"
        else:
            details = []
            for row in rows:
                variete = row.get("variete") or "Inconnue"
                quantite = row.get("total_stock", 0)
                details.append(f"- {variete} : {_fmt_number(quantite, 0)} kg")
            response_text = f"Stock {scope_text} :\n" + "\n".join(details) + note_contexte
        response_data = rows
    elif intention == "production":
        result = service.get_production(huilerie=huilerie, start_date=date_debut, end_date=date_fin, enterprise_id=user_enterprise_id)
        total = result.get("value", 0)
        if total <= 0:
            response_text = f"Aucune donnee pour {texte_periode}.{note_contexte}"
        else:
            response_text = f"La quantite d'huile produite {scope_text} est de {_fmt_number(total, 0)} litres{note_contexte}"
        response_data = {"total_production": total}
    elif intention == "machine":
        result = service.get_machines(huilerie=huilerie, start_date=date_debut, end_date=date_fin, enterprise_id=user_enterprise_id)
        rows = result.get("value") or []
        if not rows:
            response_text = f"Toutes les machines sont en bon etat {scope_text}{note_contexte}"
        else:
            details = [f"{row.get('nom_machine')} ({row.get('etat_machine')})" for row in rows]
            response_text = f"Machines necessitant attention {scope_text} : " + ", ".join(details) + note_contexte
        response_data = rows
    elif intention == "rendement":
        result = service.get_rendement(huilerie=huilerie, start_date=date_debut, end_date=date_fin, enterprise_id=user_enterprise_id)
        rendement = result.get("value", 0)
        if rendement <= 0:
            response_text = f"Aucune donnee pour {texte_periode}.{note_contexte}"
        else:
            response_text = f"Le rendement moyen reel {scope_text} est de {_fmt_number(rendement, 1)} %{note_contexte}"
        response_data = {"rendement_moyen": rendement}
    elif intention == "prediction":
        result = service.get_prediction(huilerie=huilerie, start_date=date_debut, end_date=date_fin, enterprise_id=user_enterprise_id)
        rendement = result.get("rendement_predit", 0)
        quantite = result.get("quantite_estimee", 0)
        if rendement <= 0 and quantite <= 0:
            response_text = f"Aucune donnee pour {texte_periode}.{note_contexte}"
        else:
            response_text = (
                f"Le rendement predit {scope_text} est de {_fmt_number(rendement, 1)} % "
                f"avec une production estimee de {_fmt_number(quantite, 0)} litres{note_contexte}"
            )
        response_data = result
    elif intention == "qualite":
        result = service.get_qualite(huilerie=huilerie, start_date=date_debut, end_date=date_fin, enterprise_id=user_enterprise_id)
        rows = result.get("value") or []
        summary = result.get("summary") or {}

        if not rows:
            response_text = f"Aucune donnee pour {texte_periode}.{note_contexte}"
            response_data = {"details": rows, "summary": summary}
            return ChatResponse(
                intent=intention,
                confidence=confiance,
                entities=entites,
                response=response_text,
                data=response_data,
                applied_scope={"huilerie": huilerie, "enterprise_id": user_enterprise_id, "period_label": label_periode or "aujourd_hui", "start_date": date_debut, "end_date": date_fin},
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
        response_text += note_contexte

        response_data = {
            "details": rows,
            "summary": summary,
        }
    elif intention == "diagnostic":
        result = service.diagnostic_qualite(huilerie=huilerie, start_date=date_debut, end_date=date_fin, enterprise_id=user_enterprise_id)
        issues = result.get("issues") or []
        rows = result.get("rows") or []
        if not rows:
            response_text = f"Aucune donnee pour {texte_periode}.{note_contexte}"
            response_data = result
            return ChatResponse(
                intent=intention,
                confidence=confiance,
                entities=entites,
                response=response_text,
                data=response_data,
                applied_scope={"huilerie": huilerie, "enterprise_id": user_enterprise_id, "period_label": label_periode or "aujourd_hui", "start_date": date_debut, "end_date": date_fin},
                applied_permissions=applied_permissions,
            )
        if issues:
            response_text = f"La qualite est faible {scope_text} en raison de : " + ", ".join(issues) + note_contexte
        else:
            response_text = f"Tous les parametres sont conformes {scope_text}{note_contexte}"
        response_data = result
    else:
        logger.info("Intent non reconnue pour le message: %s", payload.message)
        response_text = "Je n'ai pas compris la demande. Essayez avec stock, production, machine, rendement, prediction, qualite ou diagnostic."
        response_data = None

    return ChatResponse(
        intent=intention,
        confidence=confiance,
        entities=entites,
        response=response_text,
        data=response_data,
        applied_scope={"huilerie": huilerie, "enterprise_id": user_enterprise_id, "period_label": label_periode or "aujourd_hui", "start_date": date_debut, "end_date": date_fin},
        applied_permissions=applied_permissions,
    )
