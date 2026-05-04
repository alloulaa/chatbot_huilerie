"""
Handler pour l'intent EXPLICATION.

Répond à des questions causales/explicatives sur un lot spécifique :
  "pourquoi la qualité du lot LO17 était mauvaise ?"
  "explique-moi le lot LO07"
  "qu'est-ce qui a causé la mauvaise qualité du lot 3 ?"

Ce handler est distinct des intents existants :
  - diagnostic   → analyse qualité agrégée sur une période / huilerie entière
  - lot_cycle_vie → timeline chronologique des étapes du lot
  - analyse_labo  → liste brute des résultats de laboratoire
"""
from __future__ import annotations

import logging
from typing import Any

from app.database import get_db_connection
from app.domain.chat import ChatQuery, IntentResult
from app.services.intent.base import IntentHandler
from app.services.chatbot_service import ChatbotService

logger = logging.getLogger(__name__)

SEUILS = {
    "acidite_huile_pourcent": (0.8, 2.0, None),
    "indice_peroxyde_meq_o2_kg": (20.0, 20.0, None),
    "k270": (0.22, 0.25, None),
    "k232": (2.50, 2.60, None),
}

LABEL_SEUIL = {
    "acidite_huile_pourcent": "Acidité libre (%)",
    "indice_peroxyde_meq_o2_kg": "Indice de peroxyde (meq O2/kg)",
    "k270": "Coefficient d'extinction K270",
    "k232": "Coefficient d'extinction K232",
}

ACIDITE_OLIVE_SEUIL_CRITIQUE = 3.0
MATURITE_IDEALE_MAX = 4
RENDEMENT_MIN_NORMAL = 10.0
RENDEMENT_MAX_NORMAL = 30.0


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _fmt(value: Any, decimals: int = 2) -> str:
    try:
        return f"{_safe_float(value):,.{decimals}f}".replace(",", " ")
    except Exception:
        return str(value or "N/D")


SQL_LOT = """
    SELECT
        lo.id_lot,
        lo.reference,
        lo.variete,
        lo.fournisseur_nom,
        lo.quantite_initiale,
        lo.quantite_restante,
        lo.date_reception,
        lo.date_recolte,
        lo.acidite_olives_pourcent,
        h.nom AS huilerie_nom,
        h.entreprise_id
    FROM lot_olives lo
    JOIN huilerie h ON h.id_huilerie = lo.huilerie_id
    WHERE (LOWER(lo.reference) = LOWER(%s) OR CAST(lo.id_lot AS CHAR) = %s)
"""

SQL_EXEC = """
    SELECT
        ep.reference,
        ep.date_debut,
        ep.date_fin_reelle,
        ep.statut,
        ep.rendement,
        ep.temperature_malaxage,
        ep.duree_malaxage_minutes,
        ep.presence_ajout_eau,
        m.nom_machine
    FROM execution_production ep
    LEFT JOIN machine m ON m.id_machine = ep.machine_id
    WHERE ep.lot_olives_id = %s
    ORDER BY ep.date_debut ASC
"""

SQL_LABO = """
    SELECT
        al.date_analyse,
        al.acidite_huile_pourcent,
        al.indice_peroxyde_meq_o2_kg,
        al.k270,
        al.k232,
        al.polyphenols_mg_kg
    FROM analyse_laboratoire al
    WHERE al.lot_id = %s
    ORDER BY al.date_analyse DESC
    LIMIT 5
"""


