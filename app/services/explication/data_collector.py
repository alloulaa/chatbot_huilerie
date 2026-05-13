"""
Collecte complète des données d'un lot (DB).
"""
from __future__ import annotations

import logging
from typing import Any

from app.database import get_db_connection

logger = logging.getLogger(__name__)


def _collect_all_lot_data(normalized_ref: str, enterprise_id: int | None) -> dict[str, Any]:
    """
    Collecte TOUTES les données disponibles sur un lot :
    - Informations lot (variété, fournisseur, dates, acidité olives, maturité, région, sol…)
    - Étapes de production (machines, températures, durées, rendements, ajout eau…)
    - Analyses laboratoire (acidité, peroxyde, K270, K232, polyphénols…)
    - Mouvements de stock
    - Données huilerie (région, équipements)
    - Comparaison avec les autres lots de l'huilerie (benchmark)
    
    Args:
        normalized_ref: Référence normalisée du lot (ex. "LO01")
        enterprise_id: ID entreprise (optionnel, pour filtrer)
    
    Returns:
        dict[str, Any] : dictionnaire contenant toutes les données collectées ou erreur
    """
    from app.utils.lot_helpers import _safe_float

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
                       "al.k270", "al.k232", "al.polphenols_mg_kg"]
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
                    AVG(al.polphenols_mg_kg)            AS avg_polyphenols,
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
