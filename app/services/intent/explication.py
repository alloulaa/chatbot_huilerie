"""
Handler pour l'intent EXPLICATION.

RÃ©pond Ã  des questions causales/explicatives sur un lot spÃ©cifique :
  "pourquoi la qualitÃ© du lot LO17 Ã©tait mauvaise ?"
  "explique-moi le lot LO07"
  "qu'est-ce qui a causÃ© la mauvaise qualitÃ© du lot 3 ?"

Ce handler est distinct des intents existants :
  - diagnostic   â†’ analyse qualitÃ© agrÃ©gÃ©e sur une pÃ©riode / huilerie entiÃ¨re
  - lot_cycle_vie â†’ timeline chronologique des Ã©tapes du lot
  - analyse_labo  â†’ liste brute des rÃ©sultats de laboratoire
"""
from __future__ import annotations

import logging
import re
from typing import Any

from app.database import get_db_connection
from app.domain.chat import ChatQuery, IntentResult
from app.services.intent.base import IntentHandler
from app.services.query_service import ChatbotService

logger = logging.getLogger(__name__)

SEUILS = {
    "acidite_huile_pourcent": (0.1, 5.0, None),
    "indice_peroxyde_meq_o2_kg": (5.0, 40.0, None),
    "polyphenols_mg_kg": (100.0, 800.0, None),
    "k270": (0.1, 0.5, None),
    "k232": (1.5, 3.5, None),
}

