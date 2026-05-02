import logging
from typing import Annotated, Any

from fastapi import APIRouter, Header

from app.database import get_db_connection
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


def _annotate_fournisseurs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate supplier rows with status flags and guaranteed numeric fields.

    Ensures that kg, acidity, rendement, lots are JSON numbers (float/int),
    never strings. Also adds human-readable *_str variants and status flags.
    """
    annotated: list[dict[str, Any]] = []
    for r in rows:
        # --- Numeric extraction (always float) --------------------------------
        kg: float = _safe_float(r.get("quantite_totale_kg"), 0.0)
        acidity: float = _safe_float(r.get("acidite_moyenne"), 0.0)
        rendement: float = _safe_float(r.get("rendement_moyen"), 0.0)
        lots: int = int(_safe_float(r.get("nb_lots"), 0))

        # --- Status flags based on business rules -----------------------------
        acid_status = "ok" if 0.2 <= acidity <= 1.5 else "out of range"
        rend_status = "ok" if 10.0 <= rendement <= 30.0 else "out of range"

        # --- Human-readable string variants -----------------------------------
        kg_str = f"{kg:,.0f} kg".replace(",", " ")
        acidity_str = f"{acidity:.2f} %".replace(".", ",")
        rendement_str = f"{rendement:.1f} %".replace(".", ",")

        nr = dict(r)
        # Overwrite with guaranteed numeric types
        nr["kg"] = kg
        nr["acidity"] = acidity
        nr["rendement"] = rendement
        nr["lots"] = lots
        # Keep original snake_case keys for backward compat but also numeric
        nr["quantite_totale_kg"] = kg
        nr["acidite_moyenne"] = acidity
        nr["rendement_moyen"] = rendement
        nr["nb_lots"] = lots
        # Friendly name alias
        nr["name"] = r.get("fournisseur_nom") or "Inconnu"
        # String variants (display only — never replaces numeric fields)
        nr["kg_str"] = kg_str
        nr["acidity_str"] = acidity_str
        nr["rendement_str"] = rendement_str
        # Status
        nr["acidite_status"] = acid_status
        nr["rendement_status"] = rend_status
        annotated.append(nr)
    return annotated


def _build_fournisseur_payload(annotated: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a structured, chart-friendly payload for supplier ranking.

    Returns a dict with two complementary representations:
    - ``suppliers``: list of objects with guaranteed numeric fields (kg, acidity,
      rendement, lots) plus optional string variants.
    - ``labels`` / ``datasets``: Chart.js-compatible multi-dataset structure
      where every value in ``datasets[].data`` is a JSON number.
    """
    suppliers: list[dict[str, Any]] = []
    labels: list[str] = []
    ds_kg: list[float] = []
    ds_acidity: list[float] = []
    ds_rendement: list[float] = []

    for r in annotated:
        name: str = str(r.get("name") or r.get("fournisseur_nom") or "Inconnu")
        kg: float = _safe_float(r.get("kg") or r.get("quantite_totale_kg"), 0.0)
        acidity: float = _safe_float(r.get("acidity") or r.get("acidite_moyenne"), 0.0)
        rendement: float = _safe_float(r.get("rendement") or r.get("rendement_moyen"), 0.0)
        lots: int = int(_safe_float(r.get("lots") or r.get("nb_lots"), 0))

        suppliers.append({
            "rang": r.get("rang"),
            "name": name,
            "fournisseur_nom": name,  # backward compat
            "kg": kg,
            "acidity": acidity,
            "rendement": rendement,
            "lots": lots,
            # String variants for display (optional)
            "kg_str": r.get("kg_str", f"{kg:,.0f} kg".replace(",", " ")),
            "acidity_str": r.get("acidity_str", f"{acidity:.2f} %".replace(".", ",")),
            "rendement_str": r.get("rendement_str", f"{rendement:.1f} %".replace(".", ",")),
            # Status flags
            "acidite_status": r.get("acidite_status", "ok"),
            "rendement_status": r.get("rendement_status", "ok"),
        })

        labels.append(name)
        ds_kg.append(kg)
        ds_acidity.append(acidity)
        ds_rendement.append(rendement)

    datasets = [
        {"label": "Quantité totale (kg)", "data": ds_kg, "type": "bar"},
        {"label": "Acidité moyenne (%)", "data": ds_acidity, "type": "line"},
        {"label": "Rendement moyen (%)", "data": ds_rendement, "type": "line"},
    ]

    return {
        "suppliers": suppliers,
        # Chart.js-compatible multi-dataset structure
        "labels": labels,
        "datasets": datasets,
    }


