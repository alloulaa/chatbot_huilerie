import logging
from typing import Annotated, Any

from fastapi import APIRouter, Header

from app.database import get_db_connection
from app.models import ChatRequest, ChatResponse
from app.services.chat_service_v2 import ChatService as NewChatService
from app.nlp.normalizer import resolve_period
# ChatbotService is intentionally not imported here to avoid direct use;
# the new `ChatService` handles orchestration.
from app.services.permission_service import (
    get_user_enterprise_id,
    get_user_huilerie,
    get_user_permissions,
    is_admin,
    is_intent_allowed,
)
from app.controllers.formatters import (
    annotate_fournisseurs as _annotate_fournisseurs,
    build_fournisseur_payload as _build_fournisseur_payload,
    annotate_machines as _annotate_machines,
    build_machines_payload as _build_machines_payload,
    annotate_lots as _annotate_lots,
    build_lots_payload as _build_lots_payload,
    annotate_analyses as _annotate_analyses,
    build_analyses_payload as _build_analyses_payload,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])
new_chat_service = NewChatService()

SESSION_CONTEXT: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Validation des privilèges
# ---------------------------------------------------------------------------

def _huilerie_belongs_to_enterprise(huilerie: str, enterprise_id: int) -> bool:
    """Vérifier que la huilerie spécifiée appartient à l'entreprise donnée.
    
    Retourne True si la huilerie existe et appartient à l'entreprise,
    False sinon.
    """
    if not huilerie or not enterprise_id:
        return False
    
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT id_huilerie FROM huilerie
            WHERE LOWER(nom) = LOWER(%s)
            AND entreprise_id = %s
            LIMIT 1
        """
        cursor.execute(query, (huilerie, enterprise_id))
        result = cursor.fetchone()
        return result is not None
    except Exception as exc:
        logger.warning("Error checking huilerie ownership: %s", exc)
        return False
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


# ---------------------------------------------------------------------------
# Utilitaires de formatage
# ---------------------------------------------------------------------------

def _fmt(value: float | int | None, decimals: int = 0) -> str:
    n = float(value or 0)
    fmt = f"{n:,.{decimals}f}".replace(",", " ")
    return fmt


def _scope(huilerie: str | None, period_text: str, enterprise_scoped: bool = False) -> str:
    if huilerie:
        return f"de l'huilerie **{huilerie}** pour {period_text}"
    if enterprise_scoped:
        return f"pour {period_text} (toutes vos huileries)"
    return f"pour {period_text} (toutes huileries)"


def _is_chart_request(message: str) -> bool:
    texte = message.lower()
    return any(mot in texte for mot in ("graphique", "chart", "diagramme", "courbe", "histogramme", "visualisation"))


def _normalize_choice(message: str) -> str | None:
    texte = message.strip().lower()
    if texte in {"texte", "text", "résumé", "resume"}:
        return "texte"
    if texte in {"graphique", "chart", "diagramme", "courbe", "barre", "bar"}:
        return "graphique"
    return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default





def _chart_type_for(intent: str, rows: list[dict[str, Any]] | dict[str, Any] | None) -> str:
    if intent == "qualite":
        return "pie"
    if intent in {"production", "rendement", "prediction"}:
        return "line"
    if isinstance(rows, list) and any(any("date" in str(key).lower() for key in row.keys()) for row in rows):
        return "line"
    return "bar"


def _chart_data_for(intent: str, data: Any) -> Any:
    if isinstance(data, list):
        if not data:
            return []

        if intent == "mouvement_stock":
            compteur: dict[str, int] = {}
            for row in data:
                label = str(
                    row.get("type_mouvement")
                    or row.get("lot_ref")
                    or row.get("reference")
                    or row.get("label")
                    or "Inconnu"
                )
                compteur[label] = compteur.get(label, 0) + 1
            return [{"label": label, "value": value} for label, value in compteur.items()]

        label_keys = {
            "stock": ["variete", "label"],
            "fournisseur": ["fournisseur_nom", "name", "label"],
            "machines_utilisees": ["nomMachine", "machineRef", "nom_machine", "machine_ref", "label"],
            "lot_liste": ["reference", "lot_ref", "label"],
            "campagne": ["reference", "annee", "label"],
            "analyse_labo": ["lot_ref", "reference", "label"],
            "reception": ["reference", "lot_ref", "label"],
        }

        # --- Special fournisseur handling: always produce multi-dataset -------
        if intent == "fournisseur":
            annotated = _annotate_fournisseurs(data)
            payload = _build_fournisseur_payload(annotated)
            return {"labels": payload["labels"], "datasets": payload["datasets"]}

        # --- Special machines_utilisees handling ------
        if intent == "machines_utilisees":
            annotated = _annotate_machines(data)
            payload = _build_machines_payload(annotated)
            return {"labels": payload["labels"], "datasets": payload["datasets"]}

        # --- Special lot_liste handling ------
        if intent == "lot_liste":
            annotated = _annotate_lots(data)
            payload = _build_lots_payload(annotated)
            return {"labels": payload["labels"], "datasets": payload["datasets"]}

        # --- Special analyse_labo handling ------
        if intent == "analyse_labo":
            annotated = _annotate_analyses(data)
            payload = _build_analyses_payload(annotated)
            return {"labels": payload["labels"], "datasets": payload["datasets"]}

        value_keys = {
            "stock": ["total_stock", "value"],
            "machines_utilisees": ["nbExecutions", "nb_executions", "totalProduit", "total_produit", "value"],
            "lot_liste": ["quantite_initiale", "value"],
            "campagne": ["total_olives_kg", "nb_lots", "value"],
            "analyse_labo": ["acidite_huile_pourcent", "indice_peroxyde_meq_o2_kg", "k270", "value"],
            "reception": ["quantite_initiale", "value"],
        }

        labels_keys = label_keys.get(intent, ["label", "reference", "name", "nom", "title"])
        preferred_values = value_keys.get(intent, ["value", "total", "count"])

        labels: list[str] = []
        for index, row in enumerate(data, start=1):
            label = None
            for key in labels_keys:
                candidate = row.get(key)
                if candidate not in (None, ""):
                    label = candidate
                    break
            if label is None:
                label = f"Item {index}"
            labels.append(str(label))

        preferred_order = list(dict.fromkeys(preferred_values + [
            "quantite_totale_kg", "quantite_initiale", "total_produit", "total_stock",
            "rendement_moyen", "acidite_huile_pourcent", "indice_peroxyde_meq_o2_kg", "k270",
            "value", "total", "count", "nb_lots"
        ]))
        camel_variants = [
            "quantiteTotaleKg", "quantiteInitiale", "totalProduit", "totalStock",
            "rendementMoyen", "aciditeMoyenne", "indicePeroxydeMeqO2Kg", "k270",
            "value", "total", "count", "nbLots", "nbExecutions"
        ]
        for cv in camel_variants:
            if cv not in preferred_order:
                preferred_order.append(cv)

        metrics: list[str] = []
        for key in preferred_order:
            if any(row.get(key) not in (None, "") for row in data):
                metrics.append(key)

        if not metrics:
            detected = set()
            for row in data:
                for k, v in row.items():
                    if isinstance(v, (int, float)):
                        detected.add(k)
                    elif isinstance(v, str):
                        try:
                            float(v)
                            detected.add(k)
                        except Exception:
                            pass
            metrics = sorted(detected)

        if not metrics:
            return [{"label": labels[i], "value": 1.0} for i in range(len(labels))]

        if len(metrics) == 1:
            metric = metrics[0]
            points: list[dict[str, Any]] = []
            for i, row in enumerate(data):
                points.append({"label": labels[i], "value": _safe_float(row.get(metric), 0.0)})
            return points

        datasets: list[dict[str, Any]] = []
        for metric in metrics:
            series = []
            for row in data:
                series.append(_safe_float(row.get(metric), 0.0))
            datasets.append({"label": metric.replace("_", " ").title(), "data": series})

        return {"labels": labels, "datasets": datasets}

    if isinstance(data, dict):
        # If already a pre-built chart payload, pass through
        if "labels" in data and "datasets" in data:
            return data

        summary = data.get("summary")
        if isinstance(summary, dict) and summary:
            return [{"label": str(label), "value": _safe_float(value, 0.0)} for label, value in summary.items()]

        points: list[dict[str, Any]] = []
        for key, value in data.items():
            if isinstance(value, (int, float)):
                points.append({"label": key.replace("_", " ").title(), "value": float(value)})
        return points

    if isinstance(data, (int, float)):
        return [{"label": intent.replace("_", " ").title(), "value": float(data)}]

    return []


def _build_response(
    *,
    session_id: str,
    payload_message: str,
    intent: str,
    confidence: float,
    entities: dict,
    response_text: str,
    response_data: Any,
    applied_scope: dict,
    applied_permissions: list | None,
) -> ChatResponse:
    ctx = SESSION_CONTEXT.setdefault(session_id, {})
    selected_choice = _normalize_choice(payload_message)
    pending = ctx.get("pending_visualization")

    if selected_choice and pending:
        chart_data = pending.get("chart_data") or []
        chart_type = pending.get("chart_type") or "bar"
        if selected_choice == "texte":
            ctx.pop("pending_visualization", None)
            text_message = pending.get("text_message") or response_text
            return ChatResponse(
                type="text",
                message=text_message,
                intent=intent,
                confidence=confidence,
                entities=entities,
                response=text_message,
                data=pending.get("raw_data"),
                applied_scope=applied_scope,
                applied_permissions=applied_permissions,
                selected_option="texte",
            )
        if selected_choice == "graphique":
            ctx.pop("pending_visualization", None)
            return ChatResponse(
                type="chart",
                message="Voici la visualisation demandée.",
                intent=intent,
                confidence=confidence,
                entities=entities,
                response="Voici la visualisation demandée.",
                chart_type=chart_type,
                data=chart_data,
                applied_scope=applied_scope,
                applied_permissions=applied_permissions,
                selected_option="graphique",
            )

    wants_chart = _is_chart_request(payload_message)
    is_choice_candidate = isinstance(response_data, list) and len(response_data) > 1

    # Special handling for structured ranking intents
    ranking_intents = {"fournisseur", "machines_utilisees", "lot_liste", "analyse_labo", "stock"}
    
    if intent in ranking_intents and isinstance(response_data, list) and response_data:
        # Annotate and structure the data
        if intent == "fournisseur":
            annotated = _annotate_fournisseurs(response_data)
            structured_payload = _build_fournisseur_payload(annotated)
            title_default = "Voici une visualisation des fournisseurs."
        elif intent == "machines_utilisees":
            annotated = _annotate_machines(response_data)
            structured_payload = _build_machines_payload(annotated)
            title_default = "Voici une visualisation des machines."
        elif intent == "lot_liste":
            annotated = _annotate_lots(response_data)
            structured_payload = _build_lots_payload(annotated)
            title_default = "Voici une visualisation des lots."
        elif intent == "analyse_labo":
            annotated = _annotate_analyses(response_data)
            structured_payload = _build_analyses_payload(annotated)
            title_default = "Voici une visualisation des analyses."
        elif intent == "stock":
            # Stock: simple list format with labels and items
            items = response_data
            labels = [item.get("reference_stock", "N/D") for item in items]
            structured_payload = {
                "labels": labels,
                "items": items,
                "value": items,
                "datasets": [{
                    "label": "Quantité disponible (kg)",
                    "data": [item.get("quantite_disponible", 0) for item in items],
                    "backgroundColor": "#4CAF50",
                    "borderColor": "#2E7D32",
                    "borderWidth": 1
                }]
            }
            title_default = "Voici le stock disponible."
        else:
            structured_payload = None
            title_default = "Voici une visualisation des résultats."

        if structured_payload:
            chart_data = {
                "labels": structured_payload["labels"],
                "datasets": structured_payload["datasets"],
            }
            chart_type = "bar"

            if wants_chart:
                ctx.pop("pending_visualization", None)
                return ChatResponse(
                    type="chart",
                    message=response_text or title_default,
                    intent=intent,
                    confidence=confidence,
                    entities=entities,
                    response=response_text or title_default,
                    chart_type=chart_type,
                    data=chart_data,
                    applied_scope=applied_scope,
                    applied_permissions=applied_permissions,
                )

            if len(response_data) > 1:
                ctx["pending_visualization"] = {
                    "text_message": response_text,
                    "chart_data": chart_data,
                    "chart_type": chart_type,
                    "raw_data": structured_payload,
                }
                question = "Souhaitez-vous voir les résultats sous forme de texte ou de graphique ?"
                return ChatResponse(
                    type="choice",
                    message=question,
                    intent=intent,
                    confidence=confidence,
                    entities=entities,
                    response=question,
                    options=["texte", "graphique"],
                    chart_type=chart_type,
                    data=structured_payload,
                    applied_scope=applied_scope,
                    applied_permissions=applied_permissions,
                    pending_choice=True,
                )

            # Single item — return text with structured data
            ctx.pop("pending_visualization", None)
            return ChatResponse(
                type="text",
                message=response_text,
                intent=intent,
                confidence=confidence,
                entities=entities,
                response=response_text,
                data=structured_payload,
                applied_scope=applied_scope,
                applied_permissions=applied_permissions,
            )

    if is_choice_candidate:
        chart_data = _chart_data_for(intent, response_data)
        chart_type = _chart_type_for(intent, response_data)

        if wants_chart:
            ctx.pop("pending_visualization", None)
            return ChatResponse(
                type="chart",
                message=response_text or "Voici une visualisation des résultats.",
                intent=intent,
                confidence=confidence,
                entities=entities,
                response=response_text or "Voici une visualisation des résultats.",
                chart_type=chart_type,
                data=chart_data,
                applied_scope=applied_scope,
                applied_permissions=applied_permissions,
            )

        ctx["pending_visualization"] = {
            "text_message": response_text,
            "chart_data": chart_data,
            "chart_type": chart_type,
            "raw_data": response_data,
        }
        question = "Souhaitez-vous voir les résultats sous forme de texte ou de graphique ?"
        return ChatResponse(
            type="choice",
            message=response_text + "\n\n" + question,
            intent=intent,
            confidence=confidence,
            entities=entities,
            response=response_text + "\n\n" + question,
            options=["texte", "graphique"],
            chart_type=chart_type,
            data=response_data,
            applied_scope=applied_scope,
            applied_permissions=applied_permissions,
            pending_choice=True,
        )

    if wants_chart:
        chart_data = _chart_data_for(intent, response_data)
        if chart_data:
            chart_type = _chart_type_for(intent, response_data)
            return ChatResponse(
                type="chart",
                message=response_text or "Voici une visualisation des résultats.",
                intent=intent,
                confidence=confidence,
                entities=entities,
                response=response_text or "Voici une visualisation des résultats.",
                chart_type=chart_type,
                data=chart_data,
                applied_scope=applied_scope,
                applied_permissions=applied_permissions,
            )

    ctx.pop("pending_visualization", None)
    return ChatResponse(
        type="text",
        message=response_text,
        intent=intent,
        confidence=confidence,
        entities=entities,
        response=response_text,
        data=response_data,
        applied_scope=applied_scope,
        applied_permissions=applied_permissions,
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/ask", response_model=ChatResponse)
def ask_chatbot(
    payload: ChatRequest,
    authorization: Annotated[str | None, Header()] = None,
):
    # ── Auth ─────────────────────────────────────────────────────────────────
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip() or None

    jwt = payload.jwt_token or payload.token or bearer
    auth_data = user_is_admin = user_huilerie = user_enterprise_id = applied_perms = None

    if jwt:
        auth_data = get_user_permissions(jwt)
        if auth_data is None:
            return ChatResponse(
                type="text",
                message="Token invalide ou expiré.",
                intent="unknown",
                confidence=0.0,
                entities={},
                response="Token invalide ou expiré.",
                data=None,
                applied_scope={},
                applied_permissions=None,
            )
        user_is_admin = is_admin(auth_data)
        user_huilerie = get_user_huilerie(auth_data, jwt)
        user_enterprise_id = get_user_enterprise_id(auth_data)
        applied_perms = auth_data.get("permissions", [])

    # ── NLP (via nouveau ChatService)─────────────────────────────────────────
    import asyncio
    nlp_out = asyncio.run(new_chat_service.process_message(
        message=payload.message,
        session_id=payload.session_id,
        huilerie=None,
        enterprise_id=user_enterprise_id,
        permissions=applied_perms or [],
        user_is_admin=user_is_admin,
    ))

    intent = str(nlp_out.get("intent") or "inconnu").strip().lower()
    try:
        confidence = float(nlp_out.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    entities = nlp_out.get("entities") or {}

    # ── Intent Override : priorité aux mots-clés explicites du message ──
    _msg_lower = payload.message.lower().strip()
    _stock_keywords  = ["stock", "inventaire", "quantite disponible", "reserve d'olive"]
    _lot_keywords    = ["liste lot", "liste des lots", "lots non conformes",
                        "tracabilite", "tous les lots", "lots recus", "lots de"]
    _has_stock_word  = any(k in _msg_lower for k in _stock_keywords)
    _has_lot_word    = any(k in _msg_lower for k in _lot_keywords)

    if _has_stock_word and not _has_lot_word and intent != "stock":
        logger.info(
            "Intent override: '%s' → 'stock' (message contains stock keyword)", intent
        )
        intent = "stock"

    # Si le message contient "liste des lots" ou commence par "lots"
    _lot_list_keywords = ["liste lot", "liste des lots", "tous les lots"]
    if any(k in _msg_lower for k in _lot_list_keywords) \
            and intent not in ("lot_liste", "lot_cycle_vie"):
        logger.info("Intent override: '%s' → 'lot_liste'", intent)
        intent = "lot_liste"

    # ── RBAC ─────────────────────────────────────────────────────────────────
    if jwt and auth_data and not user_is_admin and not auth_data.get("_auth_unavailable"):
        if not is_intent_allowed(intent, auth_data.get("permissions", [])):
            return ChatResponse(
                type="text",
                message="Accès refusé pour cet intent.",
                intent=intent,
                confidence=confidence,
                entities=entities,
                response="Accès refusé pour cet intent.",
                data=None,
                applied_scope={},
                applied_permissions=applied_perms,
            )

    # ── Contexte session ─────────────────────────────────────────────────────
    ctx = SESSION_CONTEXT.get(payload.session_id, {})

    explicit_huilerie = entities.get("huilerie")
    explicit_period = entities.get("period_label")

    # ── Validation des privilèges : vérifier que la huilerie explicite appartient à l'entreprise
    if explicit_huilerie and user_enterprise_id:
        if not _huilerie_belongs_to_enterprise(explicit_huilerie, user_enterprise_id):
            return ChatResponse(
                type="text",
                message=f"L'huilerie '{explicit_huilerie}' n'appartient pas à votre entreprise ou n'existe pas.",
                intent=intent,
                confidence=confidence,
                entities=entities,
                response=f"L'huilerie '{explicit_huilerie}' n'appartient pas à votre entreprise ou n'existe pas.",
                data=None,
                applied_scope={},
                applied_permissions=applied_perms,
            )

    huilerie = explicit_huilerie or ctx.get("last_huilerie") or None
    period_label = explicit_period or ctx.get("last_period") or "aujourd_hui"

    if user_huilerie and not user_is_admin:
        huilerie = user_huilerie

    ctx_note = ""
    if (explicit_huilerie is None and ctx.get("last_huilerie")) or \
       (explicit_period is None and ctx.get("last_period")):
        ctx_note = f" *(contexte : {huilerie or 'toutes huileries'}, {period_label})*"

    start_date, end_date, period_text = resolve_period(period_label)

    SESSION_CONTEXT[payload.session_id] = {
        **SESSION_CONTEXT.get(payload.session_id, {}),
        "last_huilerie": huilerie or "",
        "last_period": period_label,
    }

    enterprise_scoped = bool(auth_data and user_enterprise_id is not None)
    scope_text = _scope(huilerie, period_text, enterprise_scoped)
    applied_scope = {
        "huilerie": huilerie,
        "enterprise_id": user_enterprise_id,
        "period_label": period_label,
        "start_date": start_date,
        "end_date": end_date,
    }

    # ── Dispatch centralisé via ChatService (résultat déjà calculé)
    response_text = nlp_out.get("text") or ""
    response_data = nlp_out.get("data")
    # Si le handler a renvoyé un payload structuré, préférer structured_payload
    if nlp_out.get("structured_payload"):
        response_data = nlp_out.get("data") or nlp_out.get("structured_payload")

    response = _build_response(
        session_id=payload.session_id,
        payload_message=payload.message,
        intent=intent,
        confidence=confidence,
        entities=entities,
        response_text=response_text,
        response_data=response_data,
        applied_scope=applied_scope,
        applied_permissions=applied_perms,
    )

    logger.info(
        "Chat response ready: intent=%s type=%s session_id=%s",
        response.intent,
        response.type,
        payload.session_id,
    )
    return response