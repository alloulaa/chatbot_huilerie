"""
Handler pour l'intent EXPLICATION.

Version intelligente : collecte TOUTES les données disponibles sur le lot
(réception, conditions des olives, étapes de production, machines, analyses labo,
mouvements stock, données agronomiques) et appelle Claude (Anthropic API) pour
générer une explication causale riche et contextuelle.

Fallback : analyse rule-based enrichie si l'API est indisponible.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx

from app.database import get_db_connection
from app.domain.chat import ChatQuery, IntentResult
from app.services.intent.base import IntentHandler
from app.services.query_service import ChatbotService

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constantes agronomiques & seuils normatifs (COI/IOC)
# ─────────────────────────────────────────────────────────────────────────────
SEUILS_VIERGE_EXTRA = {
    "acidite_huile_pourcent":        {"min": 0.0,  "max": 0.8,  "label": "Acidité libre (%)"},
    "indice_peroxyde_meq_o2_kg":    {"min": 0.0,  "max": 20.0, "label": "Indice de peroxyde (meq O₂/kg)"},
    "k270":                          {"min": 0.0,  "max": 0.22, "label": "K270"},
    "k232":                          {"min": 1.5,  "max": 2.50, "label": "K232"},
    "polyphenols_mg_kg":             {"min": 100.0,"max": 800.0,"label": "Polyphénols (mg/kg)"},
}

SEUILS_VIERGE = {
    "acidite_huile_pourcent":        {"min": 0.0,  "max": 2.0},
    "indice_peroxyde_meq_o2_kg":    {"min": 0.0,  "max": 20.0},
    "k270":                          {"min": 0.0,  "max": 0.25},
}

# Connaissance agronomique : variétés tunisiennes et leur profil
VARIETES_PROFIL = {
    "chemlali":  {"acidite_naturelle": "faible", "polyphenols": "élevés", "sensibilite_gel": "haute",   "maturite_optimale": "tard"},
    "chétoui":   {"acidite_naturelle": "faible", "polyphenols": "très élevés", "sensibilite_gel": "moyenne", "maturite_optimale": "tôt"},
    "oueslati":  {"acidite_naturelle": "moyenne","polyphenols": "moyens",  "sensibilite_gel": "basse",  "maturite_optimale": "milieu"},
    "sayali":    {"acidite_naturelle": "faible", "polyphenols": "moyens",  "sensibilite_gel": "haute",  "maturite_optimale": "tard"},
    "gerboui":   {"acidite_naturelle": "moyenne","polyphenols": "faibles", "sensibilite_gel": "basse",  "maturite_optimale": "tôt"},
    "arbequina": {"acidite_naturelle": "faible", "polyphenols": "faibles", "sensibilite_gel": "moyenne","maturite_optimale": "tôt"},
    "koroneiki": {"acidite_naturelle": "faible", "polyphenols": "très élevés","sensibilite_gel": "haute","maturite_optimale": "tôt"},
}

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

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


def _grade_huile(acid: float, perox: float, k270: float) -> str:
    if acid <= 0.8 and perox <= 20 and k270 <= 0.22:
        return "Vierge Extra"
    if acid <= 2.0 and perox <= 20 and k270 <= 0.25:
        return "Vierge"
    if acid <= 3.3:
        return "Vierge Courante"
    return "Lampante (non comestible brut)"


def _get_variete_profil(variete: str | None) -> dict:
    if not variete:
        return {}
    v = variete.strip().lower()
    for key, profil in VARIETES_PROFIL.items():
        if key in v or v in key:
            return profil
    return {}


def _date_sort_key(value: Any) -> tuple[int, str]:
    text = str(value or "").strip()
    if not text:
        return (1, "")
    return (0, text[:19])


def _latest_by(items: list[dict], key: str) -> dict | None:
    if not items:
        return None
    ordered = sorted(items, key=lambda item: _date_sort_key(item.get(key)))
    return ordered[-1] if ordered else None


def _first_by(items: list[dict], key: str) -> dict | None:
    if not items:
        return None
    ordered = sorted(items, key=lambda item: _date_sort_key(item.get(key)))
    return ordered[0] if ordered else None


def _parse_boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "oui", "on"}


# ─────────────────────────────────────────────────────────────────────────────
# Collecte complète des données du lot
# ─────────────────────────────────────────────────────────────────────────────

def _collect_all_lot_data(normalized_ref: str, enterprise_id: int | None) -> dict[str, Any]:
    """
    Collecte TOUTES les données disponibles sur un lot :
    - Informations lot (variété, fournisseur, dates, acidité olives, maturité, région, sol…)
    - Étapes de production (machines, températures, durées, rendements, ajout eau…)
    - Analyses laboratoire (acidité, peroxyde, K270, K232, polyphénols…)
    - Mouvements de stock
    - Données huilerie (région, équipements)
    - Comparaison avec les autres lots de l'huilerie (benchmark)
    """
    connection = cursor = None
    data: dict[str, Any] = {
        "lot": None,
        "lot_columns": [],
        "executions": [],
        "exec_columns": [],
        "execution_steps": [],
        "production_outputs": [],
        "analyses": [],
        "stock_movements": [],
        "huilerie_info": None,
        "fournisseur_info": None,
        "benchmark": None,
        "error": None,
    }

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # ── 1. Colonnes disponibles dans lot_olives ────────────────────────
        cursor.execute("DESCRIBE lot_olives")
        lot_cols = {c["Field"] for c in (cursor.fetchall() or [])}
        data["lot_columns"] = list(lot_cols)

        # Construire SELECT dynamique pour lot_olives (toutes colonnes utiles)
        base_lot_fields = ["lo.id_lot", "lo.reference", "lo.variete"]
        optional_lot_fields = [
            "fournisseur_nom", "fournisseur_id",
            "quantite_initiale", "quantite_restante",
            "date_reception", "date_recolte",
            "acidite_olives_pourcent", "indice_maturite",
            "maturite",
            "temperature_stockage", "duree_stockage_jours",
            "duree_stockage_avant_broyage", "temps_depuis_recolte_heures",
            "region", "zone", "localite", "commune", "gouvernorat",
            "type_sol", "sol", "altitude", "superficie",
            "methode_recolte", "mode_recolte",
            "campagne_id", "statut", "notes", "observations",
            "humidite_olives", "humidite_pourcent",
            "taux_impuretes", "taux_feuilles_pourcent",
            "lavage_effectue", "origine", "pesee", "bon_pesee_pdf_path",
        ]
        selected_lot = list(base_lot_fields)
        for f in optional_lot_fields:
            if f in lot_cols:
                selected_lot.append(f"lo.{f}")

        # Join fournisseur si nécessaire (probe columns to avoid unknown-column errors)
        fournisseur_join = ""
        f_cols: set[str] = set()
        if "fournisseur_id" in lot_cols:
            # If we will join fournisseur, inspect its columns first (some schemas are minimal)
            try:
                cursor.execute("DESCRIBE fournisseur")
                f_cols = {c["Field"] for c in (cursor.fetchall() or [])}
            except Exception:
                f_cols = set()

        if "fournisseur_nom" not in lot_cols and "fournisseur_id" in lot_cols:
            selected_lot.append("COALESCE(f.nom, 'Inconnu') AS fournisseur_nom")
            if "region" in f_cols:
                selected_lot.append("f.region AS fournisseur_region")
            if "telephone" in f_cols:
                selected_lot.append("f.telephone AS fournisseur_tel")
            fournisseur_join = " LEFT JOIN fournisseur f ON f.id_fournisseur = lo.fournisseur_id"
        elif "fournisseur_nom" in lot_cols and "fournisseur_id" in lot_cols:
            if "region" in f_cols:
                selected_lot.append("f.region AS fournisseur_region")
            fournisseur_join = " LEFT JOIN fournisseur f ON f.id_fournisseur = lo.fournisseur_id"

        selected_lot += ["h.nom AS huilerie_nom", "h.id_huilerie", "h.entreprise_id"]

        q_lot = (
            "SELECT " + ", ".join(selected_lot)
            + " FROM lot_olives lo"
            + " JOIN huilerie h ON h.id_huilerie = lo.huilerie_id"
            + fournisseur_join
            + " WHERE (LOWER(lo.reference) = LOWER(%s) OR CAST(lo.id_lot AS CHAR) = %s)"
        )
        params: list[Any] = [normalized_ref, normalized_ref]
        if enterprise_id is not None:
            q_lot += " AND h.entreprise_id = %s"
            params.append(enterprise_id)
        q_lot += " LIMIT 1"

        cursor.execute(q_lot, params)
        lot_row = cursor.fetchone()
        if not lot_row:
            data["error"] = f"Aucun lot trouvé pour {normalized_ref}."
            return data

        data["lot"] = dict(lot_row)
        lot_id = lot_row["id_lot"]
        huilerie_id = lot_row.get("id_huilerie")

        # ── 2. Données huilerie enrichies ──────────────────────────────────
        try:
            cursor.execute("DESCRIBE huilerie")
            h_cols = {c["Field"] for c in (cursor.fetchall() or [])}
            h_optional = ["region", "zone", "gouvernorat", "localite", "capacite_traitement",
                          "type_presse", "systeme_extraction", "nb_centrifugeuses", "notes"]
            h_selected = ["h.id_huilerie", "h.nom"]
            for f in h_optional:
                if f in h_cols:
                    h_selected.append(f"h.{f}")
            cursor.execute(
                "SELECT " + ", ".join(h_selected) + " FROM huilerie h WHERE h.id_huilerie = %s",
                (huilerie_id,)
            )
            data["huilerie_info"] = cursor.fetchone() or {}
        except Exception as e:
            logger.debug("Could not fetch enriched huilerie info: %s", e)
            data["huilerie_info"] = {}

        # ── 3. Colonnes disponibles dans execution_production ──────────────
        cursor.execute("DESCRIBE execution_production")
        exec_cols = {c["Field"] for c in (cursor.fetchall() or [])}
        data["exec_columns"] = list(exec_cols)

        # Détails de l'exécution et du guide de production pour comprendre les conditions réelles
        try:
            cursor.execute(
                "SELECT "
                "ep.id_execution_production AS execution_id, "
                "ep.reference AS execution_reference, "
                "ep.date_debut, ep.date_fin_reelle, ep.statut, ep.rendement, "
                "ep.controle_temperature, ep.observations, "
                "gp.reference AS guide_reference, gp.nom AS guide_nom, gp.description AS guide_description, "
                "et.ordre AS etape_ordre, et.code_etape, et.nom AS etape_nom, et.description AS etape_description, "
                "m.nom_machine, m.categorie_machine, m.type_machine, m.etat_machine "
                "FROM execution_production ep "
                "LEFT JOIN guide_production gp ON gp.id_guide_production = ep.guide_production_id "
                "LEFT JOIN etape_production et ON et.guide_production_id = gp.id_guide_production "
                "LEFT JOIN machine m ON m.id_machine = et.machine_id "
                "WHERE ep.lot_olives_id = %s "
                "ORDER BY ep.date_debut ASC, ep.id_execution_production ASC, et.ordre ASC",
                (lot_id,)
            )
            data["execution_steps"] = [dict(r) for r in (cursor.fetchall() or [])]
        except Exception as exc:
            logger.debug("Could not fetch execution steps: %s", exc)

        try:
            cursor.execute(
                "SELECT pf.id_produit, pf.reference, pf.date_production, pf.nom_produit, pf.qualite, pf.quantite_produite, pf.execution_production_id "
                "FROM produit_final pf "
                "JOIN execution_production ep ON ep.id_execution_production = pf.execution_production_id "
                "WHERE ep.lot_olives_id = %s "
                "ORDER BY pf.date_production ASC, pf.id_produit ASC",
                (lot_id,)
            )
            data["production_outputs"] = [dict(r) for r in (cursor.fetchall() or [])]
        except Exception as exc:
            logger.debug("Could not fetch final production outputs: %s", exc)

        exec_base = ["ep.id_execution_production", "ep.reference", "ep.date_debut",
                     "ep.date_fin_reelle", "ep.statut", "ep.rendement"]
        exec_optional = [
            "temperature_malaxage", "duree_malaxage_minutes",
            "presence_ajout_eau", "quantite_eau_ajoutee",
            "vitesse_malaxage", "pression_centrifugation",
            "temperature_centrifugation", "duree_centrifugation",
            "temperature_stockage_huile", "perte_extraction",
            "guide_production_id", "machine_id", "operateur_id",
            "notes", "observations", "commentaires",
        ]
        exec_selected = list(exec_base)
        for f in exec_optional:
            if f in exec_cols:
                exec_selected.append(f"ep.{f}")

        # Machines liées
        if "machine_id" in exec_cols:
            exec_selected += [
                "m.nom_machine", "m.categorie_machine", "m.type_machine",
                "m.etat_machine", "m.capacite AS machine_capacite", "m.marque AS machine_marque",
                "m.annee_fabrication AS machine_annee"
            ]
            q_exec = (
                "SELECT " + ", ".join(exec_selected)
                + " FROM execution_production ep"
                + " LEFT JOIN machine m ON m.id_machine = ep.machine_id"
                + " WHERE ep.lot_olives_id = %s ORDER BY ep.date_debut ASC"
            )
            cursor.execute(q_exec, (lot_id,))
        else:
            # Via guide_production → etape_production → machine
            try:
                cursor.execute("DESCRIBE etape_production")
                et_cols = {c["Field"] for c in (cursor.fetchall() or [])}
                if "machine_id" in et_cols:
                    exec_selected += ["GROUP_CONCAT(DISTINCT m.nom_machine SEPARATOR ', ') AS nom_machine",
                                      "GROUP_CONCAT(DISTINCT m.categorie_machine SEPARATOR ', ') AS categorie_machine",
                                      "ep.id_execution_production AS _gid"]
                    q_exec = (
                        "SELECT " + ", ".join(exec_selected)
                        + " FROM execution_production ep"
                        + " LEFT JOIN guide_production gp ON gp.id_guide_production = ep.guide_production_id"
                        + " LEFT JOIN etape_production et ON et.guide_production_id = gp.id_guide_production"
                        + " LEFT JOIN machine m ON m.id_machine = et.machine_id"
                        + " WHERE ep.lot_olives_id = %s"
                        + " GROUP BY ep.id_execution_production ORDER BY ep.date_debut ASC"
                    )
                    cursor.execute(q_exec, (lot_id,))
                else:
                    raise ValueError("no machine_id in etape")
            except Exception:
                cursor.execute(
                    "SELECT " + ", ".join(exec_base) + " FROM execution_production ep"
                    + " WHERE ep.lot_olives_id = %s ORDER BY ep.date_debut ASC",
                    (lot_id,)
                )

        data["executions"] = [dict(r) for r in (cursor.fetchall() or [])]

        # ── 4. Analyses laboratoire (toutes colonnes disponibles) ──────────
        try:
            cursor.execute("DESCRIBE analyse_laboratoire")
            al_cols = {c["Field"] for c in (cursor.fetchall() or [])}
            al_base = ["al.id_analyse", "al.reference", "al.date_analyse",
                       "al.acidite_huile_pourcent", "al.indice_peroxyde_meq_o2_kg",
                       "al.k270", "al.k232", "al.polyphenols_mg_kg"]
            al_optional = [
                "delta_k", "triglycérides", "triglycerides",
                "humidite_huile", "impuretes_huile",
                "couleur", "odeur", "gout", "saveur", "fruité", "fruite",
                "amertume", "ardence", "defauts",
                "panel_test_score", "classification_panel",
                "tocopherols", "cires",
                "analyse_par", "laboratoire", "methode_analyse",
                "notes", "observations",
            ]
            al_selected = list(al_base)
            for f in al_optional:
                if f in al_cols:
                    al_selected.append(f"al.{f}")
            cursor.execute(
                "SELECT " + ", ".join(al_selected)
                + " FROM analyse_laboratoire al WHERE al.lot_id = %s ORDER BY al.date_analyse DESC",
                (lot_id,)
            )
            data["analyses"] = [dict(r) for r in (cursor.fetchall() or [])]
        except Exception as e:
            logger.debug("Could not fetch full lab analyses: %s", e)
            data["analyses"] = []

        # ── 5. Mouvements de stock liés au lot ─────────────────────────────
        try:
            for tbl in ("stock_movement", "mouvement_stock"):
                try:
                    cursor.execute(
                        f"SELECT * FROM {tbl} WHERE lot_id = %s ORDER BY date_mouvement ASC LIMIT 20",
                        (lot_id,)
                    )
                    data["stock_movements"] = [dict(r) for r in (cursor.fetchall() or [])]
                    break
                except Exception:
                    continue
        except Exception as e:
            logger.debug("Could not fetch stock movements: %s", e)

        # ── 6. Benchmark : moyennes des autres lots de la même huilerie ────
        try:
            cursor.execute("""
                SELECT
                    AVG(al.acidite_huile_pourcent)     AS avg_acidite,
                    AVG(al.indice_peroxyde_meq_o2_kg)  AS avg_peroxyde,
                    AVG(al.k270)                        AS avg_k270,
                    AVG(al.polyphenols_mg_kg)           AS avg_polyphenols,
                    COUNT(DISTINCT lo.id_lot)           AS nb_lots_total
                FROM analyse_laboratoire al
                JOIN lot_olives lo ON lo.id_lot = al.lot_id
                JOIN huilerie h ON h.id_huilerie = lo.huilerie_id
                WHERE h.id_huilerie = %s AND lo.id_lot != %s
            """, (huilerie_id, lot_id))
            bm = cursor.fetchone()
            if bm:
                data["benchmark"] = {
                    "avg_acidite":     _safe_float(bm.get("avg_acidite")),
                    "avg_peroxyde":    _safe_float(bm.get("avg_peroxyde")),
                    "avg_k270":        _safe_float(bm.get("avg_k270")),
                    "avg_polyphenols": _safe_float(bm.get("avg_polyphenols")),
                    "nb_lots_total":   int(bm.get("nb_lots_total") or 0),
                }
        except Exception as e:
            logger.debug("Could not fetch benchmark: %s", e)

        # ── 7. Rendement moyen de l'huilerie (benchmark production) ────────
        try:
            cursor.execute("""
                SELECT AVG(ep.rendement) AS avg_rend
                FROM execution_production ep
                JOIN lot_olives lo ON lo.id_lot = ep.lot_olives_id
                WHERE lo.huilerie_id = %s AND lo.id_lot != %s AND ep.rendement IS NOT NULL
            """, (huilerie_id, lot_id))
            row = cursor.fetchone()
            if row and data["benchmark"]:
                data["benchmark"]["avg_rendement"] = _safe_float(row.get("avg_rend"))
        except Exception as e:
            logger.debug("Could not fetch rendement benchmark: %s", e)

    except Exception as exc:
        logger.exception("Error collecting lot data for %s: %s", normalized_ref, exc)
        data["error"] = f"Erreur lors de la collecte des données : {exc}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return data


# ─────────────────────────────────────────────────────────────────────────────
# Construction du prompt expert pour Claude
# ─────────────────────────────────────────────────────────────────────────────

def _build_expert_prompt(lot_data: dict, user_question: str) -> str:
    lot = lot_data.get("lot") or {}
    execs = lot_data.get("executions") or []
    execution_steps = lot_data.get("execution_steps") or []
    production_outputs = lot_data.get("production_outputs") or []
    analyses = lot_data.get("analyses") or []
    movements = lot_data.get("stock_movements") or []
    benchmark = lot_data.get("benchmark") or {}
    huilerie_info = lot_data.get("huilerie_info") or {}

    variete = lot.get("variete") or "inconnue"
    variete_profil = _get_variete_profil(variete)

    # Calcul du grade COI
    grade = "Non déterminé"
    if analyses:
        a = analyses[0]
        grade = _grade_huile(
            _safe_float(a.get("acidite_huile_pourcent")),
            _safe_float(a.get("indice_peroxyde_meq_o2_kg")),
            _safe_float(a.get("k270"))
        )

    # Durée de stockage estimée (gère plusieurs schémas de colonnes)
    duree_stockage = _safe_float(lot.get("duree_stockage_jours"))
    if duree_stockage == 0:
        duree_stockage = _safe_float(lot.get("duree_stockage_avant_broyage"))
    if duree_stockage == 0:
        heures_depuis_recolte = _safe_float(lot.get("temps_depuis_recolte_heures"))
        if heures_depuis_recolte > 0:
            duree_stockage = heures_depuis_recolte / 24.0
    if duree_stockage == 0 and lot.get("date_reception") and execs:
        try:
            from datetime import datetime
            dr = str(lot["date_reception"])[:10]
            dp = str(execs[0].get("date_debut", ""))[:10]
            if dr and dp:
                d1 = datetime.strptime(dr, "%Y-%m-%d")
                d2 = datetime.strptime(dp, "%Y-%m-%d")
                duree_stockage = abs((d2 - d1).days)
        except Exception:
            pass

    lines = [
        "Tu es un expert en oléiculture et en technologie d'extraction d'huile d'olive.",
        "Tu dois analyser TOUTES les données disponibles sur ce lot et produire une explication",
        "causale complète, intelligente et pédagogique en français.",
        "Ne recopie pas les informations brutes du lot en ouverture : va directement à l'analyse,",
        "avec un langage humain, naturel et concret.",
        "",
        f"## Question de l'utilisateur\n{user_question}",
        "",
        "## Données collectées",
        "",
        "### 1. Informations du lot",
        f"- Référence : {lot.get('reference', '?')}",
        f"- Variété d'olive : {variete}",
        f"- Fournisseur : {lot.get('fournisseur_nom', 'inconnu')}",
        f"- Huilerie : {lot.get('huilerie_nom', 'inconnue')}",
        f"- Région fournisseur : {lot.get('fournisseur_region') or lot.get('region') or 'non renseignée'}",
        f"- Région du lot/verger : {lot.get('region') or lot.get('zone') or lot.get('localite') or lot.get('gouvernorat') or 'non renseignée'}",
        f"- Type de sol : {lot.get('type_sol') or lot.get('sol') or 'non renseigné'}",
        f"- Altitude : {lot.get('altitude') or 'non renseignée'}",
        f"- Méthode de récolte : {lot.get('methode_recolte') or lot.get('mode_recolte') or 'non renseignée'}",
        f"- Date de récolte : {lot.get('date_recolte') or 'non renseignée'}",
        f"- Date de réception à l'huilerie : {lot.get('date_reception') or 'non renseignée'}",
        f"- Délai récolte→trituration estimé : {int(round(duree_stockage))} jour(s)" if duree_stockage else "- Délai récolte→trituration : non calculable",
        f"- Quantité initiale : {_fmt(lot.get('quantite_initiale'), 0)} kg",
        f"- Quantité restante : {_fmt(lot.get('quantite_restante'), 0)} kg",
        f"- Acidité des olives à la réception : {_fmt(lot.get('acidite_olives_pourcent'), 2)} %" if lot.get('acidite_olives_pourcent') else "- Acidité des olives à la réception : non renseignée",
        f"- Indice de maturité : {_fmt(lot.get('indice_maturite') or lot.get('maturite'), 1)}" if (lot.get('indice_maturite') or lot.get('maturite')) else "- Indice de maturité : non renseigné",
        f"- Humidité des olives : {_fmt(lot.get('humidite_olives') or lot.get('humidite_pourcent'), 1)} %" if (lot.get('humidite_olives') or lot.get('humidite_pourcent')) else "",
        f"- Temps depuis récolte : {_fmt(lot.get('temps_depuis_recolte_heures'), 0)} h" if lot.get('temps_depuis_recolte_heures') else "",
        f"- Lavage effectué : {'Oui' if lot.get('lavage_effectue') else 'Non'}" if lot.get('lavage_effectue') is not None else "",
        f"- Taux de feuilles : {_fmt(lot.get('taux_feuilles_pourcent'), 1)} %" if lot.get('taux_feuilles_pourcent') else "",
        f"- Taux d'impuretés : {_fmt(lot.get('taux_impuretes'), 2)} %" if lot.get('taux_impuretes') else "",
        f"- Température de stockage avant trituration : {_fmt(lot.get('temperature_stockage'), 1)} °C" if lot.get('temperature_stockage') else "",
        f"- Observations sur le lot : {lot.get('notes') or lot.get('observations') or 'aucune'}",
    ]

    # Profil variétal
    if variete_profil:
        lines += [
            "",
            f"### 2. Profil agronomique de la variété {variete}",
            f"- Acidité naturelle caractéristique : {variete_profil.get('acidite_naturelle', 'inconnue')}",
            f"- Teneur en polyphénols caractéristique : {variete_profil.get('polyphenols', 'inconnue')}",
            f"- Sensibilité au gel : {variete_profil.get('sensibilite_gel', 'inconnue')}",
            f"- Époque de maturité optimale : {variete_profil.get('maturite_optimale', 'inconnue')}",
        ]

    # Étapes de production
    if execs:
        lines += ["", "### 3. Étapes de production / Conditions de trituration"]
        for i, ep in enumerate(execs, 1):
            lines.append(f"\n**Exécution {i} — {ep.get('reference', '?')}**")
            lines.append(f"- Statut : {ep.get('statut', 'inconnu')}")
            lines.append(f"- Date début : {ep.get('date_debut', '?')}")
            lines.append(f"- Date fin : {ep.get('date_fin_reelle', '?') or 'en cours'}")
            if ep.get("controle_temperature") is not None:
                lines.append(f"- Contrôle température : {'Oui' if ep.get('controle_temperature') else 'Non'}")
            rend = ep.get("rendement")
            if rend is not None:
                lines.append(f"- Rendement obtenu : {_fmt(rend, 2)} %")
            if ep.get("nom_machine"):
                lines.append(f"- Machine(s) utilisée(s) : {ep.get('nom_machine')}")
            if ep.get("categorie_machine"):
                lines.append(f"- Catégorie machine : {ep.get('categorie_machine')}")
            if ep.get("etat_machine"):
                lines.append(f"- État de la machine : {ep.get('etat_machine')}")
            if ep.get("machine_marque"):
                lines.append(f"- Marque machine : {ep.get('machine_marque')} ({ep.get('machine_annee', '?')})")
            if ep.get("temperature_malaxage") is not None:
                lines.append(f"- Température de malaxage : {_fmt(ep.get('temperature_malaxage'), 1)} °C")
            if ep.get("duree_malaxage_minutes") is not None:
                lines.append(f"- Durée de malaxage : {int(_safe_float(ep.get('duree_malaxage_minutes')))} min")
            if ep.get("vitesse_malaxage") is not None:
                lines.append(f"- Vitesse de malaxage : {ep.get('vitesse_malaxage')} tr/min")
            presence_eau = ep.get("presence_ajout_eau")
            if presence_eau is not None:
                ajout_str = "Oui" if presence_eau in (1, True, "1", "oui", "yes", "true") else "Non"
                lines.append(f"- Ajout d'eau : {ajout_str}")
                if ep.get("quantite_eau_ajoutee"):
                    lines.append(f"  → Quantité eau : {ep.get('quantite_eau_ajoutee')} L")
            if ep.get("pression_centrifugation") is not None:
                lines.append(f"- Pression centrifugation : {ep.get('pression_centrifugation')}")
            if ep.get("temperature_centrifugation") is not None:
                lines.append(f"- Température centrifugation : {_fmt(ep.get('temperature_centrifugation'), 1)} °C")
            if ep.get("perte_extraction") is not None:
                lines.append(f"- Perte extraction : {_fmt(ep.get('perte_extraction'), 2)} %")
            if ep.get("notes") or ep.get("observations") or ep.get("commentaires"):
                lines.append(f"- Notes : {ep.get('notes') or ep.get('observations') or ep.get('commentaires')}")
        if execution_steps:
            lines += ["", "- Détail des étapes de l'exécution :"]
            for step in execution_steps:
                step_name = step.get("etape_nom") or step.get("code_etape") or "Étape inconnue"
                lines.append(
                    f"  • {step.get('etape_ordre', '?')}. {step_name}"
                    + (f" — {step.get('etape_description')}" if step.get("etape_description") else "")
                )
                if step.get("nom_machine"):
                    lines.append(f"    → Machine : {step.get('nom_machine')}")
                if step.get("categorie_machine"):
                    lines.append(f"    → Catégorie : {step.get('categorie_machine')}")
                if step.get("etat_machine"):
                    lines.append(f"    → État machine : {step.get('etat_machine')}")
        if production_outputs:
            lines += ["", "- Produit final obtenu :"]
            for pf in production_outputs:
                lines.append(
                    f"  • {pf.get('reference', '?')} : {pf.get('nom_produit') or 'Produit final'}"
                    f" | qualité = {pf.get('qualite') or 'N/D'}"
                    f" | quantité = {_fmt(pf.get('quantite_produite'), 1)} L"
                )
                if pf.get("qualite"):
                    lines.append(
                        f"    → En clair, la qualité finale est {pf.get('qualite')}, donc la chaîne de production a dégradé l'huile malgré un grade labo plus favorable."
                    )
    else:
        lines += ["", "### 3. Étapes de production", "Aucune exécution de production enregistrée."]

    # Analyses laboratoire
    if analyses:
        lines += ["", "### 4. Résultats laboratoire"]
        for i, al in enumerate(analyses, 1):
            lines.append(f"\n**Analyse {i} — {al.get('date_analyse', '?')}**")
            acid = _safe_float(al.get("acidite_huile_pourcent"))
            perox = _safe_float(al.get("indice_peroxyde_meq_o2_kg"))
            k270 = _safe_float(al.get("k270"))
            k232 = _safe_float(al.get("k232"))
            poly = _safe_float(al.get("polyphenols_mg_kg"))

            # Grade calculé
            g = _grade_huile(acid, perox, k270)
            lines.append(f"- **Grade COI calculé : {g}**")
            lines.append("- Interprétation : le grade COI est calculé à partir des paramètres de l'huile analysée (acidité, peroxyde, K270), pas à partir de l'acidité des olives à la réception.")
            lines.append(f"- Acidité libre : {_fmt(acid)} % (seuil vierge extra ≤ 0,8 %)")
            lines.append(f"- Indice de peroxyde : {_fmt(perox, 1)} meq O₂/kg (seuil ≤ 20)")
            lines.append(f"- K270 : {_fmt(k270, 3)} (seuil ≤ 0,22)")
            if k232 > 0:
                lines.append(f"- K232 : {_fmt(k232, 3)} (seuil 1,5-2,50)")
            if poly > 0:
                lines.append(f"- Polyphénols : {_fmt(poly, 0)} mg/kg (référence 100-800, idéal >200)")
            for extra_f in ["delta_k", "humidite_huile", "impuretes_huile", "couleur", "odeur",
                             "gout", "saveur", "amertume", "ardence", "defauts",
                             "panel_test_score", "classification_panel", "tocopherols"]:
                if al.get(extra_f) is not None and al.get(extra_f) != 0:
                    lines.append(f"- {extra_f.replace('_', ' ').capitalize()} : {al.get(extra_f)}")
    else:
        lines += ["", "### 4. Résultats laboratoire", "Aucune analyse enregistrée."]

    # Benchmark
    if benchmark and benchmark.get("nb_lots_total", 0) > 0:
        lines += [
            "", "### 5. Comparaison avec les autres lots de l'huilerie",
            f"(Basé sur {benchmark['nb_lots_total']} autre(s) lot(s))",
            f"- Acidité moyenne de l'huilerie : {_fmt(benchmark.get('avg_acidite', 0))} %",
            f"- Peroxyde moyen : {_fmt(benchmark.get('avg_peroxyde', 0), 1)}",
            f"- K270 moyen : {_fmt(benchmark.get('avg_k270', 0), 3)}",
        ]
        if benchmark.get("avg_polyphenols", 0) > 0:
            lines.append(f"- Polyphénols moyens : {_fmt(benchmark.get('avg_polyphenols', 0), 0)} mg/kg")
        if benchmark.get("avg_rendement", 0) > 0:
            lines.append(f"- Rendement moyen de l'huilerie : {_fmt(benchmark.get('avg_rendement', 0), 1)} %")

    # Huilerie
    if huilerie_info:
        region_h = huilerie_info.get("region") or huilerie_info.get("gouvernorat") or huilerie_info.get("zone")
        if region_h:
            lines += ["", f"### 6. Région de l'huilerie : {region_h}"]
        for f in ["capacite_traitement", "type_presse", "systeme_extraction", "nb_centrifugeuses"]:
            if huilerie_info.get(f):
                lines.append(f"- {f.replace('_', ' ').capitalize()} : {huilerie_info[f]}")

    # Mouvements stock
    if movements:
        lines += ["", "### 7. Mouvements de stock liés au lot"]
        for mv in movements[:5]:
            lines.append(
                f"- {mv.get('type_mouvement', '?')} le {mv.get('date_mouvement', '?')}"
                + (f" — {mv.get('commentaire', '')}" if mv.get("commentaire") else "")
            )

    lines += [
        "",
        "## Instructions pour ta réponse",
        "",
        "Génère une analyse experte, structurée en sections claires avec des titres markdown (##, ###).",
        "Utilise des emojis indicateurs (🔴 critique, 🟡 attention, 🟢 ok, ✅ conforme, ❌ non conforme).",
        "",
        "Tu DOIS obligatoirement :",
        "1. **Identifier et expliquer TOUS les facteurs** qui influencent la qualité, le rendement et la quantité,",
        "   en croisant les données : conditions des olives × paramètres de trituration × résultats labo × comparaison benchmark.",
        "2. **Expliquer les mécanismes biochimiques/physiques** : pourquoi ce paramètre affecte cette caractéristique.",
        "3. **Quantifier l'écart au benchmark** quand les données le permettent.",
        "4. **Contextualiser selon la variété** si le profil variétal est connu.",
        "5. **Donner des recommandations concrètes** pour améliorer la qualité au prochain lot.",
        "6. Terminer par une **conclusion synthétique** avec les 3 leviers d'amélioration prioritaires.",
        "",
        "Si une donnée manque, signale-le brièvement mais ne t'y attarde pas.",
        "Réponds UNIQUEMENT en français, de façon experte mais accessible.",
    ]

    return "\n".join(l for l in lines if l is not None)


def _humanize_explanation_text(text: str) -> str:
    """Remove the metadata-heavy opening so the answer reads like an analysis, not a dump."""
    if not text:
        return text

    blocked_prefixes = (
        "## Analyse experte du lot",
        "**Variété** :",
        "**Région** :",
        "**Quantité** :",
        "**Fournisseur** :",
        "**Huilerie** :",
        "**Réception** :",
        "**Méthode récolte** :",
        "- Référence :",
        "- Variété d'olive :",
        "- Fournisseur :",
        "- Huilerie :",
        "- Région fournisseur :",
        "- Région du lot/verger :",
        "- Type de sol :",
        "- Altitude :",
        "- Méthode de récolte :",
        "- Date de récolte :",
        "- Date de réception à l'huilerie :",
        "- Quantité initiale :",
        "- Quantité restante :",
        "- Acidité des olives à la réception :",
        "- Indice de maturité :",
        "- Humidité des olives :",
        "- Taux d'impuretés :",
        "- Température de stockage avant trituration :",
        "- Observations sur le lot :",
        "### 1. Informations du lot",
    )

    cleaned_lines: list[str] = []
    skip_blank = False
    for line in text.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in blocked_prefixes):
            skip_blank = True
            continue
        if skip_blank and not stripped:
            continue
        skip_blank = False
        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines).strip()
    return cleaned_text or text


# ─────────────────────────────────────────────────────────────────────────────
# Appel à l'API Anthropic (Claude)
# ─────────────────────────────────────────────────────────────────────────────

async def _call_anthropic_api(prompt: str) -> str | None:
    """
    Appelle l'API Anthropic pour générer une explication intelligente.
    Retourne le texte généré ou None si l'API est indisponible.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.info("ANTHROPIC_API_KEY not set — skipping AI explanation, using rule-based fallback")
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 2000,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("content", [])
            if content and isinstance(content, list):
                return content[0].get("text", "")
            return None
    except httpx.ReadTimeout:
        logger.warning("Anthropic API timeout for lot explanation")
        return None
    except Exception as exc:
        logger.warning("Anthropic API call failed: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Fallback : analyse rule-based enrichie
# ─────────────────────────────────────────────────────────────────────────────

def _rule_based_explanation(lot_data: dict, user_question: str) -> str:
    """
    Analyse causale enrichie par règles expertes — FORMAT NARRATIF.
    Génère une explication narrative : "La qualité du lot est [grade] parce que [raisons avec valeurs mesurées]"
    """
    lot = lot_data.get("lot") or {}
    execs = lot_data.get("executions") or []
    analyses = lot_data.get("analyses") or []
    production_outputs = lot_data.get("production_outputs") or []
    benchmark = lot_data.get("benchmark") or {}

    lot_ref = lot.get("reference", "?")
    variete = lot.get("variete") or "variété inconnue"
    primary_execution = _first_by(execs, "date_debut") or (execs[0] if execs else None)
    latest_analysis = _latest_by(analyses, "date_analyse") or (analyses[0] if analyses else None)
    final_output = _latest_by(production_outputs, "date_production") or (production_outputs[0] if production_outputs else None)
    
    # Durée de stockage (gère plusieurs schémas de colonnes)
    duree_stockage = _safe_float(lot.get("duree_stockage_jours"))
    if duree_stockage == 0:
        duree_stockage = _safe_float(lot.get("duree_stockage_avant_broyage"))
    if duree_stockage == 0:
        heures_depuis_recolte = _safe_float(lot.get("temps_depuis_recolte_heures"))
        if heures_depuis_recolte > 0:
            duree_stockage = heures_depuis_recolte / 24.0
    if duree_stockage == 0 and lot.get("date_reception") and execs:
        try:
            from datetime import datetime
            dr = str(lot["date_reception"])[:10]
            dp = str(execs[0].get("date_debut", ""))[:10]
            if dr and dp:
                d1 = datetime.strptime(dr, "%Y-%m-%d")
                d2 = datetime.strptime(dp, "%Y-%m-%d")
                duree_stockage = abs((d2 - d1).days)
        except Exception:
            pass

    causal_reasons: list[str] = []
    points_positifs: list[str] = []
    qualite_judgement = "moyenne"
    grade = "Non déterminé"
    production_quality = None
    analytic_grade = None

    # ── Analyse des olives à la réception ─────────────────────────────────
    acidite_olive = _safe_float(lot.get("acidite_olives_pourcent"))
    if acidite_olive > 0:
        if acidite_olive > 3.0:
            causal_reasons.append(
                f"l'acidité des olives à la réception était critique ({_fmt(acidite_olive)} %), "
                f"ce qui indique des olives blessées ou trop mûres ayant déjà subi une dégradation enzymatique importante"
            )
        elif acidite_olive > 1.5:
            causal_reasons.append(
                f"l'acidité des olives à la réception était élevée ({_fmt(acidite_olive)} %), "
                f"ce qui a risqué de dégénérer en huile classée vierge ou lampante"
            )
        else:
            points_positifs.append("l'acidité des olives à la réception était acceptable")

    maturite = _safe_float(lot.get("indice_maturite") if lot.get("indice_maturite") is not None else lot.get("maturite"))
    if maturite > 0:
        if maturite >= 5:
            causal_reasons.append(
                f"les olives étaient sur-mûres (indice {_fmt(maturite, 1)}), "
                f"ce qui a fortement réduit la teneur en polyphénols et augmenté l'acidité"
            )
        elif maturite > 3.5:
            causal_reasons.append(
                f"les olives avaient une maturité avancée (indice {_fmt(maturite, 1)}), "
                f"ce qui a diminué les polyphénols bénéfiques"
            )
        elif 1.5 <= maturite <= 3.5:
            points_positifs.append("la maturité des olives était optimale")

    if duree_stockage > 0:
        if duree_stockage > 3:
            causal_reasons.append(
                f"le temps entre la récolte et l'exécution de production a été trop large ({int(duree_stockage)} jour(s)), "
                f"permettant aux enzymes lipolytiques de dégrader les triglycérides et augmenter l'acidité"
            )
        elif duree_stockage > 1:
            causal_reasons.append(
                f"le temps entre la récolte et l'exécution de production était de {int(duree_stockage)} jour(s), "
                f"ce qui a légèrement affecté la qualité"
            )
        else:
            points_positifs.append("la trituration a été effectuée rapidement après réception")

    taux_feuilles = _safe_float(lot.get("taux_feuilles_pourcent"))
    if taux_feuilles > 0:
        if taux_feuilles > 3:
            causal_reasons.append(
                f"le taux de feuilles ({_fmt(taux_feuilles, 1)} %) était élevé, "
                f"ce qui augmente les impuretés et accélère l'oxydation enzymatique"
            )
        elif taux_feuilles > 1:
            causal_reasons.append(
                f"le taux de feuilles était de {_fmt(taux_feuilles, 1)} %, "
                f"ce qui a légèrement augmenté la charge enzymatique"
            )

    temp_malax_primary = _safe_float(primary_execution.get("temperature_malaxage")) if primary_execution else 0.0
    duree_malax_primary = _safe_float(primary_execution.get("duree_malaxage_minutes")) if primary_execution else 0.0
    presence_eau_primary = primary_execution.get("presence_ajout_eau") if primary_execution else None
    qty_eau_primary = primary_execution.get("quantite_eau_ajoutee") if primary_execution else None
    controle_temp = primary_execution.get("controle_temperature") if primary_execution else None
    type_machine = primary_execution.get("type_machine") if primary_execution else None

    # Vérifier l'absence de contrôle température et son impact direct
    if controle_temp is not None and not _parse_boolish(controle_temp) and temp_malax_primary > 0:
        causal_reasons.insert(
            0,
            f"l'absence de contrôle température lors du malaxage a laissé la température monter à {_fmt(temp_malax_primary, 1)} °C sans intervention, "
            f"ce qui explique directement l'accélération de l'oxydation et la perte de polyphénols"
        )

    # Corréler machine traditionnelle + absence de contrôle température
    if type_machine and "traditionnel" in str(type_machine).lower() and not _parse_boolish(controle_temp) and temp_malax_primary > 0:
        causal_reasons.insert(
            0,
            f"l'utilisation d'une machine {type_machine} sans système de contrôle température rend très difficile "
            f"le maintien de la température optimale, d'où les {_fmt(temp_malax_primary, 1)} °C observés"
        )

    # Signaler l'absence de lavage des olives
    lavage_effectue = lot.get("lavage_effectue")
    if lavage_effectue is not None and not _parse_boolish(lavage_effectue):
        causal_reasons.append(
            f"l'absence de lavage des olives avant trituration a conservé les résidus microbiens et lipolytiques "
            f"à la surface, accélérant l'acidification et l'oxydation"
        )

    # Si une exécution est identifiée, exploiter ses conditions comme cause de production
    if primary_execution:
        temp_malax = temp_malax_primary
        duree_malax = duree_malax_primary
        presence_eau = presence_eau_primary
        qty_eau = qty_eau_primary

        if temp_malax > 0:
            if temp_malax >= 27:
                causal_reasons.append(
                    f"la température de malaxage a atteint {_fmt(temp_malax, 1)} °C, au-dessus de la zone de confort (18-24 °C), "
                    f"ce qui accélère l'oxydation et la dégradation des composés phénoliques"
                )
            elif temp_malax > 25:
                causal_reasons.append(
                    f"la température de malaxage était de {_fmt(temp_malax, 1)} °C, légèrement trop élevée pour préserver au mieux les arômes et les polyphénols"
                )

        if duree_malax > 0:
            if duree_malax >= 50:
                causal_reasons.append(
                    f"le malaxage a duré {int(duree_malax)} min, ce qui prolonge le contact avec l'oxygène et favorise l'oxydation"
                )
            elif duree_malax > 45:
                causal_reasons.append(
                    f"le malaxage a duré {int(duree_malax)} min, légèrement au-dessus de l'optimum habituel"
                )

        if _parse_boolish(presence_eau):
            causal_reasons.append(
                f"l'ajout d'eau au malaxage" + (f" ({qty_eau} L)" if qty_eau else "") +
                " a pu entraîner une perte de polyphénols hydrophiles et une baisse de qualité organoleptique"
            )

    # Si la chaîne produit_final est connue, l'utiliser comme vérité de production
    if final_output and final_output.get("qualite"):
        production_quality = str(final_output.get("qualite")).strip()
        if production_quality:
            production_quality_low = production_quality.lower()
            if any(tok in production_quality_low for tok in ("lamp", "non comestible", "lampante")):
                qualite_judgement = "mauvaise"
                grade = "lampante"
            elif any(tok in production_quality_low for tok in ("vierge extra", "extra")):
                qualite_judgement = "bonne"
                grade = "Vierge Extra"
            elif "vierge" in production_quality_low:
                qualite_judgement = "moyenne"
                grade = "Vierge"

    methode_recolte = lot.get("methode_recolte") or lot.get("mode_recolte") or "non renseignée"
    if methode_recolte and methode_recolte.lower() not in ("non renseignée", ""):
        if any(m in methode_recolte.lower() for m in ["gaulage", "baton", "bâton", "abscission"]):
            causal_reasons.append(
                f"la récolte par {methode_recolte} a traumatisé les olives, "
                f"ce qui a activé les lipases et accéléré l'acidification"
            )

    # ── Conditions de trituration ──────────────────────────────────────────
    for ep in execs:
        etat_machine = ep.get("etat_machine", "")
        if etat_machine and "maintenance" in str(etat_machine).lower():
            causal_reasons.append(
                f"la machine utilisée était en maintenance, ce qui a compromis la qualité de la trituration"
            )

        temp_malax = _safe_float(ep.get("temperature_malaxage"))
        if temp_malax > 0:
            if temp_malax > 27:
                causal_reasons.append(
                    f"la température de malaxage était élevée ({_fmt(temp_malax, 1)} °C, dépassant le seuil critique), "
                    f"ce qui a activé les enzymes oxydatives et détruit les polyphénols bénéfiques"
                )
            elif temp_malax > 25:
                causal_reasons.append(
                    f"la température de malaxage était de {_fmt(temp_malax, 1)} °C, légèrement au-dessus de l'optimum (18-24°C)"
                )
            else:
                points_positifs.append("la température de malaxage était optimale")

        duree_malax = _safe_float(ep.get("duree_malaxage_minutes"))
        if duree_malax > 0:
            if duree_malax > 60:
                causal_reasons.append(
                    f"le malaxage a duré {int(duree_malax)} minutes, beaucoup trop long, "
                    f"ce qui a exposé l'huile trop longtemps à l'oxygène et favorisé l'oxydation"
                )
            elif duree_malax > 45:
                causal_reasons.append(
                    f"le malaxage a duré {int(duree_malax)} minutes, légèrement au-delà de l'optimum (20-45 min)"
                )
            else:
                points_positifs.append("la durée de malaxage était correcte")

        presence_eau = ep.get("presence_ajout_eau")
        if presence_eau in (1, True, "1", "oui", "yes", "true"):
            qty_eau = ep.get("quantite_eau_ajoutee")
            causal_reasons.append(
                f"l'ajout d'eau lors du malaxage" + (f" ({qty_eau} L)" if qty_eau else "")
                + " a dilué les polyphénols hydrophiles et réduit la qualité organoleptique"
            )

    # ── Analyses laboratoire ───────────────────────────────────────────────
    if analyses:
        a = analyses[0]
        acid = _safe_float(a.get("acidite_huile_pourcent"))
        perox = _safe_float(a.get("indice_peroxyde_meq_o2_kg"))
        k270 = _safe_float(a.get("k270"))
        poly = _safe_float(a.get("polyphenols_mg_kg"))
        analytic_grade = _grade_huile(acid, perox, k270)
        # Déterminer le jugement sur la qualité du produit final
        if not production_quality:
            grade = analytic_grade
            if "Lampante" in grade or "lampante" in grade:
                qualite_judgement = "mauvaise"
            elif "Vierge" in grade and "Extra" not in grade:
                qualite_judgement = "moyenne"
            elif "Extra" in grade or "Vierge Extra" in grade:
                qualite_judgement = "bonne"
            else:
                qualite_judgement = "moyenne"


        if acid > 0.8:
            causal_reasons.append(
                f"l'acidité mesurée de l'huile ({_fmt(acid)} %, seuil vierge extra ≤ 0,8 %) "
                f"reflète la dégradation des triglycérides durant la production"
            )
        else:
            points_positifs.append("l'acidité de l'huile était conforme vierge extra")

        if perox > 20:
            causal_reasons.append(
                f"l'indice de peroxyde ({_fmt(perox, 1)} meq O₂/kg, seuil ≤ 20) indique une oxydation primaire, "
                f"causée par une exposition excessive à l'air ou une température de malaxage trop élevée"
            )
        else:
            points_positifs.append("le peroxyde était conforme")

        if k270 > 0.22:
            causal_reasons.append(
                f"le K270 ({_fmt(k270, 3)}, seuil ≤ 0,22) montre une oxydation secondaire "
                f"due à un malaxage trop chaud ou un stockage inadéquat"
            )

        k232 = _safe_float(a.get("k232"))
        if k232 > 0:
            if k232 > 2.5:
                causal_reasons.append(
                    f"le K232 ({_fmt(k232, 3)}) dépasse le seuil COI de 2,50, indiquant une oxydation secondaire avancée, "
                    f"causée par le malaxage prolongé à température excessive et la perte d'antioxydants"
                )
            elif k232 < 1.5:
                points_positifs.append(f"le K232 ({_fmt(k232, 3)}) était en dessous du seuil minimum, conforme")

        if poly > 0:
            if poly < 100:
                causal_reasons.append(
                    f"les polyphénols sont très faibles ({_fmt(poly, 0)} mg/kg, référence 100-800), "
                    f"ce qui signifie que l'huile a perdu ses antioxydants naturels"
                )
            elif poly < 200:
                causal_reasons.append(
                    f"les polyphénols sont faibles ({_fmt(poly, 0)} mg/kg), ce qui réduit la durée de conservation"
                )
            else:
                points_positifs.append(f"les polyphénols étaient élevés ({_fmt(poly, 0)} mg/kg)")

    # ── Croisement final : production vs analytique ───────────────────────
    mismatch_detected = False
    mismatch_note = ""
    if final_output:
        pf_ref = final_output.get("reference", "?")
        pf_id = final_output.get("id_produit", "?")
        pf_date = final_output.get("date_production", "?")
        pf_qual = (final_output.get("qualite") or "").strip()

        if pf_qual:
            pf_qual_low = pf_qual.lower()
            if any(tok in pf_qual_low for tok in ("lamp", "non comestible", "inadmissible")):
                if latest_analysis:
                    acid = _safe_float(latest_analysis.get("acidite_huile_pourcent"))
                    perox = _safe_float(latest_analysis.get("indice_peroxyde_meq_o2_kg"))
                    k270 = _safe_float(latest_analysis.get("k270"))
                    poly = _safe_float(latest_analysis.get("polyphenols_mg_kg"))
                    analytic_grade = _grade_huile(acid, perox, k270)
                    if analytic_grade != "Lampante (non comestible brut)":
                        mismatch_detected = True
                        mismatch_note = (
                            f"Si les analyses labo montrent un grade différent ({analytic_grade}) "
                            f"avec acidité {_fmt(acid)} %, K270 {_fmt(k270, 3)} et polyphénols {_fmt(poly, 0)} mg/kg, "
                            f"il faut suspecter un problème de traçabilité, d'échantillonnage ou de saisie."
                        )
                    else:
                        causal_reasons.insert(
                            0,
                            f"Le produit final est enregistré comme « {pf_qual} » (réf {pf_ref}, id {pf_id}, date {pf_date}) et l'analyse labo confirme un grade lampante ; la cause la plus probable est la combinaison du délai de {_fmt(duree_stockage, 0)} jour(s), de la récolte traumatisante, du malaxage défavorable et de la faible teneur en polyphénols."
                        )
                else:
                    causal_reasons.insert(
                        0,
                        f"Le produit final est enregistré comme « {pf_qual} » (réf {pf_ref}, id {pf_id}, date {pf_date}), mais aucune analyse récente n'est disponible pour confirmer ou infirmer ce classement."
                    )
            elif any(tok in pf_qual_low for tok in ("vierge extra", "extra")):
                causal_reasons.insert(
                    0,
                    f"Le produit final est enregistré comme « {pf_qual} » (réf {pf_ref}, id {pf_id}, date {pf_date}) ; il faut vérifier que les conditions de production et l'analyse labo sont cohérentes avec ce classement."
                )

    # Si aucune cause forte n'a été trouvée, remettre la plus probable en tête
    if production_quality:
        if any(tok in production_quality.lower() for tok in ("lamp", "non comestible", "lampante")):
            qualite_judgement = "mauvaise"
            grade = "lampante"

    if causal_reasons:
        strong_markers = ("délai", "température", "malaxage", "eau", "gaulage", "acidité", "polyphénols", "lampante")
        causal_reasons.sort(key=lambda reason: 0 if any(marker in reason.lower() for marker in strong_markers) else 1)

    # ── Construction de la narration causale finale ────────────────────────
    narration_lines: list[str] = []

    # Paragraphe synthèse exigé pour le cas qualité mauvaise
    summary_line = ""
    if qualite_judgement == "mauvaise":
        factors: list[str] = []
        if duree_stockage > 0:
            factors.append(f"un délai de {int(round(duree_stockage))} jour(s) entre la récolte et l'extraction")
        if methode_recolte and methode_recolte.lower() not in ("non renseignée", ""):
            factors.append(f"une récolte par {methode_recolte}")
        if acidite_olive > 0:
            factors.append(f"une acidité des olives à la réception de {_fmt(acidite_olive)} %")
        if temp_malax_primary > 0:
            factors.append(f"une température de malaxage de {_fmt(temp_malax_primary, 1)} °C")
        if duree_malax_primary > 0:
            factors.append(f"un malaxage de {int(duree_malax_primary)} min")
        if _parse_boolish(presence_eau_primary):
            factors.append(f"un ajout de {qty_eau_primary or 0} L d'eau")

        if latest_analysis:
            acid_l = _safe_float(latest_analysis.get("acidite_huile_pourcent"))
            k270_l = _safe_float(latest_analysis.get("k270"))
            poly_l = _safe_float(latest_analysis.get("polyphenols_mg_kg"))
            confirmation = (
                f"Ces conditions ont favorisé la dégradation des triglycérides et l'oxydation, "
                f"ce que confirment l'acidité de l'huile à {_fmt(acid_l)} %, "
                f"le K270 à {_fmt(k270_l, 3)} et des polyphénols à {_fmt(poly_l, 0)} mg/kg."
            )
        else:
            confirmation = "Ces conditions ont favorisé la dégradation des triglycérides et l'oxydation."

        if factors:
            summary_line = (
                f"Le lot {lot_ref} est enregistré comme lampante. La cause la plus probable est "
                + ", ".join(factors)
                + ". "
                + confirmation
            )
        else:
            summary_line = (
                f"Le lot {lot_ref} est enregistré comme lampante et la cause la plus probable est "
                f"une combinaison de facteurs de récolte et de trituration défavorables. "
                + confirmation
            )

        if mismatch_detected and mismatch_note:
            summary_line += " " + mismatch_note
    
    # Ligne d'ouverture
    narration_lines.append(
        f"La qualité du produit final extrait à partir du lot {lot_ref} est {qualite_judgement} ({grade}) parce que :"
    )
    narration_lines.append("")

    if summary_line:
        narration_lines.append(summary_line)
        narration_lines.append("")
    
    # Énumérer les raisons causales
    filtered_reasons = [
        reason for reason in causal_reasons
        if "incohérence de données" not in reason.lower()
    ]
    if filtered_reasons:
        for reason in filtered_reasons:
            narration_lines.append(f"• {reason},")
    else:
        narration_lines.append("• données insuffisantes pour identifier les causes spécifiques.")
    
    narration_lines.append("")
    
    # Résumé des points positifs s'il y en a
    if points_positifs:
        narration_lines.append("Cependant, quelques points positifs :")
        for point in points_positifs:
            narration_lines.append(f"• {point}")
        narration_lines.append("")
    
    # Recommandations
    narration_lines.append("Recommandations pour améliorer la qualité :")
    recs = []
    
    causal_str = " ".join(causal_reasons)
    if "délai" in causal_str or "temps" in causal_str:
        recs.append("• Réduire le temps entre la récolte et l'exécution de production à moins de 24h")
    if "température" in causal_str and "malaxage" in causal_str:
        recs.append("• Ramener la température de malaxage à 18-24°C pour préserver les polyphénols")
    if "malaxage" in causal_str and ("long" in causal_str or "prolongé" in causal_str):
        recs.append("• Limiter la durée de malaxage à 25-35 minutes")
    if "eau" in causal_str:
        recs.append("• Réduire ou éliminer l'ajout d'eau lors du malaxage")
    if "machine" in causal_str and "maintenance" in causal_str:
        recs.append("• Vérifier et entretenir les machines avant la prochaine campagne")
    if "acidité des olives" in causal_str or "maturité" in causal_str or "récolte" in causal_str:
        methode_lower = str(methode_recolte or "").lower()
        if any(m in methode_lower for m in ("gaulage", "baton", "bâton")):
            recs.append("• Améliorer la qualité à la récolte : éviter le gaulage, trier les olives abîmées")
        else:
            recs.append("• Renforcer le tri à la récolte et limiter les olives abîmées avant trituration")
    
    if recs:
        for rec in recs[:3]:  # Top 3 recommendations
            narration_lines.append(rec)
    else:
        narration_lines.append("• Maintenir les pratiques actuelles qui donnent de bons résultats")

    return "\n".join(narration_lines)


# ─────────────────────────────────────────────────────────────────────────────
# Handler principal
# ─────────────────────────────────────────────────────────────────────────────

class ExplicationHandler(IntentHandler):
    """Handler intelligent pour expliquer la qualité/rendement d'un lot spécifique.

    1. Collecte TOUTES les données disponibles (lot, production, labo, stock, benchmark).
    2. Appelle Claude (Anthropic API) pour une analyse causale profonde.
    3. Fallback vers analyse rule-based enrichie si l'API est indisponible.
    """

    def __init__(self, service: ChatbotService):
        self.service = service

    async def handle(self, query: ChatQuery) -> IntentResult:
        # ── Extraction de la référence lot ────────────────────────────────
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
            lot_ref = (entities.get("lot_reference") or entities.get("reference_lot")
                       or entities.get("code_lot"))

        if not lot_ref:
            return IntentResult(
                text=(
                    "Précisez la référence du lot pour que je puisse l'analyser en détail. "
                    "Exemple : *\"pourquoi la qualité du lot LO01 était mauvaise ?\"*"
                ),
                data=None,
                structured_payload=None,
            )

        normalized_ref = _normalize_lot_reference(lot_ref)
        if not normalized_ref:
            return IntentResult(
                text=f"Référence de lot invalide : **{lot_ref}**.",
                data=None, structured_payload=None,
            )

        # ── Collecte des données ──────────────────────────────────────────
        lot_data = _collect_all_lot_data(normalized_ref, query.enterprise_id)

        if lot_data.get("error"):
            return IntentResult(
                text=f"Impossible de récupérer les données du lot **{normalized_ref}** : {lot_data['error']}",
                data=None, structured_payload=None,
            )

        if not lot_data.get("lot"):
            return IntentResult(
                text=f"Aucun lot trouvé pour la référence **{normalized_ref}**.",
                data=None, structured_payload=None,
            )

        # ── Génération de l'explication ───────────────────────────────────
        user_question = query.message or f"Explique la qualité du lot {normalized_ref}"

        # Tentative appel Claude API
        prompt = _build_expert_prompt(lot_data, user_question)
        ai_explanation = await _call_anthropic_api(prompt)

        if ai_explanation and len(ai_explanation.strip()) > 100:
            explanation_text = _humanize_explanation_text(ai_explanation)
            logger.info("AI explanation generated for lot %s (%d chars)", normalized_ref, len(ai_explanation))
        else:
            # Fallback rule-based enrichi
            explanation_text = _humanize_explanation_text(_rule_based_explanation(lot_data, user_question))
            logger.info("Rule-based fallback explanation for lot %s", normalized_ref)

        # ── Payload chart (paramètres labo vs seuils) ─────────────────────
        structured_payload = None
        analyses = lot_data.get("analyses") or []
        if analyses:
            a = analyses[0]
            acid = _safe_float(a.get("acidite_huile_pourcent"))
            perox = _safe_float(a.get("indice_peroxyde_meq_o2_kg"))
            k270 = _safe_float(a.get("k270"))
            k232 = _safe_float(a.get("k232"))
            poly = _safe_float(a.get("polyphenols_mg_kg"))

            benchmark = lot_data.get("benchmark") or {}
            chart_labels = ["Acidité (%)", "Peroxyde (meq O₂/kg)", "K270", "K232"]
            chart_lot = [acid, perox / 20 * 100, k270 / 0.22 * 100, k232 / 2.5 * 100]  # normalisé %
            chart_seuil = [100, 100, 100, 100]

            structured_payload = {
                "labels": chart_labels,
                "datasets": [
                    {
                        "label": f"Lot {normalized_ref} (% du seuil)",
                        "data": [round(v, 1) for v in chart_lot],
                        "type": "bar",
                        "backgroundColor": [
                            "#FF5722" if chart_lot[i] > 100 else "#4CAF50"
                            for i in range(len(chart_lot))
                        ],
                    },
                    {
                        "label": "Seuil vierge extra (100%)",
                        "data": chart_seuil,
                        "type": "line",
                        "borderColor": "#FF9800",
                        "borderDash": [5, 5],
                    },
                ],
                "raw_values": {
                    "acidite": acid, "peroxyde": perox,
                    "k270": k270, "k232": k232, "polyphenols": poly,
                },
                "grade": _grade_huile(acid, perox, k270),
                "benchmark": benchmark,
            }

        return IntentResult(
            text=explanation_text,
            data={
                "lot": lot_data.get("lot"),
                "executions": lot_data.get("executions"),
                "analyses": analyses,
                "benchmark": lot_data.get("benchmark"),
            },
            structured_payload=structured_payload,
        )