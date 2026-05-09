"""Build final ChatResponse objects from service results."""
from typing import Any

from app.models import ChatResponse
from app.services.session_service import SessionService
from app.services.chat_formatters import _is_chart_request, _normalize_choice, _safe_float


def _annotate_fournisseurs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        fournisseur_nom: str = r.get("fournisseur_nom") or "Inconnu"
        lots: int = int(_safe_float(r.get("nb_lots"), 0))
        kg: float = _safe_float(r.get("quantite_totale_kg"), 0.0)
        rendement: float = _safe_float(r.get("rendement_moyen"), 0.0)
        acidity: float = _safe_float(r.get("acidite_moyenne"), 0.0)

        nr = dict(r)
        nr["rang"] = idx
        nr["fournisseur_nom"] = fournisseur_nom
        nr["lots"] = lots
        nr["kg"] = kg
        nr["rendement"] = rendement
        nr["acidity"] = acidity
        nr["name"] = fournisseur_nom
        nr["kg_str"] = f"{kg:,.0f} kg".replace(",", " ")
        nr["acidity_str"] = f"{acidity:.2f} %".replace(".", ",")
        nr["rendement_str"] = f"{rendement:.1f} %".replace(".", ",")
        nr["acidite_status"] = "ok" if 0.5 <= acidity <= 2.0 else "out of range"
        nr["rendement_status"] = "ok" if rendement >= 10.0 else "out of range"
        annotated.append(nr)
    return annotated


def _build_fournisseur_payload(annotated: list[dict[str, Any]]) -> dict[str, Any]:
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
            "fournisseur_nom": name,
            "kg": kg,
            "acidity": acidity,
            "rendement": rendement,
            "lots": lots,
            "kg_str": r.get("kg_str", f"{kg:,.0f} kg".replace(",", " ")),
            "acidity_str": r.get("acidity_str", f"{acidity:.2f} %".replace(".", ",")),
            "rendement_str": r.get("rendement_str", f"{rendement:.1f} %".replace(".", ",")),
            "acidite_status": r.get("acidite_status", "ok"),
            "rendement_status": r.get("rendement_status", "ok"),
        })

        labels.append(name)
        ds_kg.append(kg)
        ds_acidity.append(acidity)
        ds_rendement.append(rendement)

    return {
        "suppliers": suppliers,
        "labels": labels,
        "datasets": [
            {"label": "Quantité totale (kg)", "data": ds_kg, "type": "bar"},
            {"label": "Acidité moyenne (%)", "data": ds_acidity, "type": "line"},
            {"label": "Rendement moyen (%)", "data": ds_rendement, "type": "line"},
        ],
    }


