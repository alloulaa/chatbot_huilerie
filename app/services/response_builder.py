"""Build final ChatResponse objects from service results."""
from typing import Any

from app.models import ChatResponse
from app.services.session_service import SessionService
from app.services.chat_formatters import _is_chart_request, _normalize_choice, _safe_float

# Intents qui NE proposent PAS le choix texte/graphique
# Ajouter "machine" : l'intent machine doit toujours retourner du texte
_NO_CHOICE_INTENTS = {"explication", "inconnu", "machine", "lot_cycle_vie", "prediction"}


def _annotate_fournisseurs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        fournisseur_nom: str = r.get("name") or r.get("fournisseur_nom") or "Inconnu"
        lots: int = int(_safe_float(r.get("lots") or r.get("nb_lots"), 0))
        kg: float = _safe_float(r.get("kg") or r.get("quantite_totale_kg"), 0.0)
        rendement: float = _safe_float(r.get("rendement") or r.get("rendement_moyen"), 0.0)
        acidity: float = _safe_float(r.get("acidity") or r.get("acidite_moyenne") or r.get("acidite"), 0.0)

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
        kg: float = _safe_float(r.get("kg"), 0.0)
        acidity: float = _safe_float(r.get("acidity"), 0.0)
        rendement: float = _safe_float(r.get("rendement"), 0.0)
        lots: int = int(_safe_float(r.get("lots"), 0))

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
        "items": suppliers,
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
        nom: str = r.get("nomMachine") or r.get("nom_machine") or r.get("name") or "Machine inconnue"
        ref: str = r.get("machineRef") or r.get("machine_ref") or r.get("reference") or "N/D"
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
        "items": machines,
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
        ref: str = r.get("reference") or r.get("ref") or "N/D"
        var: str = r.get("variete") or r.get("variety") or "N/D"
        fournisseur: str = r.get("fournisseur_nom") or r.get("supplier") or r.get("fournisseur") or "N/D"
        qte: float = _safe_float(r.get("quantite_initiale") or r.get("quantite") or r.get("quantity"), 0.0)
        qualite: str = r.get("qualite_huile") or r.get("qualite") or r.get("quality") or "N/D"

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
        "items": lots,
        "labels": labels,
        "datasets": [{"label": "Quantité (kg)", "data": ds_qte, "type": "bar"}],
    }


def _annotate_analyses(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        lot_ref: str = r.get("lot_ref") or r.get("reference") or r.get("lot_reference") or "N/D"
        date: str = r.get("date_analyse") or r.get("date") or "N/D"
        acidity: float = _safe_float(r.get("acidite_huile_pourcent") or r.get("acidite") or r.get("acidity"), 0.0)
        peroxide: float = _safe_float(r.get("indice_peroxyde_meq_o2_kg") or r.get("peroxyde") or r.get("peroxide"), 0.0)
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
        "items": analyses,
        "labels": labels,
        "datasets": [
            {"label": "Acidité (%)", "data": ds_acid, "type": "bar"},
            {"label": "Peroxyde (meq O2/kg)", "data": ds_perox, "type": "line"},
            {"label": "K270", "data": ds_k270, "type": "line"},
        ],
    }


def _annotate_stock(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        variete = r.get("variete") or "Inconnue"
        reference = r.get("reference_stock") or r.get("reference") or r.get("ref") or variete
        references_lots = r.get("references_lots") or r.get("lot_reference") or r.get("lots") or ""
        type_stock = r.get("type_stock") or r.get("type") or r.get("label") or "N/D"
        total = _safe_float(r.get("total_stock") or r.get("quantite_disponible"), 0.0)

        nr = dict(r)
        nr["rang"] = idx
        nr["name"] = variete
        nr["reference_stock"] = reference
        nr["reference"] = reference
        nr["variete"] = variete
        nr["references_lots"] = references_lots
        nr["lot_reference"] = references_lots
        nr["lots"] = references_lots
        nr["type"] = type_stock
        nr["type_stock"] = type_stock
        nr["total_stock"] = total
        nr["quantite"] = total
        nr["quantite_disponible"] = total
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
            "fournisseur": ["name", "fournisseur_nom", "label"],
            "machines_utilisees": ["name", "nomMachine", "machineRef", "label"],
            "machine": ["name", "nomMachine", "label"],
            "lot_liste": ["name", "reference", "lot_ref", "label"],
            "campagne": ["name", "reference", "annee", "label"],
            "analyse_labo": ["name", "lot_ref", "reference", "label"],
            "reception": ["name", "reference", "lot_ref", "label"],
        }
        value_keys = {
            "stock": ["total_stock", "quantite_disponible", "value"],
            "machines_utilisees": ["nbExecutions", "rendementMoyen", "totalProduit", "value"],
            "machine": ["nbExecutions", "rendementMoyen", "value"],
            "lot_liste": ["quantite_initiale", "value"],
            "campagne": ["total_olives_kg", "nbLots", "value"],
            "analyse_labo": ["acidite_huile_pourcent", "indicePeroxydeMeqO2Kg", "k270", "value"],
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
            "kg", "quantite_initiale", "totalProduit", "total_stock",
            "rendementMoyen", "acidite_huile_pourcent", "indicePeroxydeMeqO2Kg", "k270",
            "value", "total", "count", "nb_lots"
        ]))
        for cv in ["kg", "quantiteInitiale", "totalProduit", "totalStock", "rendementMoyen", "acidity", "indicePeroxydeMeqO2Kg", "k270", "value", "total", "count", "nbLots", "nbExecutions", "quantite_disponible"]:
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