def _analyse_labo_issues(labo_rows: list[dict]) -> list[str]:
    if not labo_rows:
        return []

    r = labo_rows[0]
    issues = []

    acid = _safe_float(r.get("acidite_huile_pourcent"))
    perox = _safe_float(r.get("indice_peroxyde_meq_o2_kg"))
    k270 = _safe_float(r.get("k270"))
    k232 = _safe_float(r.get("k232"))
    polyphenols = _safe_float(r.get("polyphenols_mg_kg"))

    if acid > 0.8:
        grade = "vierge" if acid <= 2.0 else "lampante"
        issues.append(
            f"🔴 **Acidité élevée** ({_fmt(acid)} % > seuil vierge extra 0,8 %) → "
            f"huile classée au mieux **{grade}**. Cause probable : olives trop mûres, blessées, "
            f"stockées trop longtemps avant trituration ou températures de récolte/stockage élevées."
        )
    elif acid > 0.5:
        issues.append(
            f"🟡 **Acidité limite** ({_fmt(acid)} %) — encore dans la norme vierge extra (< 0,8 %) "
            f"mais proche du seuil. Surveiller la qualité à la récolte suivante."
        )

    if perox > 20.0:
        issues.append(
            f"🔴 **Indice de peroxyde élevé** ({_fmt(perox, 1)} meq O₂/kg > seuil 20) → "
            f"oxydation primaire de l'huile. Cause probable : contact prolongé avec l'air, "
            f"températures élevées lors du malaxage ou stockage inapproprié."
        )

    if k270 > 0.22:
        issues.append(
            f"🔴 **K270 hors norme** ({_fmt(k270, 3)} > seuil vierge extra 0,22) → "
            f"présence de produits d'oxydation secondaire. Cause probable : huile ancienne, "
            f"chauffage excessif ou raffinage partiel."
        )

    if k232 > 2.50:
        issues.append(
            f"🟡 **K232 élevé** ({_fmt(k232, 2)} > seuil 2,50) → diènes conjugués — signe d'oxydation en cours."
        )

    if polyphenols > 0 and polyphenols < 100:
        issues.append(
            f"🟡 **Faible teneur en polyphénols** ({_fmt(polyphenols, 0)} mg/kg) → olives sur-mûres ou extraction dans de mauvaises conditions."
        )

    return issues


def _analyse_olive_issues(lot: dict) -> list[str]:
    issues = []

    acidite_olive = _safe_float(lot.get("acidite_olives_pourcent"))
    if acidite_olive > ACIDITE_OLIVE_SEUIL_CRITIQUE:
        issues.append(
            f"🔴 **Acidité des olives à la réception élevée** ({_fmt(acidite_olive)} %) — "
            f"au-delà de {ACIDITE_OLIVE_SEUIL_CRITIQUE} %, la qualité de l'huile est presque inévitablement compromise."
        )

    maturite = lot.get("indice_maturite")
    if maturite is not None:
        m = _safe_float(maturite)
        if m > MATURITE_IDEALE_MAX:
            issues.append(
                f"🟡 **Sur-maturité des olives** (indice {_fmt(m, 1)} > idéal ≤ {MATURITE_IDEALE_MAX}) — "
                f"les olives trop mûres ont une acidité plus élevée et moins de polyphénols."
            )

    duree = _safe_float(lot.get("duree_stockage_jours"))
    if duree > 2:
        issues.append(
            f"🟡 **Délai avant trituration long** ({int(duree)} jour(s)) — les olives doivent idéalement être triturées dans les 24–48h."
        )

    temp = lot.get("temperature_stockage")
    if temp is not None and _safe_float(temp) > 20:
        issues.append(
            f"🟡 **Température de stockage élevée** ({_fmt(temp, 1)} °C > 20 °C) — accélère la dégradation enzymatique."
        )

    return issues


def _analyse_production_issues(exec_rows: list[dict]) -> list[str]:
    if not exec_rows:
        return []

    issues = []
    for ep in exec_rows:
        rend = _safe_float(ep.get("rendement"))
        temp_malax = ep.get("temperature_malaxage")
        duree_malax = ep.get("duree_malaxage_minutes")
        eau = ep.get("presence_ajout_eau")

        if rend > 0:
            if rend < RENDEMENT_MIN_NORMAL:
                issues.append(
                    f"🟡 **Rendement faible** ({_fmt(rend, 1)} % < {RENDEMENT_MIN_NORMAL} %) lors de l'exécution {ep.get('reference', '')} — "
                    f"peut indiquer des olives sèches ou un problème de centrifugation."
                )
            elif rend > RENDEMENT_MAX_NORMAL:
                issues.append(f"🟢 Rendement élevé ({_fmt(rend, 1)} %) lors de {ep.get('reference', '')}.")

        if temp_malax is not None and _safe_float(temp_malax) > 27:
            issues.append(
                f"🔴 **Malaxage chaud** ({_fmt(temp_malax, 1)} °C > 27 °C) pour {ep.get('reference', '')} — "
                f"augmente le rendement mais dégrade les polyphénols et accélère l'oxydation."
            )

        if duree_malax is not None and _safe_float(duree_malax) > 45:
            issues.append(
                f"🟡 **Malaxage prolongé** ({int(_safe_float(duree_malax))} min > 45 min) — expose davantage l'huile à l'oxygène."
            )

        if eau in (1, True, "1", "oui", "yes", "true"):
            issues.append(
                f"🟡 **Ajout d'eau lors du malaxage** ({ep.get('reference', '')}) — dilue les polyphénols et peut augmenter l'indice de peroxyde."
            )

    return issues


