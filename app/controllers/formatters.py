from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def annotate_fournisseurs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for r in rows:
        kg: float = _safe_float(r.get("quantite_totale_kg"), 0.0)
        acidity: float = _safe_float(r.get("acidite_moyenne"), 0.0)
        rendement: float = _safe_float(r.get("rendement_moyen"), 0.0)
        lots: int = int(_safe_float(r.get("nb_lots"), 0))

        acid_status = "ok" if 0.2 <= acidity <= 1.5 else "out of range"
        rend_status = "ok" if 10.0 <= rendement <= 30.0 else "out of range"

        kg_str = f"{kg:,.0f} kg".replace(",", " ")
        acidity_str = f"{acidity:.2f} %".replace(".", ",")
        rendement_str = f"{rendement:.1f} %".replace(".", ",")

        nr = dict(r)
        nr["kg"] = kg
        nr["acidity"] = acidity
        nr["rendement"] = rendement
        nr["lots"] = lots
        nr["quantite_totale_kg"] = kg
        nr["acidite_moyenne"] = acidity
        nr["rendement_moyen"] = rendement
        nr["nb_lots"] = lots
        nr["name"] = r.get("fournisseur_nom") or "Inconnu"
        nr["kg_str"] = kg_str
        nr["acidity_str"] = acidity_str
        nr["rendement_str"] = rendement_str
        nr["acidite_status"] = acid_status
        nr["rendement_status"] = rend_status
        annotated.append(nr)
    return annotated


def build_fournisseur_payload(annotated: list[dict[str, Any]]) -> dict[str, Any]:
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

    datasets = [
        {"label": "Quantité totale (kg)", "data": ds_kg, "type": "bar"},
        {"label": "Acidité moyenne (%)", "data": ds_acidity, "type": "line"},
        {"label": "Rendement moyen (%)", "data": ds_rendement, "type": "line"},
    ]

    return {
        "suppliers": suppliers,
        "labels": labels,
        "datasets": datasets,
    }


def annotate_machines(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

        nr["nb_exec_str"] = str(nb_exec)
        nr["rend_str"] = f"{rend_moy:.1f} %".replace(".", ",")
        nr["prod_str"] = f"{total_prod:,.0f} L".replace(",", " ")

        annotated.append(nr)
    return annotated


def build_machines_payload(annotated: list[dict[str, Any]]) -> dict[str, Any]:
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


def annotate_lots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def build_lots_payload(annotated: list[dict[str, Any]]) -> dict[str, Any]:
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


def annotate_analyses(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        lot_ref: str = r.get("lot_ref") or "N/D"
        date: str = r.get("date_analyse") or "N/D"
        acidity: float = _safe_float(r.get("acidite_huile_pourcent"), 0.0)
        peroxide: float = _safe_float(r.get("indice_peroxyde_meq_o2_kg"), 0.0)
        k270: float = _safe_float(r.get("k270"), 0.0)

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

        nr["acid_str"] = f"{acidity:.2f} %".replace(".", ",")
        nr["peroxide_str"] = f"{peroxide:.1f}".replace(".", ",")
        nr["k270_str"] = f"{k270:.3f}".replace(".", ",")

        nr["acidity_status"] = acidity_status
        nr["peroxide_status"] = peroxide_status
        nr["k270_status"] = k270_status

        annotated.append(nr)
    return annotated


def build_analyses_payload(annotated: list[dict[str, Any]]) -> dict[str, Any]:
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