def _annotate_machines(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate machine usage rows with guaranteed numeric fields."""
    annotated: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        nom: str = r.get("nomMachine") or r.get("nom_machine") or "Machine inconnue"
        ref: str = r.get("machineRef") or r.get("machine_ref") or "N/D"
        nb_exec: int = int(_safe_float(r.get("nbExecutions") or r.get("nb_executions"), 0))
        rend_moy: float = _safe_float(r.get("rendementMoyen") or r.get("rendement_moyen"), 0.0)
        total_prod: float = _safe_float(r.get("totalProduit") or r.get("total_produit"), 0.0)

        nr = dict(r)
        nr["rang"] = idx
        nr["nomMachine"] = nom
        nr["machineRef"] = ref
        nr["nbExecutions"] = nb_exec
        nr["rendementMoyen"] = rend_moy
        nr["totalProduit"] = total_prod
        nr["name"] = nom

        # String variants for display
        nr["nb_exec_str"] = str(nb_exec)
        nr["rend_str"] = f"{rend_moy:.1f} %".replace(".", ",")
        nr["prod_str"] = f"{total_prod:,.0f} L".replace(",", " ")

        annotated.append(nr)
    return annotated


def _build_machines_payload(annotated: list[dict[str, Any]]) -> dict[str, Any]:
    """Build chart-friendly payload for machine ranking."""
    machines: list[dict[str, Any]] = []
    labels: list[str] = []
    ds_exec: list[int] = []
    ds_rend: list[float] = []
    ds_prod: list[float] = []

    for r in annotated:
        nom = r.get("name") or r.get("nomMachine") or "Inconnue"
        nb_exec = int(_safe_float(r.get("nbExecutions"), 0))
        rend_moy = _safe_float(r.get("rendementMoyen"), 0.0)
        total_prod = _safe_float(r.get("totalProduit"), 0.0)

        machines.append({
            "rang": r.get("rang"),
            "name": nom,
            "nomMachine": nom,
            "machineRef": r.get("machineRef", "N/D"),
            "nbExecutions": nb_exec,
            "rendementMoyen": rend_moy,
            "totalProduit": total_prod,
            "nb_exec_str": r.get("nb_exec_str"),
            "rend_str": r.get("rend_str"),
            "prod_str": r.get("prod_str"),
        })

        labels.append(nom)
        ds_exec.append(nb_exec)
        ds_rend.append(rend_moy)
        ds_prod.append(total_prod)

    datasets = [
        {"label": "Exécutions", "data": ds_exec, "type": "bar"},
        {"label": "Rendement moyen (%)", "data": ds_rend, "type": "line"},
        {"label": "Production (L)", "data": ds_prod, "type": "bar"},
    ]

    return {
        "machines": machines,
        "labels": labels,
        "datasets": datasets,
    }


def _annotate_lots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate lot list rows with guaranteed numeric fields."""
    annotated: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        ref: str = r.get("reference") or "N/D"
        var: str = r.get("variete") or "N/D"
        fournisseur: str = r.get("fournisseur_nom") or "N/D"
        qte: float = _safe_float(r.get("quantite_initiale"), 0.0)
        qualite: str = r.get("qualite_huile") or "N/D"

        nr = dict(r)
        nr["rang"] = idx
        nr["reference"] = ref
        nr["variete"] = var
        nr["fournisseur_nom"] = fournisseur
        nr["quantite_initiale"] = qte
        nr["qualite_huile"] = qualite
        nr["name"] = ref

        nr["qte_str"] = f"{qte:,.0f} kg".replace(",", " ")
        annotated.append(nr)
    return annotated


def _build_lots_payload(annotated: list[dict[str, Any]]) -> dict[str, Any]:
    """Build chart-friendly payload for lot listing."""
    lots: list[dict[str, Any]] = []
    labels: list[str] = []
    ds_qte: list[float] = []

    for r in annotated:
        ref = r.get("name") or r.get("reference") or "N/D"
        qte = _safe_float(r.get("quantite_initiale"), 0.0)

        lots.append({
            "rang": r.get("rang"),
            "name": ref,
            "reference": ref,
            "variete": r.get("variete", "N/D"),
            "fournisseur_nom": r.get("fournisseur_nom", "N/D"),
            "quantite_initiale": qte,
            "qualite_huile": r.get("qualite_huile", "N/D"),
            "qte_str": r.get("qte_str"),
        })

        labels.append(ref)
        ds_qte.append(qte)

    datasets = [
        {"label": "Quantité (kg)", "data": ds_qte, "type": "bar"},
    ]

    return {
        "lots": lots,
        "labels": labels,
        "datasets": datasets,
    }


def _annotate_analyses(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate lab analysis rows with guaranteed numeric fields."""
    annotated: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        lot_ref: str = r.get("lot_ref") or "N/D"
        date: str = r.get("date_analyse") or "N/D"
        acidity: float = _safe_float(r.get("acidite_huile_pourcent"), 0.0)
        peroxide: float = _safe_float(r.get("indice_peroxyde_meq_o2_kg"), 0.0)
        k270: float = _safe_float(r.get("k270"), 0.0)

        # Status flags for quality
        acidity_status = "ok" if 0.2 <= acidity <= 0.8 else "out of range"
        peroxide_status = "ok" if peroxide <= 20.0 else "out of range"
        k270_status = "ok" if k270 <= 0.25 else "out of range"

        nr = dict(r)
        nr["rang"] = idx
        nr["lot_ref"] = lot_ref
        nr["date_analyse"] = date
        nr["acidite_huile_pourcent"] = acidity
        nr["indice_peroxyde_meq_o2_kg"] = peroxide
        nr["k270"] = k270
        nr["name"] = lot_ref

        # String variants
        nr["acid_str"] = f"{acidity:.2f} %".replace(".", ",")
        nr["peroxide_str"] = f"{peroxide:.1f}".replace(".", ",")
        nr["k270_str"] = f"{k270:.3f}".replace(".", ",")

        # Status
        nr["acidity_status"] = acidity_status
        nr["peroxide_status"] = peroxide_status
        nr["k270_status"] = k270_status

        annotated.append(nr)
    return annotated


def _build_analyses_payload(annotated: list[dict[str, Any]]) -> dict[str, Any]:
    """Build chart-friendly payload for lab analysis ranking."""
    analyses: list[dict[str, Any]] = []
    labels: list[str] = []
    ds_acid: list[float] = []
    ds_perox: list[float] = []
    ds_k270: list[float] = []

    for r in annotated:
        lot_ref = r.get("name") or r.get("lot_ref") or "N/D"
        acidity = _safe_float(r.get("acidite_huile_pourcent"), 0.0)
        peroxide = _safe_float(r.get("indice_peroxyde_meq_o2_kg"), 0.0)
        k270 = _safe_float(r.get("k270"), 0.0)

        analyses.append({
            "rang": r.get("rang"),
            "name": lot_ref,
            "lot_ref": lot_ref,
            "date_analyse": r.get("date_analyse", "N/D"),
            "acidite_huile_pourcent": acidity,
            "indice_peroxyde_meq_o2_kg": peroxide,
            "k270": k270,
            "acid_str": r.get("acid_str"),
            "peroxide_str": r.get("peroxide_str"),
            "k270_str": r.get("k270_str"),
            "acidity_status": r.get("acidity_status"),
            "peroxide_status": r.get("peroxide_status"),
            "k270_status": r.get("k270_status"),
        })

        labels.append(lot_ref)
        ds_acid.append(acidity)
        ds_perox.append(peroxide)
        ds_k270.append(k270)

    datasets = [
        {"label": "Acidité (%)", "data": ds_acid, "type": "bar"},
        {"label": "Peroxyde (meq O2/kg)", "data": ds_perox, "type": "line"},
        {"label": "K270", "data": ds_k270, "type": "line"},
    ]

    return {
        "analyses": analyses,
        "labels": labels,
        "datasets": datasets,
    }


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

    # ── Dispatch ─────────────────────────────────────────────────────────────

    response_text = ""
    response_data = None

    # --- STOCK ---------------------------------------------------------------
    if intent == "stock":
        result = service.get_stock(huilerie, None, None, user_enterprise_id)
        rows = result.get("value") or []

        if not rows:
            scope_part = f" pour l'huilerie **{huilerie}**" if huilerie else ""
            response_text = f"Aucune donnée de stock disponible{scope_part}.{ctx_note}"
            response_data = []
        else:
            # Texte résumé
            lines = []
            for r in rows:
                ref  = r.get("reference_stock") or "N/D"
                var  = r.get("variete") or "Inconnue"
                qte  = r.get("quantite_disponible") or r.get("total_stock") or 0
                lot  = r.get("lot_reference") or ""
                lot_part = f" | lot : **{lot}**" if lot else ""
                lines.append(f"- **{ref}** | {var} | **{_fmt(qte)} kg**{lot_part}")

            scope_part = f" de l'huilerie **{huilerie}**" if huilerie else ""
            response_text = f"Stock{scope_part} :\n" + "\n".join(lines) + ctx_note

            # Données structurées pour le widget Angular
            response_data = rows

    # --- PRODUCTION ----------------------------------------------------------
    elif intent == "production":
        query_start_date = start_date if explicit_period else None
        query_end_date = end_date if explicit_period else None
        result = service.get_production(huilerie, query_start_date, query_end_date, user_enterprise_id)
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
        # Only apply date filter if user explicitly mentioned a period
        query_start_date = start_date if explicit_period else None
        query_end_date = end_date if explicit_period else None
        result = service.get_machines_utilisees(huilerie, query_start_date, query_end_date, user_enterprise_id)
        rows = result.get("value") or []
        if not rows:
            response_text = f"Aucune donnée d'utilisation machines {scope_text}.{ctx_note}"
        else:
            lines = []
            for r in rows[:5]:
                nom = r.get('nomMachine') or r.get('nom_machine') or r.get('nom', 'Machine inconnue')
                nb = r.get('nbExecutions') or r.get('nb_executions') or 0
                rend = r.get('rendementMoyen') or r.get('rendement_moyen') or 0.0
                total = r.get('totalProduit') or r.get('total_produit') or 0.0
                lines.append(
                    f"- **{nom}** — {nb} exécution(s), "
                    f"rendement {_fmt(rend, 1)} %, {_fmt(total)} L produits"
                )
            extra = f" *(+{len(rows) - 5} autres)*" if len(rows) > 5 else ""
            response_text = f"Machines les plus utilisées {scope_text} :\n" + "\n".join(lines) + extra + ctx_note
        response_data = rows

    # --- RENDEMENT -----------------------------------------------------------
    elif intent == "rendement":
        query_start_date = start_date if explicit_period else None
        query_end_date = end_date if explicit_period else None
        result = service.get_rendement(huilerie, query_start_date, query_end_date, user_enterprise_id)
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
        query_start_date = start_date if explicit_period else None
        query_end_date = end_date if explicit_period else None
        result = service.get_qualite(huilerie, query_start_date, query_end_date, user_enterprise_id)
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

    # --- MEILLEUR FOURNISSEUR ------------------------------------------------
    elif intent == "fournisseur":
        query_start_date = start_date if explicit_period else None
        query_end_date = end_date if explicit_period else None
        result = service.get_meilleur_fournisseur(huilerie, query_start_date, query_end_date, user_enterprise_id)
        rows = result.get("value") or []
        if not rows:
            response_text = f"Aucune donnée fournisseur disponible pour {period_text}.{ctx_note}"
        else:
            annotated = _annotate_fournisseurs(rows)
            lines = []
            for r in annotated[:8]:
                acid_flag = " ⚠️" if r.get("acidite_status") == "out of range" else ""
                rend_flag = " ⚠️" if r.get("rendement_status") == "out of range" else ""
                lines.append(
                    f"{r.get('rang', '?')}. **{r.get('fournisseur_nom')}** — {r.get('lots', 0)} lot(s), "
                    f"{_fmt(r.get('kg'))} kg, rendement {_fmt(r.get('rendement'), 1)} %{rend_flag}, "
                    f"acidité {_fmt(r.get('acidity'), 2)} %{acid_flag}"
                )
            extra = f" *(+{len(rows) - 8} autres)*" if len(rows) > 8 else ""
            response_text = f"Classement fournisseurs {scope_text} :\n" + "\n".join(lines) + extra + ctx_note
        response_data = rows

    # --- CYCLE DE VIE D'UN LOT -----------------------------------------------
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

    # --- LISTE LOTS ----------------------------------------------------------
    elif intent == "lot_liste":
        query_start_date = start_date if explicit_period else None
        query_end_date = end_date if explicit_period else None
        non_conf = any(kw in payload.message.lower() for kw in ["non conforme", "lampante", "mauvaise"])
        result = service.get_lot_liste(
            huilerie, query_start_date, query_end_date, user_enterprise_id,
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

    # --- CAMPAGNE ------------------------------------------------------------
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

    # --- ANALYSE LABO --------------------------------------------------------
    elif intent == "analyse_labo":
        lot_ref = entities.get("lot_reference") or entities.get("code_lot")
        result = service.get_analyse_labo(huilerie, start_date, end_date, user_enterprise_id, lot_ref)
        rows = result.get("value") or []
        if not rows:
            response_text = f"Aucune analyse laboratoire pour {period_text}.{ctx_note}"
        else:
            lines = []
            for r in rows[:8]:
                lines.append(
                    f"- Lot **{r.get('lot_ref')}** ({r.get('date_analyse')}) — "
                    f"acidité {_fmt(r.get('acidite_huile_pourcent'), 2)} %, "
                    f"peroxyde {_fmt(r.get('indice_peroxyde_meq_o2_kg'), 1)}, "
                    f"K270 {_fmt(r.get('k270'), 3)}"
                )
            extra = f" *(+{len(rows) - 8} autres)*" if len(rows) > 8 else ""
            response_text = f"Analyses laboratoire {scope_text} :\n" + "\n".join(lines) + extra + ctx_note
        response_data = rows

    # --- MOUVEMENT STOCK -----------------------------------------------------
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

    # --- RECEPTION -----------------------------------------------------------
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