def _build_explanation(lot: dict, exec_rows: list[dict], labo_rows: list[dict]) -> str:
    lot_ref = lot.get("reference", "?")
    variete = lot.get("variete") or "variété inconnue"
    fournisseur = lot.get("fournisseur_nom") or "fournisseur inconnu"
    huilerie = lot.get("huilerie_nom") or "huilerie inconnue"
    date_rec = lot.get("date_reception") or "date inconnue"

    qualite_finale = "non déterminée"
    if labo_rows:
        r = labo_rows[0]
        acid = _safe_float(r.get("acidite_huile_pourcent"))
        perox = _safe_float(r.get("indice_peroxyde_meq_o2_kg"))
        k270 = _safe_float(r.get("k270"))
        if acid <= 0.8 and perox <= 20 and k270 <= 0.22:
            qualite_finale = "✅ **Vierge Extra** (tous les paramètres conformes)"
        elif acid <= 2.0 and perox <= 20:
            qualite_finale = "⚠️ **Vierge** (acidité hors norme vierge extra)"
        else:
            qualite_finale = "❌ **Lampante** (non consommable directement)"

    olive_issues = _analyse_olive_issues(lot)
    prod_issues = _analyse_production_issues(exec_rows)
    labo_issues = _analyse_labo_issues(labo_rows)

    all_issues = olive_issues + prod_issues + labo_issues
    nb_issues = len([i for i in all_issues if i.startswith("🔴")])

    lines = [
        f"## Analyse du lot **{lot_ref}**",
        f"",
        f"**Variété** : {variete} | **Fournisseur** : {fournisseur} | **Huilerie** : {huilerie} | **Réception** : {date_rec}",
        f"**Quantité initiale** : {_fmt(_safe_float(lot.get('quantite_initiale')), 0)} kg",
        f"",
        f"### 🧪 Qualité finale : {qualite_finale}",
        f"",
    ]

    if not all_issues:
        lines.append(
            "✅ Aucun facteur anormal détecté — toutes les conditions de réception, de trituration et d'analyse sont dans les normes."
        )
        return "\n".join(lines)

    if olive_issues:
        lines.append("### 🫒 Facteurs liés aux olives à la réception")
        lines.extend(olive_issues)
        lines.append("")

    if prod_issues:
        lines.append("### ⚙️ Facteurs liés aux conditions de trituration")
        lines.extend(prod_issues)
        lines.append("")

    if labo_issues:
        lines.append("### 📊 Résultats laboratoire")
        if labo_rows:
            r = labo_rows[0]
            lines.append(
                f"*(Analyse du {r.get('date_analyse', '?')} — acidité {_fmt(r.get('acidite_huile_pourcent'))} %, peroxyde {_fmt(r.get('indice_peroxyde_meq_o2_kg'), 1)}, K270 {_fmt(r.get('k270'), 3)})*"
            )
        lines.extend(labo_issues)
        lines.append("")

    if nb_issues > 0:
        lines.append(
            f"### 🔎 Conclusion\n{nb_issues} facteur(s) critique(s) identifié(s). La qualité de ce lot a été principalement affectée par : "
            + ", ".join(i.split("**")[1] for i in all_issues if i.startswith("🔴") and "**" in i)
            + "."
        )
    else:
        lines.append(
            "### 🔎 Conclusion\nAucun facteur critique, mais des points d'amélioration ont été détectés (signalés en 🟡)."
        )

    return "\n".join(lines)