LABEL_SEUIL = {
    "acidite_huile_pourcent": "AciditÃ© libre (%)",
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


def _normalize_lot_reference(text: str | None) -> str | None:
    if not text:
        return None
    t = str(text).strip().upper()
    if re.fullmatch(r"LO\d+", t):
        return f"LO{int(t[2:]):02d}"
    match = re.fullmatch(r"(?:LOT|L)\s*(\d+)", t)
    if match:
        return f"LO{int(match.group(1)):02d}"
    if re.fullmatch(r"\d+", t):
        return f"LO{int(t):02d}"
    return t


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

    if acid < 0.1 or acid > 5.0:
        grade = "hors norme" if acid < 0.1 else "hors intervalle"
        issues.append(
            f"ðŸ”´ **AciditÃ© hors intervalle standard** ({_fmt(acid)} % ; intervalle 0,1 Ã  5 %) â†’ "
            f"huile classÃ©e **{grade}**. Cause probable : olives trop mÃ»res, blessÃ©es, "
            f"stockÃ©es trop longtemps avant trituration ou tempÃ©ratures de rÃ©colte/stockage Ã©levÃ©es."
        )
    elif acid > 0.8:
        issues.append(
            f"ðŸŸ¡ **AciditÃ© surveiller** ({_fmt(acid)} %) â€” encore dans l'intervalle standard, "
            f"mais proche de la limite haute (5 %)."
        )

    if perox < 5.0 or perox > 40.0:
        issues.append(
            f"ðŸ”´ **Indice de peroxyde hors intervalle standard** ({_fmt(perox, 1)} meq Oâ‚‚/kg ; intervalle 5 Ã  40) â†’ "
            f"oxydation primaire de l'huile. Cause probable : contact prolongÃ© avec l'air, "
            f"tempÃ©ratures Ã©levÃ©es lors du malaxage ou stockage inappropriÃ©."
        )

    if k270 < 0.1 or k270 > 0.5:
        issues.append(
            f"ðŸ”´ **K270 hors intervalle standard** ({_fmt(k270, 3)} ; intervalle 0,1 Ã  0,5) â†’ "
            f"prÃ©sence de produits d'oxydation secondaire. Cause probable : huile ancienne, "
            f"chauffage excessif ou raffinage partiel."
        )

    if k232 < 1.5 or k232 > 3.5:
        issues.append(
            f"ðŸŸ¡ **K232 hors intervalle standard** ({_fmt(k232, 2)} ; intervalle 1,5 Ã  3,5) â†’ diÃ¨nes conjuguÃ©s â€” signe d'oxydation en cours."
        )

    if polyphenols and (polyphenols < 100 or polyphenols > 800):
        issues.append(
            f"ðŸŸ¡ **PolyphÃ©nols hors intervalle standard** ({_fmt(polyphenols, 0)} mg/kg ; intervalle 100 Ã  800) â†’ olives sur-mÃ»res ou extraction dans de mauvaises conditions."
        )

    return issues


def _analyse_olive_issues(lot: dict) -> list[str]:
    issues = []

    acidite_olive = _safe_float(lot.get("acidite_olives_pourcent"))
    if acidite_olive > ACIDITE_OLIVE_SEUIL_CRITIQUE:
        issues.append(
            f"ðŸ”´ **AciditÃ© des olives Ã  la rÃ©ception Ã©levÃ©e** ({_fmt(acidite_olive)} %) â€” "
            f"au-delÃ  de {ACIDITE_OLIVE_SEUIL_CRITIQUE} %, la qualitÃ© de l'huile est presque inÃ©vitablement compromise."
        )

    maturite = lot.get("indice_maturite")
    if maturite is not None:
        m = _safe_float(maturite)
        if m > MATURITE_IDEALE_MAX:
            issues.append(
                f"ðŸŸ¡ **Sur-maturitÃ© des olives** (indice {_fmt(m, 1)} > idÃ©al â‰¤ {MATURITE_IDEALE_MAX}) â€” "
                f"les olives trop mÃ»res ont une aciditÃ© plus Ã©levÃ©e et moins de polyphÃ©nols."
            )

    duree = _safe_float(lot.get("duree_stockage_jours"))
    if duree > 2:
        issues.append(
            f"ðŸŸ¡ **DÃ©lai avant trituration long** ({int(duree)} jour(s)) â€” les olives doivent idÃ©alement Ãªtre triturÃ©es dans les 24â€“48h."
        )

    temp = lot.get("temperature_stockage")
    if temp is not None and _safe_float(temp) > 20:
        issues.append(
            f"ðŸŸ¡ **TempÃ©rature de stockage Ã©levÃ©e** ({_fmt(temp, 1)} Â°C > 20 Â°C) â€” accÃ©lÃ¨re la dÃ©gradation enzymatique."
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
                    f"ðŸŸ¡ **Rendement faible** ({_fmt(rend, 1)} % < {RENDEMENT_MIN_NORMAL} %) lors de l'exÃ©cution {ep.get('reference', '')} â€” "
                    f"peut indiquer des olives sÃ¨ches ou un problÃ¨me de centrifugation."
                )
            elif rend > RENDEMENT_MAX_NORMAL:
                issues.append(f"ðŸŸ¢ Rendement Ã©levÃ© ({_fmt(rend, 1)} %) lors de {ep.get('reference', '')}.")

        if temp_malax is not None and _safe_float(temp_malax) > 27:
            issues.append(
                f"ðŸ”´ **Malaxage chaud** ({_fmt(temp_malax, 1)} Â°C > 27 Â°C) pour {ep.get('reference', '')} â€” "
                f"augmente le rendement mais dÃ©grade les polyphÃ©nols et accÃ©lÃ¨re l'oxydation."
            )

        if duree_malax is not None and _safe_float(duree_malax) > 45:
            issues.append(
                f"ðŸŸ¡ **Malaxage prolongÃ©** ({int(_safe_float(duree_malax))} min > 45 min) â€” expose davantage l'huile Ã  l'oxygÃ¨ne."
            )

        if eau in (1, True, "1", "oui", "yes", "true"):
            issues.append(
                f"ðŸŸ¡ **Ajout d'eau lors du malaxage** ({ep.get('reference', '')}) â€” dilue les polyphÃ©nols et peut augmenter l'indice de peroxyde."
            )

    return issues


def _build_explanation(
    lot: dict,
    exec_rows: list[dict],
    labo_rows: list[dict],
    asks_good_yield: bool = False,
) -> str:
    lot_ref = lot.get("reference", "?")
    variete = lot.get("variete") or "variÃ©tÃ© inconnue"
    fournisseur = lot.get("fournisseur_nom") or "fournisseur inconnu"
    huilerie = lot.get("huilerie_nom") or "huilerie inconnue"
    date_rec = lot.get("date_reception") or "date inconnue"

    qualite_finale = "non dÃ©terminÃ©e"
    if labo_rows:
        r = labo_rows[0]
        acid = _safe_float(r.get("acidite_huile_pourcent"))
        perox = _safe_float(r.get("indice_peroxyde_meq_o2_kg"))
        k270 = _safe_float(r.get("k270"))
        k232 = _safe_float(r.get("k232"))
        polyphenols = _safe_float(r.get("polyphenols_mg_kg"))
        if 0.1 <= acid <= 5 and 5 <= perox <= 40 and 0.1 <= k270 <= 0.5 and 1.5 <= k232 <= 3.5 and 100 <= polyphenols <= 800:
            qualite_finale = "âœ… **Vierge Extra** (tous les paramÃ¨tres conformes)"
        elif 0.1 <= acid <= 5 and 5 <= perox <= 40:
            qualite_finale = "âš ï¸ **Conforme aux intervalles standards**"
        else:
            qualite_finale = "âŒ **Hors intervalle standard**"

    olive_issues = _analyse_olive_issues(lot)
    prod_issues = _analyse_production_issues(exec_rows)
    labo_issues = _analyse_labo_issues(labo_rows)

    all_issues = olive_issues + prod_issues + labo_issues
    nb_issues = len([i for i in all_issues if i.startswith("ðŸ”´")])

    lines = [
        f"## Analyse du lot **{lot_ref}**",
        f"",
        f"**VariÃ©tÃ©** : {variete} | **Fournisseur** : {fournisseur} | **Huilerie** : {huilerie} | **RÃ©ception** : {date_rec}",
        f"**QuantitÃ© initiale** : {_fmt(_safe_float(lot.get('quantite_initiale')), 0)} kg",
        f"",
        f"### ðŸ§ª QualitÃ© finale : {qualite_finale}",
        f"",
    ]

    if not all_issues:
        lines.append(
            "âœ… Aucun facteur anormal dÃ©tectÃ© â€” toutes les conditions de rÃ©ception, de trituration et d'analyse sont dans les normes."
        )
        return "\n".join(lines)

    if olive_issues:
        lines.append("### ðŸ«’ Facteurs liÃ©s aux olives Ã  la rÃ©ception")
        lines.extend(olive_issues)
        lines.append("")

    if prod_issues:
        lines.append("### âš™ï¸ Facteurs liÃ©s aux conditions de trituration")
        lines.extend(prod_issues)
        lines.append("")

    if labo_issues:
        lines.append("### ðŸ“Š RÃ©sultats laboratoire")
        if labo_rows:
            r = labo_rows[0]
            lines.append(
                f"*(Analyse du {r.get('date_analyse', '?')} â€” aciditÃ© {_fmt(r.get('acidite_huile_pourcent'))} %, peroxyde {_fmt(r.get('indice_peroxyde_meq_o2_kg'), 1)}, K270 {_fmt(r.get('k270'), 3)})*"
            )
        lines.extend(labo_issues)
        lines.append("")

    if nb_issues > 0:
        lines.append(
            f"### ðŸ”Ž Conclusion\n{nb_issues} facteur(s) critique(s) identifiÃ©(s). La qualitÃ© de ce lot a Ã©tÃ© principalement affectÃ©e par : "
            + ", ".join(i.split("**")[1] for i in all_issues if i.startswith("ðŸ”´") and "**" in i)
            + "."
        )
    else:
        rendements = [
            _safe_float(ep.get("rendement"))
            for ep in exec_rows
            if _safe_float(ep.get("rendement")) > 0
        ]
        has_low_yield = any(r < RENDEMENT_MIN_NORMAL for r in rendements)
        normal_yields = [
            r
            for r in rendements
            if RENDEMENT_MIN_NORMAL <= r <= RENDEMENT_MAX_NORMAL
        ]

        if asks_good_yield and normal_yields and not has_low_yield:
            avg_yield = sum(normal_yields) / len(normal_yields)
            lines.append(
                f"### ðŸ”Ž Conclusion\nLe rendement est globalement bon pour ce lot (moyenne observÃ©e : {_fmt(avg_yield, 1)} %), et aucun facteur critique n'a Ã©tÃ© dÃ©tectÃ©."
            )
        else:
            lines.append(
                "### ðŸ”Ž Conclusion\nAucun facteur critique, mais des points d'amÃ©lioration ont Ã©tÃ© dÃ©tectÃ©s (signalÃ©s en ðŸŸ¡)."
            )

    return "\n".join(lines)


class ExplicationHandler(IntentHandler):
    """Handler pour expliquer la qualitÃ© / le comportement d'un lot spÃ©cifique."""

    def __init__(self, service: ChatbotService):
        self.service = service

    async def handle(self, query: ChatQuery) -> IntentResult:
        message_lower = (query.message or "").lower()
        asks_good_yield = (
            "rendement" in message_lower
            and any(token in message_lower for token in ["bon", "bonne", "correct", "eleve", "Ã©levÃ©"])
        )

        lot_ref = (
            query.extra_context.get("lot_reference")
            or query.extra_context.get("reference_lot")
            or query.extra_context.get("code_lot")
            or getattr(query, "lot_reference", None)
            or getattr(query, "reference_lot", None)
            or getattr(query, "code_lot", None)
        )

        if not lot_ref and query.extra_context.get("entities"):
            entities = query.extra_context["entities"]
            lot_ref = entities.get("lot_reference") or entities.get("reference_lot") or entities.get("code_lot")

        if not lot_ref:
            return IntentResult(
                text=(
                    "PrÃ©cisez la rÃ©fÃ©rence du lot pour que je puisse l'analyser. "
                    "Exemple : *\"pourquoi la qualitÃ© du lot LO17 Ã©tait mauvaise ?\"*"
                ),
                data=None,
                structured_payload=None,
            )

        normalized_ref = _normalize_lot_reference(lot_ref)
        if not normalized_ref:
            return IntentResult(
                text=f"RÃ©fÃ©rence de lot invalide : **{lot_ref}**.",
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
            ]
            # handle fournisseur: legacy column fournisseur_nom or new relation fournisseur_id -> fournisseur.nom
            joins = ""
            if "fournisseur_nom" in cols:
                base_fields.append("lo.fournisseur_nom")
            else:
                base_fields.append("f.nom AS fournisseur_nom")
                joins += " LEFT JOIN fournisseur f ON f.id_fournisseur = lo.fournisseur_id"

            base_fields += [
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
            q_lot = "SELECT " + ", ".join(select_fields) + " FROM lot_olives lo JOIN huilerie h ON h.id_huilerie = lo.huilerie_id" + joins

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
                    text=f"Aucun lot trouvÃ© pour la rÃ©fÃ©rence **{normalized_ref}**.",
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
            for ef in ["temperature_malaxage", "duree_malaxage_minutes", "presence_ajout_eau", "machine_id"]:
                if ef in exec_cols:
                    exec_optional.append(f"ep.{ef}")

            # If execution_production still has machine_id use direct join, otherwise
            # try to aggregate machine names from etape_production -> machine via guide_production
            exec_rows = []
            try:
                if "machine_id" in exec_cols:
                    select_exec_fields = exec_base + exec_optional + ["m.nom_machine"]
                    q_exec = "SELECT " + ", ".join(select_exec_fields) + " FROM execution_production ep LEFT JOIN machine m ON m.id_machine = ep.machine_id WHERE ep.lot_olives_id = %s ORDER BY ep.date_debut ASC"
                    cursor.execute(q_exec, (lot_id,))
                    exec_rows = cursor.fetchall() or []
                else:
                    # check etape_production exists and has machine_id
                    try:
                        cursor.execute("DESCRIBE etape_production")
                        et_cols = [c["Field"] for c in (cursor.fetchall() or [])]
                    except Exception:
                        et_cols = []

                    if "machine_id" in et_cols:
                        # aggregate machine names used by the guide associated to each execution
                        select_exec_fields = exec_base + exec_optional + ["GROUP_CONCAT(DISTINCT m.nom_machine SEPARATOR ', ') AS nom_machine", "ep.id_execution_production"]
                        group_by_fields = exec_base + exec_optional + ["ep.id_execution_production"]
                        q_exec = (
                            "SELECT " + ", ".join(select_exec_fields)
                            + " FROM execution_production ep"
                            + " LEFT JOIN guide_production gp ON gp.id_guide_production = ep.guide_production_id"
                            + " LEFT JOIN etape_production et ON et.guide_production_id = gp.id_guide_production"
                            + " LEFT JOIN machine m ON m.id_machine = et.machine_id"
                            + " WHERE ep.lot_olives_id = %s"
                            + " GROUP BY " + ", ".join(group_by_fields)
                            + " ORDER BY ep.date_debut ASC"
                        )
                        cursor.execute(q_exec, (lot_id,))
                        exec_rows = cursor.fetchall() or []
                    else:
                        # fallback to minimal execution query if no machine info available
                        cursor.execute(
                            "SELECT reference, date_debut, date_fin_reelle, statut, rendement FROM execution_production WHERE lot_olives_id = %s ORDER BY date_debut ASC",
                            (lot_id,),
                        )
                        exec_rows = cursor.fetchall() or []
            except Exception:
                # final fallback
                cursor.execute(
                    "SELECT reference, date_debut, date_fin_reelle, statut, rendement FROM execution_production WHERE lot_olives_id = %s ORDER BY date_debut ASC",
                    (lot_id,),
                )
                exec_rows = cursor.fetchall() or []

            cursor.execute(SQL_LABO, (lot_id,))
            labo_rows = cursor.fetchall() or []

        except Exception as exc:
            logger.exception("Error fetching lot explanation data for %s: %s", normalized_ref, exc)
            return IntentResult(
                text="Impossible de rÃ©cupÃ©rer les donnÃ©es du lot. VÃ©rifiez la connexion Ã  la base.",
                data=None,
                structured_payload=None,
            )
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

        explanation = _build_explanation(
            lot_row,
            exec_rows,
            labo_rows,
            asks_good_yield=asks_good_yield,
        )

        chart_data = None
        if labo_rows:
            r = labo_rows[0]
            chart_data = {
                "labels": ["AciditÃ© (%)", "Peroxyde (meq O2/kg)", "K270", "K232"],
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