def _annotate_machines(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        nom: str = r.get("nomMachine") or r.get("nom_machine") or "Machine inconnue"
        ref: str = r.get("machineRef") or r.get("machine_ref") or "N/D"
        etat: str = r.get("etatMachine") or r.get("etat_machine") or r.get("etat") or "INCONNU"
        nb_exec: int = int(_safe_float(r.get("nbExecutions") or r.get("nb_executions"), 0))
        rend_moy: float = _safe_float(r.get("rendementMoyen") or r.get("rendement_moyen"), 0.0)
        total_prod: float = _safe_float(r.get("totalProduit") or r.get("total_produit"), 0.0)

        nr = dict(r)
        nr["rang"] = idx
        nr["nomMachine"] = nom
        nr["machineRef"] = ref
        nr["etatMachine"] = etat
        nr["nbExecutions"] = nb_exec
        nr["rendementMoyen"] = rend_moy
        nr["totalProduit"] = total_prod
        nr["name"] = nom
        nr["nb_exec_str"] = str(nb_exec)
        nr["rend_str"] = f"{rend_moy:.1f} %".replace(".", ",")
        nr["prod_str"] = f"{total_prod:,.0f} L".replace(",", " ")
        annotated.append(nr)
    return annotated


def _build_machines_payload(annotated: list[dict[str, Any]]) -> dict[str, Any]:
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
            "etatMachine": r.get("etatMachine", "INCONNU"),
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

    return {
        "machines": machines,
        "labels": labels,
        "datasets": [
            {"label": "Exécutions", "data": ds_exec, "type": "bar"},
            {"label": "Rendement moyen (%)", "data": ds_rend, "type": "line"},
            {"label": "Production (L)", "data": ds_prod, "type": "bar"},
        ],
    }


def _annotate_lots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

    return {
        "lots": lots,
        "labels": labels,
        "datasets": [{"label": "Quantité (kg)", "data": ds_qte, "type": "bar"}],
    }


def _annotate_analyses(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        lot_ref: str = r.get("lot_ref") or "N/D"
        date: str = r.get("date_analyse") or "N/D"
        acidity: float = _safe_float(r.get("acidite_huile_pourcent"), 0.0)
        peroxide: float = _safe_float(r.get("indice_peroxyde_meq_o2_kg"), 0.0)
        k270: float = _safe_float(r.get("k270"), 0.0)

        nr = dict(r)
        nr["rang"] = idx
        nr["lot_ref"] = lot_ref
        nr["date_analyse"] = date
        nr["acidite_huile_pourcent"] = acidity
        nr["indice_peroxyde_meq_o2_kg"] = peroxide
        nr["k270"] = k270
        nr["name"] = lot_ref
        nr["acid_str"] = f"{acidity:.2f} %".replace(".", ",")
        nr["peroxide_str"] = f"{peroxide:.1f}".replace(".", ",")
        nr["k270_str"] = f"{k270:.3f}".replace(".", ",")
        nr["acidity_status"] = "ok" if 0.2 <= acidity <= 0.8 else "out of range"
        nr["peroxide_status"] = "ok" if peroxide <= 20.0 else "out of range"
        nr["k270_status"] = "ok" if k270 <= 0.25 else "out of range"
        annotated.append(nr)
    return annotated


def _build_analyses_payload(annotated: list[dict[str, Any]]) -> dict[str, Any]:
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

    return {
        "analyses": analyses,
        "labels": labels,
        "datasets": [
            {"label": "Acidité (%)", "data": ds_acid, "type": "bar"},
            {"label": "Peroxyde (meq O2/kg)", "data": ds_perox, "type": "line"},
            {"label": "K270", "data": ds_k270, "type": "line"},
        ],
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
                label = str(row.get("type_mouvement") or row.get("lot_ref") or row.get("reference") or row.get("label") or "Inconnu")
                compteur[label] = compteur.get(label, 0) + 1
            return [{"label": label, "value": value} for label, value in compteur.items()]

        if intent == "fournisseur":
            annotated = _annotate_fournisseurs(data)
            payload = _build_fournisseur_payload(annotated)
            return {"labels": payload["labels"], "datasets": payload["datasets"]}
        if intent == "machines_utilisees":
            annotated = _annotate_machines(data)
            payload = _build_machines_payload(annotated)
            return {"labels": payload["labels"], "datasets": payload["datasets"]}
        if intent == "lot_liste":
            annotated = _annotate_lots(data)
            payload = _build_lots_payload(annotated)
            return {"labels": payload["labels"], "datasets": payload["datasets"]}
        if intent == "analyse_labo":
            annotated = _annotate_analyses(data)
            payload = _build_analyses_payload(annotated)
            return {"labels": payload["labels"], "datasets": payload["datasets"]}

        label_keys = {
            "stock": ["variete", "label"],
            "fournisseur": ["fournisseur_nom", "name", "label"],
            "machines_utilisees": ["nomMachine", "machineRef", "nom_machine", "machine_ref", "label"],
            "lot_liste": ["reference", "lot_ref", "label"],
            "campagne": ["reference", "annee", "label"],
            "analyse_labo": ["lot_ref", "reference", "label"],
            "reception": ["reference", "lot_ref", "label"],
        }
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
            labels.append(str(label if label is not None else f"Item {index}"))

        preferred_order = list(dict.fromkeys(preferred_values + [
            "quantite_totale_kg", "quantite_initiale", "total_produit", "total_stock",
            "rendement_moyen", "acidite_huile_pourcent", "indice_peroxyde_meq_o2_kg", "k270",
            "value", "total", "count", "nb_lots"
        ]))
        for cv in ["quantiteTotaleKg", "quantiteInitiale", "totalProduit", "totalStock", "rendementMoyen", "aciditeMoyenne", "indicePeroxydeMeqO2Kg", "k270", "value", "total", "count", "nbLots", "nbExecutions"]:
            if cv not in preferred_order:
                preferred_order.append(cv)

        metrics: list[str] = [key for key in preferred_order if any(row.get(key) not in (None, "") for row in data)]
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
            return [{"label": labels[i], "value": _safe_float(row.get(metric), 0.0)} for i, row in enumerate(data)]

        datasets: list[dict[str, Any]] = []
        for metric in metrics:
            series = [_safe_float(row.get(metric), 0.0) for row in data]
            datasets.append({"label": metric.replace("_", " ").title(), "data": series})
        return {"labels": labels, "datasets": datasets}

    if isinstance(data, dict):
        if "labels" in data and "datasets" in data:
            return data
        summary = data.get("summary")
        if isinstance(summary, dict) and summary:
            return [{"label": str(label), "value": _safe_float(value, 0.0)} for label, value in summary.items()]
        return [{"label": key.replace("_", " ").title(), "value": float(value)} for key, value in data.items() if isinstance(value, (int, float))]

    if isinstance(data, (int, float)):
        return [{"label": intent.replace("_", " ").title(), "value": float(data)}]
    return []


def build_chat_response(
    *,
    session_service: SessionService,
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
    """
    Construire la réponse HTTP finale (texte/graphique/choix).

    Cette logique était auparavant dans chat_formatters.py puis a été
    déplacée dans un module dédié pour mieux séparer le shaping de données
    et la construction finale de la réponse API.
    """
    ctx = session_service.get(session_id)
    selected_choice = _normalize_choice(payload_message)
    pending = session_service.get_pending_visualization(session_id)

    if selected_choice and pending:
        chart_data = pending.get("chart_data") or []
        chart_type = pending.get("chart_type") or "bar"
        if selected_choice == "texte":
            session_service.clear_pending_visualization(session_id)
            text_message = pending.get("text_message") or response_text
            pending_intent = pending.get("intent") or intent
            return ChatResponse(
                type="text",
                message=text_message,
                intent=pending_intent,
                confidence=confidence,
                entities=entities,
                response=text_message,
                data=pending.get("raw_data"),
                applied_scope=applied_scope,
                applied_permissions=applied_permissions,
                selected_option="texte",
            )
        if selected_choice == "graphique":
            session_service.clear_pending_visualization(session_id)
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
    ranking_intents = {"fournisseur", "machines_utilisees", "lot_liste", "analyse_labo"}

    if intent in ranking_intents and isinstance(response_data, list) and response_data:
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
        else:
            structured_payload = None
            title_default = "Voici une visualisation des résultats."

        if structured_payload:
            chart_data = {"labels": structured_payload["labels"], "datasets": structured_payload["datasets"]}
            chart_type = "bar"

            if wants_chart:
                session_service.clear_pending_visualization(session_id)
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
                session_service.set_pending_visualization(session_id, {
                    "text_message": response_text,
                    "chart_data": chart_data,
                    "chart_type": chart_type,
                    "raw_data": structured_payload,
                    "intent": intent,
                })
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

            session_service.clear_pending_visualization(session_id)
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
            session_service.clear_pending_visualization(session_id)
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

        session_service.set_pending_visualization(session_id, {
            "text_message": response_text,
            "chart_data": chart_data,
            "chart_type": chart_type,
            "raw_data": response_data,
            "intent": intent,
        })
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

    session_service.clear_pending_visualization(session_id)
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