class ExplicationHandler(IntentHandler):
    """Handler pour expliquer la qualité / le comportement d'un lot spécifique."""

    def __init__(self, service: ChatbotService):
        self.service = service

    async def handle(self, query: ChatQuery) -> IntentResult:
        lot_ref = (
            query.extra_context.get("lot_reference")
            or query.extra_context.get("code_lot")
            or getattr(query, "lot_reference", None)
            or getattr(query, "code_lot", None)
        )

        if not lot_ref and query.extra_context.get("entities"):
            entities = query.extra_context["entities"]
            lot_ref = entities.get("lot_reference") or entities.get("reference_lot") or entities.get("code_lot")

        if not lot_ref:
            return IntentResult(
                text=(
                    "Précisez la référence du lot pour que je puisse l'analyser. "
                    "Exemple : *\"pourquoi la qualité du lot LO17 était mauvaise ?\"*"
                ),
                data=None,
                structured_payload=None,
            )

        normalized_ref = self.service._normalize_lot_reference(lot_ref)
        if not normalized_ref:
            return IntentResult(
                text=f"Référence de lot invalide : **{lot_ref}**.",
                data=None,
                structured_payload=None,
            )

        connection = cursor = None
        lot_row = None
        exec_rows: list[dict] = []
        labo_rows: list[dict] = []

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            # Build SELECT dynamically based on available columns in `lot_olives`
            cursor.execute("DESCRIBE lot_olives")
            cols = [c["Field"] for c in (cursor.fetchall() or [])]

            base_fields = [
                "lo.id_lot",
                "lo.reference",
                "lo.variete",
                "lo.fournisseur_nom",
                "lo.quantite_initiale",
                "lo.quantite_restante",
                "lo.date_reception",
                "lo.date_recolte",
            ]
            optional_fields = []
            for f in [
                "acidite_olives_pourcent",
                "indice_maturite",
                "temperature_stockage",
                "duree_stockage_jours",
            ]:
                if f in cols:
                    optional_fields.append(f"lo.{f}")

            select_fields = base_fields + optional_fields + ["h.nom AS huilerie_nom", "h.entreprise_id"]
            q_lot = "SELECT " + ", ".join(select_fields) + " FROM lot_olives lo JOIN huilerie h ON h.id_huilerie = lo.huilerie_id"

            params: list[Any] = [normalized_ref, normalized_ref]
            q_lot += " WHERE (LOWER(lo.reference) = LOWER(%s) OR CAST(lo.id_lot AS CHAR) = %s)"
            if query.enterprise_id:
                q_lot += " AND h.entreprise_id = %s"
                params.append(query.enterprise_id)
            q_lot += " LIMIT 1"

            cursor.execute(q_lot, params)
            lot_row = cursor.fetchone()

            if not lot_row:
                return IntentResult(
                    text=f"Aucun lot trouvé pour la référence **{normalized_ref}**.",
                    data=None,
                    structured_payload=None,
                )

            lot_id = lot_row["id_lot"]

            # Build execution SELECT dynamically based on available columns in execution_production
            cursor.execute("DESCRIBE execution_production")
            exec_cols = [c["Field"] for c in (cursor.fetchall() or [])]
            exec_base = [
                "ep.reference",
                "ep.date_debut",
                "ep.date_fin_reelle",
                "ep.statut",
                "ep.rendement",
            ]
            exec_optional = []
            for ef in ["temperature_malaxage", "duree_malaxage_minutes", "presence_ajout_eau", "machine_id", "machine_id"]:
                if ef in exec_cols:
                    exec_optional.append(f"ep.{ef}")

            # include machine name if machine table and join possible
            # we'll left join machine and select its name as nom_machine
            select_exec_fields = exec_base + exec_optional + ["m.nom_machine"]
            q_exec = "SELECT " + ", ".join(select_exec_fields) + " FROM execution_production ep LEFT JOIN machine m ON m.id_machine = ep.machine_id WHERE ep.lot_olives_id = %s ORDER BY ep.date_debut ASC"
            try:
                cursor.execute(q_exec, (lot_id,))
                exec_rows = cursor.fetchall() or []
            except Exception:
                # fallback to minimal execution query if dynamic one fails
                cursor.execute("SELECT reference, date_debut, date_fin_reelle, statut, rendement FROM execution_production WHERE lot_olives_id = %s ORDER BY date_debut ASC", (lot_id,))
                exec_rows = cursor.fetchall() or []

            cursor.execute(SQL_LABO, (lot_id,))
            labo_rows = cursor.fetchall() or []

        except Exception as exc:
            logger.exception("Error fetching lot explanation data for %s: %s", normalized_ref, exc)
            return IntentResult(
                text="Impossible de récupérer les données du lot. Vérifiez la connexion à la base.",
                data=None,
                structured_payload=None,
            )
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

        explanation = _build_explanation(lot_row, exec_rows, labo_rows)

        chart_data = None
        if labo_rows:
            r = labo_rows[0]
            chart_data = {
                "labels": ["Acidité (%)", "Peroxyde (meq O2/kg)", "K270", "K232"],
                "datasets": [
                    {
                        "label": f"Lot {normalized_ref}",
                        "data": [
                            _safe_float(r.get("acidite_huile_pourcent")),
                            _safe_float(r.get("indice_peroxyde_meq_o2_kg")),
                            _safe_float(r.get("k270")),
                            _safe_float(r.get("k232")),
                        ],
                        "type": "bar",
                    },
                    {
                        "label": "Seuil vierge extra",
                        "data": [0.8, 20.0, 0.22, 2.50],
                        "type": "line",
                    },
                ],
            }

        return IntentResult(
            text=explanation,
            data={"lot": dict(lot_row), "executions": exec_rows, "analyses": labo_rows},
            structured_payload=None,
        )