def _build_structured_payload_for(intent: str, data: Any) -> dict[str, Any] | None:
    """
    Construire un structured_payload uniforme pour n'importe quel intent.
    Retourne None si les données ne permettent pas un graphique.
    """
    if data is None:
        return None

    # Intents avec annotateurs dédiés
    if intent == "fournisseur" and isinstance(data, list) and data:
        annotated = _annotate_fournisseurs(data)
        return _build_fournisseur_payload(annotated)
    if intent == "machines_utilisees" and isinstance(data, list) and data:
        annotated = _annotate_machines(data)
        return _build_machines_payload(annotated)
    if intent == "lot_liste" and isinstance(data, list) and data:
        annotated = _annotate_lots(data)
        return _build_lots_payload(annotated)
    if intent == "analyse_labo" and isinstance(data, list) and data:
        annotated = _annotate_analyses(data)
        return _build_analyses_payload(annotated)
    if intent == "stock" and isinstance(data, list) and data:
        annotated = _annotate_stock(data)
        labels = [r["reference_stock"] for r in annotated]
        datasets = [{"label": "Stock (kg)", "data": [r["total_stock"] for r in annotated], "type": "bar"}]
        return {"labels": labels, "datasets": datasets, "items": annotated, "value": annotated}

    # Intents scalaires : production, rendement, stock global, etc.
    chart_data = _chart_data_for(intent, data)
    if not chart_data:
        return None

    chart_type = _chart_type_for(intent, data if isinstance(data, list) else None)

    if isinstance(chart_data, list):
        labels = [item.get("label", str(i)) for i, item in enumerate(chart_data)]
        datasets = [{"label": intent.replace("_", " ").title(), "data": [item.get("value", 0) for item in chart_data], "type": chart_type}]
        return {"labels": labels, "datasets": datasets, "items": data}

    if isinstance(chart_data, dict) and "labels" in chart_data and "datasets" in chart_data:
        return {**chart_data, "items": data}

    return None


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
    Construire la réponse HTTP finale.

    Règle principale :
      - Tous les intents SAUF ceux dans _NO_CHOICE_INTENTS proposent un choix texte/graphique
        (ou affichent directement le graphique si l'utilisateur l'a demandé explicitement).
      - Les intents dans _NO_CHOICE_INTENTS (explication, inconnu) retournent toujours du texte.
    """
    ctx = session_service.get(session_id)
    selected_choice = _normalize_choice(payload_message)
    pending = session_service.get_pending_visualization(session_id)

    # ── 1. Résolution d'un choix en attente ────────────────────────────────
    if selected_choice and pending:
        chart_data = pending.get("chart_data") or []
        chart_type = pending.get("chart_type") or "bar"
        raw_data = dict(pending.get("raw_data") or {})
        pending_intent = str(pending.get("intent") or intent)

        if selected_choice == "texte":
            session_service.clear_pending_visualization(session_id)
            text_message = pending.get("text_message") or response_text
            return ChatResponse(
                type="text",
                message=text_message,
                intent=pending_intent,
                confidence=confidence,
                entities=entities,
                response=text_message,
                data=raw_data,
                applied_scope=applied_scope,
                applied_permissions=applied_permissions,
                selected_option="texte",
            )

        if selected_choice == "graphique":
            session_service.clear_pending_visualization(session_id)
            # Inclure les items dans le chart_data pour le frontend
            items = raw_data.get("items", [])
            chart_data_with_items = {**chart_data, "items": items}
            return ChatResponse(
                type="chart",
                message="Voici la visualisation demandée.",
                intent=pending_intent,
                confidence=confidence,
                entities=entities,
                response="Voici la visualisation demandée.",
                chart_type=chart_type,
                data=chart_data_with_items,
                applied_scope=applied_scope,
                applied_permissions=applied_permissions,
                selected_option="graphique",
            )

    # ── 2. Intents sans choix (explication, inconnu) → texte direct ────────
    if intent in _NO_CHOICE_INTENTS:
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

    # ── 3. Tous les autres intents : choix texte / graphique ───────────────
    wants_chart = _is_chart_request(payload_message)

    # Construire le payload graphique
    structured_payload = _build_structured_payload_for(intent, response_data)

    # Si aucune donnée graphique n'est disponible, répondre en texte directement
    if structured_payload is None:
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

    chart_data = {"labels": structured_payload.get("labels", []), "datasets": structured_payload.get("datasets", [])}
    chart_type = _chart_type_for(intent, response_data if isinstance(response_data, list) else None)

    # L'utilisateur a explicitement demandé un graphique → afficher directement
    if wants_chart:
        session_service.clear_pending_visualization(session_id)
        return ChatResponse(
            type="chart",
            message=response_text or "Voici la visualisation demandée.",
            intent=intent,
            confidence=confidence,
            entities=entities,
            response=response_text or "Voici la visualisation demandée.",
            chart_type=chart_type,
            data=chart_data,
            applied_scope=applied_scope,
            applied_permissions=applied_permissions,
        )

    # Cas standard : proposer le choix texte / graphique
    session_service.set_pending_visualization(session_id, {
        "text_message": response_text,
        "chart_data": chart_data,
        "chart_type": chart_type,
        "raw_data": structured_payload,
        "intent": intent,
    })
    question = "Souhaitez-vous voir les résultats sous forme de **texte** ou de **graphique** ?"
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