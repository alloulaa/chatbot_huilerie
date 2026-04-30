"""
chat_controller.py — Contrôleur principal du chatbot huilerie.

Gère tous les intents :
  stock, production, machine, machines_utilisees, rendement, prediction,
  qualite, diagnostic, fournisseur, lot_cycle_vie, lot_liste, campagne,
  reception, mouvement_stock, analyse_labo, unknown
"""

import logging
from typing import Annotated, Any

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

SESSION_CONTEXT: dict[str, dict] = {}


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


def _annotate_fournisseurs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate supplier rows with status flags for acidite and rendement.

    Adds keys `acidite_status` and `rendement_status` with values
    "ok" or "out of range" according to business rules.
    """
    annotated: list[dict[str, Any]] = []
    for r in rows:
        acid = _safe_float(r.get("acidite_moyenne"), 0.0)
        rend = _safe_float(r.get("rendement_moyen"), 0.0)
        acid_status = "ok" if 0.2 <= acid <= 1.5 else "out of range"
        rend_status = "ok" if 10.0 <= rend <= 30.0 else "out of range"
        nr = dict(r)
        nr["acidite_moyenne"] = acid
        nr["rendement_moyen"] = rend
        nr["acidite_status"] = acid_status
        nr["rendement_status"] = rend_status
        annotated.append(nr)
    return annotated


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
            "fournisseur": ["fournisseur_nom", "label"],
            "machines_utilisees": ["nomMachine", "machineRef", "nom_machine", "machine_ref", "label"],
            "lot_liste": ["reference", "lot_ref", "label"],
            "campagne": ["reference", "annee", "label"],
            "analyse_labo": ["lot_ref", "reference", "label"],
            "reception": ["reference", "lot_ref", "label"],
        }
        value_keys = {
            "stock": ["total_stock", "value"],
            "fournisseur": ["quantite_totale_kg", "nb_lots", "value"],
            "machines_utilisees": ["nbExecutions", "nb_executions", "totalProduit", "total_produit", "value"],
            "lot_liste": ["quantite_initiale", "value"],
            "campagne": ["total_olives_kg", "nb_lots", "value"],
            "analyse_labo": ["acidite_huile_pourcent", "indice_peroxyde_meq_o2_kg", "k270", "value"],
            "reception": ["quantite_initiale", "value"],
        }

        labels_keys = label_keys.get(intent, ["label", "reference", "name", "nom", "title"])
        preferred_values = value_keys.get(intent, ["value", "total", "count"])

        # build labels array
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

        # detect available numeric metrics, prioritizing known keys
        preferred_order = list(dict.fromkeys(preferred_values + [
            "quantite_totale_kg", "quantite_initiale", "total_produit", "total_stock",
            "rendement_moyen", "acidite_huile_pourcent", "indice_peroxyde_meq_o2_kg", "k270",
            "value", "total", "count", "nb_lots"
        ]))
        # also accept camelCase variants produced by updated services
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

        # fallback: detect any numeric keys present in rows
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

        # if no numeric metric found, return counts per label (fallback behaviour)
        if not metrics:
            return [{"label": labels[i], "value": 1.0} for i in range(len(labels))]

        # single metric -> return old point format for backward compatibility
        if len(metrics) == 1:
            metric = metrics[0]
            points: list[dict[str, Any]] = []
            for i, row in enumerate(data):
                points.append({"label": labels[i], "value": _safe_float(row.get(metric), 0.0)})
            return points

        # multiple metrics -> return Chart.js friendly multi-dataset structure
        # Special handling for fournisseur: show ONLY quantite_totale_kg as bars (no dual-axis)
        if intent == "fournisseur":
            # Extract quantity metric for bars
            qty_key = None
            for k in ("quantite_totale_kg", "quantiteTotaleKg", "quantite", "value"):
                if k in metrics:
                    qty_key = k
                    break

            datasets = []
            if qty_key:
                series = [ _safe_float(row.get(qty_key), 0.0) for row in data ]
                datasets.append({
                    "label": "Quantité livrée (kg)",
                    "data": series,
                    "type": "bar",
                })
            
            return {"labels": labels, "datasets": datasets}

        datasets: list[dict[str, Any]] = []
        for metric in metrics:
            series = []
            for row in data:
                series.append(_safe_float(row.get(metric), 0.0))
            datasets.append({"label": metric.replace("_", " ").title(), "data": series})

        return {"labels": labels, "datasets": datasets}

    if isinstance(data, dict):
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

    # ── NLP ──────────────────────────────────────────────────────────────────
    resultat = analyser_message_sync(payload.message)
    intent = str(resultat.get("intention") or "inconnu").strip().lower()
    try:
        confidence = float(resultat.get("confiance", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    entities = {
        "huilerie": resultat.get("huilerie"),
        "periode": resultat.get("periode"),
        "period_label": resultat.get("periode"),
        "type_huile": resultat.get("type_huile"),
        "variete": resultat.get("variete"),
        "code_lot": resultat.get("code_lot"),
        "reference_lot": resultat.get("reference_lot") or resultat.get("code_lot"),
        "lot_reference": resultat.get("lot_reference") or resultat.get("reference_lot") or resultat.get("code_lot"),
        "campagne_annee": resultat.get("campagne_annee"),
    }

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

    # ── Dispatch ─────────────────────────────────────────────────────────────

    response_text = ""
    response_data = None

    # --- STOCK ---------------------------------------------------------------
    if intent == "stock":
        result = service.get_stock(huilerie, start_date, end_date, user_enterprise_id)
        rows = result.get("value") or []
        if not rows:
            response_text = f"Aucune donnée de stock pour {period_text}.{ctx_note}"
        else:
            lines = [f"- {r['variete']} : **{_fmt(r['total_stock'])} kg**" for r in rows]
            response_text = f"Stock {scope_text} :\n" + "\n".join(lines) + ctx_note
        response_data = rows

    # --- PRODUCTION ----------------------------------------------------------
    elif intent == "production":
        result = service.get_production(huilerie, start_date, end_date, user_enterprise_id)
        total = result.get("value", 0)
        if total <= 0:
            response_text = f"Aucune production enregistrée pour {period_text}.{ctx_note}"
        else:
            response_text = f"Production {scope_text} : **{_fmt(total)} litres** d'huile.{ctx_note}"
        response_data = {"total_production_litres": total}

    # --- MACHINE — état ------------------------------------------------------
    elif intent == "machine":
        result = service.get_machines(huilerie, start_date, end_date, user_enterprise_id)
        rows = result.get("value") or []
        if not rows:
            response_text = f"Toutes les machines sont opérationnelles {scope_text}.{ctx_note}"
        else:
            lines = [
                f"- **{r.get('nomMachine') or r.get('nom_machine') or r.get('nom', 'Machine inconnue')}** : "
                f"{r.get('etatMachine') or r.get('etat_machine') or r.get('etat', 'INCONNU')}"
                for r in rows
            ]
            response_text = f"Machines nécessitant attention {scope_text} :\n" + "\n".join(lines) + ctx_note
        response_data = rows

    # --- MACHINES LES PLUS UTILISÉES -----------------------------------------
    elif intent == "machines_utilisees":
        result = service.get_machines_utilisees(huilerie, start_date, end_date, user_enterprise_id)
        rows = result.get("value") or []
        if not rows:
            response_text = f"Aucune donnée d'utilisation machines {scope_text}.{ctx_note}"
        else:
            lines = []
            for r in rows[:5]:
                nom = r.get('nomMachine') or r.get('nom_machine') or r.get('nom', 'Machine inconnue')
                ref = r.get('machineRef') or r.get('machine_ref') or r.get('reference') or 'N/D'
                nb = r.get('nbExecutions') or r.get('nb_executions') or 0
                rend = r.get('rendementMoyen') or r.get('rendement_moyen') or 0.0
                total = r.get('totalProduit') or r.get('total_produit') or 0.0
                lines.append(
                    f"- **{nom}** ({ref}) — "
                    f"{nb} exécution(s), "
                    f"rendement moyen {_fmt(rend, 1)} %, "
                    f"{_fmt(total)} L produits"
                )
            response_text = f"Machines les plus utilisées {scope_text} :\n" + "\n".join(lines) + ctx_note
        response_data = rows

    # --- RENDEMENT -----------------------------------------------------------
    elif intent == "rendement":
        result = service.get_rendement(huilerie, start_date, end_date, user_enterprise_id)
        rend = result.get("value", 0)
        if rend <= 0:
            response_text = f"Aucune donnée de rendement pour {period_text}.{ctx_note}"
        else:
            response_text = f"Rendement moyen réel {scope_text} : **{_fmt(rend, 1)} %**.{ctx_note}"
        response_data = {"rendement_moyen": rend}

    # --- PREDICTION ----------------------------------------------------------
    elif intent == "prediction":
        result = service.get_prediction(huilerie, start_date, end_date, user_enterprise_id)
        rend = result.get("rendement_predit", 0)
        qte  = result.get("quantite_estimee", 0)
        if rend <= 0 and qte <= 0:
            response_text = f"Aucune prédiction disponible pour {period_text}.{ctx_note}"
        else:
            response_text = (
                f"Prédiction {scope_text} : rendement prédit **{_fmt(rend, 1)} %**, "
                f"production estimée **{_fmt(qte)} litres**.{ctx_note}"
            )
        response_data = result

    # --- QUALITE -------------------------------------------------------------
    elif intent == "qualite":
        result = service.get_qualite(huilerie, start_date, end_date, user_enterprise_id)
        rows = result.get("value") or []
        summary = result.get("summary", {})
        if not rows:
            response_text = f"Aucune donnée de qualité pour {period_text}.{ctx_note}"
        else:
            parts = []
            for k in ("Bonne", "Moyenne", "Mauvaise", "Inconnue"):
                if summary.get(k, 0) > 0:
                    parts.append(f"{k}: {summary[k]}")
            response_text = f"Qualité des produits {scope_text} — " + ", ".join(parts) + ctx_note
        response_data = {"details": rows, "summary": summary}

    # --- DIAGNOSTIC ----------------------------------------------------------
    elif intent == "diagnostic":
        result = service.diagnostic_qualite(huilerie, start_date, end_date, user_enterprise_id)
        issues = result.get("issues") or []
        rows   = result.get("rows") or []
        if not rows:
            response_text = f"Aucune analyse labo disponible pour {period_text}.{ctx_note}"
        elif issues:
            response_text = (
                f"Qualité insuffisante {scope_text} — causes identifiées : "
                + ", ".join(f"**{i}**" for i in issues) + ".{ctx_note}"
            )
        else:
            response_text = f"Tous les paramètres sont conformes {scope_text}.{ctx_note}"
        response_data = result

    # --- MEILLEUR FOURNISSEUR ← NOUVELLE -------------------------------------
    elif intent == "fournisseur":
        result = service.get_meilleur_fournisseur(huilerie, start_date, end_date, user_enterprise_id)
        rows = result.get("value") or []
        annotated = _annotate_fournisseurs(rows)
        if not annotated:
            response_text = f"Aucune donnée fournisseur disponible pour {period_text}.{ctx_note}"
        else:
            lines = []
            for r in annotated[:8]:
                acid_flag = " ⚠️ (out of range)" if r.get("acidite_status") == "out of range" else ""
                rend_flag = " ⚠️ (out of range)" if r.get("rendement_status") == "out of range" else ""
                lines.append(
                    f"{r.get('rang', '?')}. **{r.get('fournisseur_nom')}** — "
                    f"{r.get('nb_lots', 0)} lot(s), "
                    f"{_fmt(r.get('quantite_totale_kg'))} kg livrés, "
                    f"rendement moyen {_fmt(r.get('rendement_moyen'), 1)} %{rend_flag}, "
                    f"acidité moy. {_fmt(r.get('acidite_moyenne'), 2)} %{acid_flag}"
                )
            extra = f" *(+{len(annotated) - 8} autres)*" if len(annotated) > 8 else ""
            response_text = f"Classement fournisseurs {scope_text} :\n" + "\n".join(lines) + extra + ctx_note
        # return the annotated list so chart builder can create appropriate datasets
        response_data = annotated

    # --- CYCLE DE VIE D'UN LOT ← NOUVELLE ------------------------------------
    elif intent == "lot_cycle_vie":
        lot_ref = entities.get("lot_reference") or entities.get("code_lot")
        if not lot_ref:
            response_text = (
                "Précisez la référence du lot. Exemple : "
                "\"cycle de vie du lot LO07\" ou \"donne-moi le cycle de vie de lot15\"."
            )
            response_data = None
        else:
            result = service.get_lot_cycle_vie(lot_reference=lot_ref)
            if result.get("error"):
                response_text = result["error"]
            else:
                lot_info = result["lot"]
                steps = result["steps"]
                nb = len(steps)
                remaining_steps = [step.get("etape") for step in steps[1:] if step.get("etape")]
                history_text = " → ".join(remaining_steps) if remaining_steps else "aucune étape supplémentaire"
                response_text = (
                    f"Cycle de vie du lot **{lot_ref}** "
                    f"({lot_info.get('variete', '?')}, fournisseur : {lot_info.get('fournisseur_nom', '?')}) :\n"
                    f"{nb} étape(s) retracée(s) — réception → {history_text}."
                )
            response_data = result

    # --- LISTE LOTS ← NOUVELLE -----------------------------------------------
    elif intent == "lot_liste":
        non_conf = any(kw in payload.message.lower() for kw in ["non conforme", "lampante", "mauvaise"])
        result = service.get_lot_liste(
            huilerie, start_date, end_date, user_enterprise_id,
            variete=entities.get("variete"),
            non_conformes_only=non_conf,
        )
        rows = result.get("value") or []
        if not rows:
            label = "lots non conformes" if non_conf else "lots"
            response_text = f"Aucun {label} trouvé pour {period_text}.{ctx_note}"
        else:
            lines = []
            for r in rows[:8]:
                lines.append(
                    f"- **{r.get('reference')}** | {r.get('variete')} | "
                    f"{r.get('fournisseur_nom')} | {r.get('quantite_initiale')} kg | "
                    f"qualité : {r.get('qualite_huile') or 'N/D'}"
                )
            extra = f" *(+{len(rows) - 8} autres)*" if len(rows) > 8 else ""
            response_text = f"Lots {scope_text} :\n" + "\n".join(lines) + extra + ctx_note
        response_data = rows

    # --- CAMPAGNE ← NOUVELLE -------------------------------------------------
    elif intent == "campagne":
        annee = entities.get("campagne_annee")
        result = service.get_campagnes(huilerie, user_enterprise_id, annee)
        rows = result.get("value") or []
        if not rows:
            response_text = "Aucune campagne trouvée."
        else:
            lines = []
            for r in rows:
                lines.append(
                    f"- **{r.get('reference')}** ({r.get('annee')}) | "
                    f"{r.get('huilerie_nom')} | "
                    f"du {r.get('date_debut')} au {r.get('date_fin')} | "
                    f"{r.get('nb_lots') or 0} lots | "
                    f"{_fmt(r.get('total_olives_kg'))} kg"
                )
            response_text = "Campagnes :\n" + "\n".join(lines)
        response_data = rows

    # --- ANALYSE LABO ← NOUVELLE ---------------------------------------------
    elif intent == "analyse_labo":
        lot_ref = entities.get("lot_reference") or entities.get("code_lot")
        result = service.get_analyse_labo(huilerie, start_date, end_date, user_enterprise_id, lot_ref)
        rows = result.get("value") or []
        if not rows:
            response_text = f"Aucune analyse laboratoire pour {period_text}.{ctx_note}"
        else:
            lines = []
            for r in rows[:5]:
                lines.append(
                    f"- Lot **{r.get('lot_ref')}** ({r.get('date_analyse')}) — "
                    f"acidité {_fmt(r.get('acidite_huile_pourcent'), 2)} %, "
                    f"peroxyde {_fmt(r.get('indice_peroxyde_meq_o2_kg'), 1)}, "
                    f"K270 {_fmt(r.get('k270'), 3)}"
                )
            response_text = f"Analyses laboratoire {scope_text} :\n" + "\n".join(lines) + ctx_note
        response_data = rows

    # --- MOUVEMENT STOCK ← NOUVELLE ------------------------------------------
    elif intent == "mouvement_stock":
        result = service.get_mouvements_stock(huilerie, start_date, end_date, user_enterprise_id)
        rows = result.get("value") or []
        if not rows:
            response_text = f"Aucun mouvement de stock pour {period_text}.{ctx_note}"
        else:
            lines = [
                f"- **{r.get('type_mouvement')}** | lot {r.get('lot_ref')} | "
                f"{r.get('date_mouvement')} — {r.get('commentaire') or ''}"
                for r in rows[:8]
            ]
            response_text = f"Mouvements de stock {scope_text} :\n" + "\n".join(lines) + ctx_note
        response_data = rows

    # --- RECEPTION ← NOUVELLE ------------------------------------------------
    elif intent == "reception":
        result = service.get_reception(huilerie, start_date, end_date, user_enterprise_id)
        rows  = result.get("value") or []
        total = result.get("total_kg", 0)
        if not rows:
            response_text = f"Aucune réception enregistrée pour {period_text}.{ctx_note}"
        else:
            lines = [
                f"- Lot **{r.get('reference')}** | {r.get('variete')} | "
                f"{r.get('fournisseur_nom')} | {_fmt(r.get('quantite_initiale'))} kg | "
                f"{r.get('date_reception')}"
                for r in rows[:8]
            ]
            response_text = (
                f"Réceptions {scope_text} — total **{_fmt(total)} kg** :\n"
                + "\n".join(lines) + ctx_note
            )
        response_data = {"lots": rows, "total_kg": total}

    # --- UNKNOWN -------------------------------------------------------------
    else:
        logger.info("Intent non reconnu : %s", payload.message)
        response_text = (
            "Je n'ai pas compris votre demande. Vous pouvez me poser des questions sur :\n"
            "- **Stock** d'olives ou d'huile\n"
            "- **Production** et rendement\n"
            "- **Machines** (état, utilisation)\n"
            "- **Machines les plus utilisées**\n"
            "- **Fournisseurs** (classement, qualité)\n"
            "- **Cycle de vie** d'un lot (ex : *cycle de vie du lot LO07*)\n"
            "- **Liste des lots** et lots non conformes\n"
            "- **Qualité** et diagnostic\n"
            "- **Analyses laboratoire**\n"
            "- **Campagnes** de récolte\n"
            "- **Mouvements de stock** et réceptions"
        )
        response_data = None

    return _build_response(
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