import logging
from typing import Any

from app.database import get_db_connection
from app.utils.shared import normalize_quality_label, to_float

logger = logging.getLogger(__name__)


class LotRepository:
    def __init__(self, db_connection_factory=None):
        self._get_db_connection = db_connection_factory or get_db_connection

    def get_lot_liste(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
        variete: str | None = None,
        non_conformes_only: bool = False,
    ) -> dict[str, Any]:
        query = """
            SELECT
                lo.id_lot,
                lo.reference,
                lo.variete,
                {supplier_select},
                lo.quantite_initiale,
                lo.quantite_restante,
                lo.date_reception,
                MAX(pf.qualite) AS qualite_brute,
                MAX(al.acidite_huile_pourcent) AS acidite_max,
                MAX(al.indice_peroxyde_meq_o2_kg) AS peroxyde_max,
                h.nom AS huilerie_nom
            FROM lot_olives lo
            JOIN huilerie h ON h.id_huilerie = lo.huilerie_id
            {supplier_join}
            LEFT JOIN execution_production ep ON ep.lot_olives_id = lo.id_lot
            LEFT JOIN produit_final pf ON pf.execution_production_id = ep.id_execution_production
            LEFT JOIN analyse_laboratoire al ON al.lot_id = lo.id_lot
            WHERE 1=1
        """
        params: list[Any] = []
        if enterprise_id is not None:
            query += " AND h.entreprise_id = %s"
            params.append(enterprise_id)
        if huilerie:
            query += " AND LOWER(h.nom) = LOWER(%s)"
            params.append(huilerie)
        if start_date and end_date:
            query += " AND lo.date_reception BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        if variete:
            query += " AND LOWER(lo.variete) = LOWER(%s)"
            params.append(variete)
        query += (
            " GROUP BY lo.id_lot ORDER BY lo.date_reception DESC, lo.reference DESC"
        )

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            supplier_select, supplier_join = self._resolve_lot_supplier_select(cursor)
            query = query.format(
                supplier_select=supplier_select, supplier_join=supplier_join
            )
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall() or []

            normalized = []
            for row in rows:
                qualite_brute = row.get("qualite_brute")
                acidite_max = to_float(row.get("acidite_max"), 0.0)
                peroxyde_max = to_float(row.get("peroxyde_max"), 0.0)
                qualite_huile = normalize_quality_label(qualite_brute)

                if qualite_huile == "Inconnue" and (
                    acidite_max > 0.8 or peroxyde_max > 20
                ):
                    qualite_huile = "Mauvaise"

                if non_conformes_only and qualite_huile not in {"Mauvaise", "Inconnue"}:
                    if acidite_max <= 0.8 and peroxyde_max <= 20:
                        continue

                normalized.append(
                    {
                        "id_lot": row.get("id_lot"),
                        "reference": row.get("reference"),
                        "variete": row.get("variete") or "Inconnue",
                        "fournisseur_nom": row.get("fournisseur_nom") or "Inconnu",
                        "quantite_initiale": to_float(
                            row.get("quantite_initiale"), 0.0
                        ),
                        "quantite_restante": to_float(
                            row.get("quantite_restante"), 0.0
                        ),
                        "date_reception": row.get("date_reception"),
                        "qualite_huile": qualite_huile,
                        "huilerie_nom": row.get("huilerie_nom"),
                    }
                )

            return {"value": normalized}
        except Exception as exc:
            logger.exception("Error while reading lot list: %s", exc)
            return {"value": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_analyse_labo(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
        lot_reference: str | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT
                al.reference,
                al.date_analyse,
                al.acidite_huile_pourcent,
                al.indice_peroxyde_meq_o2_kg,
                al.k232,
                al.k270,
                al.polyphenols_mg_kg,
                lo.reference AS lot_ref,
                lo.variete,
                h.nom AS huilerie_nom
            FROM analyse_laboratoire al
            JOIN lot_olives lo ON lo.id_lot = al.lot_id
            JOIN huilerie h ON h.id_huilerie = lo.huilerie_id
            WHERE 1=1
        """
        params: list[Any] = []
        if enterprise_id is not None:
            query += " AND h.entreprise_id = %s"
            params.append(enterprise_id)
        if huilerie:
            query += " AND LOWER(h.nom) = LOWER(%s)"
            params.append(huilerie)
        if start_date and end_date:
            query += " AND al.date_analyse BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        if lot_reference:
            normalized_ref = self._normalize_lot_reference(lot_reference)
            if normalized_ref:
                query += " AND (LOWER(lo.reference) = LOWER(%s) OR CAST(lo.id_lot AS CHAR) = %s)"
                params.extend([normalized_ref, normalized_ref])
        query += " ORDER BY al.date_analyse DESC, al.id_analyse DESC"

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall() or []

            normalized = []
            for row in rows:
                normalized.append(
                    {
                        "reference": row.get("reference"),
                        "lot_ref": row.get("lot_ref"),
                        "date_analyse": row.get("date_analyse"),
                        "acidite_huile_pourcent": to_float(
                            row.get("acidite_huile_pourcent"), 0.0
                        ),
                        "indice_peroxyde_meq_o2_kg": to_float(
                            row.get("indice_peroxyde_meq_o2_kg"), 0.0
                        ),
                        "k232": to_float(row.get("k232"), 0.0),
                        "k270": to_float(row.get("k270"), 0.0),
                        "polyphenols_mg_kg": to_float(
                            row.get("polyphenols_mg_kg"), 0.0
                        ),
                        "variete": row.get("variete"),
                        "huilerie_nom": row.get("huilerie_nom"),
                    }
                )

            return {"value": normalized}
        except Exception as exc:
            logger.exception("Error while reading laboratory analysis: %s", exc)
            return {"value": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def _resolve_lot_supplier_select(
        self, cursor, lot_alias: str = "lo"
    ) -> tuple[str, str]:
        cursor.execute("DESCRIBE lot_olives")
        cols = {c["Field"] for c in (cursor.fetchall() or [])}

        if "fournisseur_nom" in cols:
            return f"{lot_alias}.fournisseur_nom AS fournisseur_nom", ""

        join_sql = (
            f" LEFT JOIN fournisseur f ON f.id_fournisseur = {lot_alias}.fournisseur_id"
        )
        select_sql = "COALESCE(NULLIF(TRIM(f.nom), ''), 'Inconnu') AS fournisseur_nom"
        return select_sql, join_sql

    def _normalize_lot_reference(self, text: str | None) -> str | None:
        if not text:
            return None
        t = str(text).strip().upper()
        # Accept LONN, LOT N, L N, digits
        import re

        if re.fullmatch(r"LO\d+", t):
            return f"LO{int(t[2:]):02d}"
        match = re.fullmatch(r"(?:LOT|L)\s*(\d+)", t)
        if match:
            return f"LO{int(match.group(1)):02d}"
        if re.fullmatch(r"\d+", t):
            return f"LO{int(t):02d}"
        return t

    def get_meilleur_fournisseur(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT
                {supplier_select},
                COUNT(*) AS nb_lots,
                COALESCE(SUM(lo.quantite_initiale), 0) AS quantite_totale_kg,
                COALESCE(AVG(ep.rendement), 0) AS rendement_moyen,
                COALESCE(AVG(lo.acidite_olives_pourcent), 0) AS acidite_moyenne
            FROM lot_olives lo
            LEFT JOIN execution_production ep ON ep.lot_olives_id = lo.id_lot
            JOIN huilerie h ON h.id_huilerie = lo.huilerie_id
            {supplier_join}
            WHERE 1=1
        """
        params: list[Any] = []
        if enterprise_id is not None:
            query += " AND h.entreprise_id = %s"
            params.append(enterprise_id)
        if huilerie:
            query += " AND LOWER(h.nom) = LOWER(%s)"
            params.append(huilerie)
        if start_date and end_date:
            query += " AND lo.date_reception BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        query += " GROUP BY fournisseur_nom ORDER BY quantite_totale_kg DESC, rendement_moyen DESC"

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            supplier_select, supplier_join = self._resolve_lot_supplier_select(cursor)
            query = query.format(
                supplier_select=supplier_select, supplier_join=supplier_join
            )
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall() or []

            normalized = []
            for index, row in enumerate(rows, start=1):
                normalized.append(
                    {
                        "rang": index,
                        "fournisseur_nom": row.get("fournisseur_nom") or "Inconnu",
                        "nb_lots": int(row.get("nb_lots") or 0),
                        "quantite_totale_kg": to_float(
                            row.get("quantite_totale_kg"), 0.0
                        ),
                        "rendement_moyen": to_float(row.get("rendement_moyen"), 0.0),
                        "acidite_moyenne": to_float(row.get("acidite_moyenne"), 0.0),
                    }
                )

            return {"value": normalized}
        except Exception as exc:
            logger.exception("Error while reading supplier ranking: %s", exc)
            return {"value": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_campagnes(
        self,
        huilerie: str | None = None,
        enterprise_id: int | None = None,
        annee: str | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT
                c.reference,
                c.annee,
                c.date_debut,
                c.date_fin,
                h.nom AS huilerie_nom,
                COUNT(l.id_lot) AS nb_lots,
                COALESCE(SUM(l.quantite_initiale), 0) AS total_olives_kg
            FROM campagne_olives c
            LEFT JOIN huilerie h ON h.id_huilerie = c.huilerie_id
            LEFT JOIN lot_olives l ON l.campagne_id = c.id_campagne
            WHERE 1=1
        """
        params: list[Any] = []
        if enterprise_id is not None:
            query += " AND h.entreprise_id = %s"
            params.append(enterprise_id)
        if huilerie:
            query += " AND LOWER(h.nom) = LOWER(%s)"
            params.append(huilerie)
        if annee:
            annee_filtre = str(annee).strip()
            if annee_filtre:
                query += " AND c.annee LIKE %s"
                params.append(f"%{annee_filtre}%")
        query += " GROUP BY c.id_campagne ORDER BY c.date_debut DESC, c.reference DESC"

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall() or []

            normalized = []
            for row in rows:
                normalized.append(
                    {
                        "reference": row.get("reference"),
                        "annee": row.get("annee"),
                        "date_debut": row.get("date_debut"),
                        "date_fin": row.get("date_fin"),
                        "huilerie_nom": row.get("huilerie_nom"),
                        "nb_lots": int(row.get("nb_lots") or 0),
                        "total_olives_kg": to_float(row.get("total_olives_kg"), 0.0),
                    }
                )

            return {"value": normalized}
        except Exception as exc:
            logger.exception("Error while reading campaigns: %s", exc)
            return {"value": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_mouvements_stock(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT
                sm.reference,
                sm.date_mouvement,
                sm.type_mouvement,
                sm.commentaire,
                lo.reference AS lot_ref,
                lo.variete,
                h.nom AS huilerie_nom
            FROM stock_movement sm
            JOIN lot_olives lo ON lo.id_lot = sm.lot_id
            JOIN huilerie h ON h.id_huilerie = lo.huilerie_id
            WHERE 1=1
        """
        params: list[Any] = []
        if enterprise_id is not None:
            query += " AND h.entreprise_id = %s"
            params.append(enterprise_id)
        if huilerie:
            query += " AND LOWER(h.nom) = LOWER(%s)"
            params.append(huilerie)
        if start_date and end_date:
            query += " AND sm.date_mouvement BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        query += " ORDER BY sm.date_mouvement DESC, sm.id_stock_movement DESC"

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall() or []

            normalized = []
            for row in rows:
                normalized.append(
                    {
                        "reference": row.get("reference"),
                        "date_mouvement": row.get("date_mouvement"),
                        "type_mouvement": row.get("type_mouvement"),
                        "commentaire": row.get("commentaire"),
                        "lot_ref": row.get("lot_ref"),
                        "variete": row.get("variete"),
                        "huilerie_nom": row.get("huilerie_nom"),
                    }
                )

            return {"value": normalized}
        except Exception as exc:
            logger.exception("Error while reading stock movements: %s", exc)
            return {"value": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_reception(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT
                lo.reference,
                lo.variete,
                {supplier_select},
                lo.quantite_initiale,
                lo.date_reception,
                h.nom AS huilerie_nom
            FROM lot_olives lo
            JOIN huilerie h ON h.id_huilerie = lo.huilerie_id
            {supplier_join}
            WHERE 1=1
        """
        params: list[Any] = []
        if enterprise_id is not None:
            query += " AND h.entreprise_id = %s"
            params.append(enterprise_id)
        if huilerie:
            query += " AND LOWER(h.nom) = LOWER(%s)"
            params.append(huilerie)
        if start_date and end_date:
            query += " AND lo.date_reception BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        query += " ORDER BY lo.date_reception DESC, lo.reference DESC"

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            supplier_select, supplier_join = self._resolve_lot_supplier_select(cursor)
            query = query.format(
                supplier_select=supplier_select, supplier_join=supplier_join
            )
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall() or []

            normalized = []
            total = 0.0
            for row in rows:
                quantite = to_float(row.get("quantite_initiale"), 0.0)
                total += quantite
                normalized.append(
                    {
                        "reference": row.get("reference"),
                        "variete": row.get("variete") or "Inconnue",
                        "fournisseur_nom": row.get("fournisseur_nom") or "Inconnu",
                        "quantite_initiale": quantite,
                        "date_reception": row.get("date_reception"),
                        "huilerie_nom": row.get("huilerie_nom"),
                    }
                )

            return {"value": normalized, "total_kg": total}
        except Exception as exc:
            logger.exception("Error while reading receptions: %s", exc)
            return {"value": [], "total_kg": 0.0}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_lot_cycle_vie(
        self,
        lot_reference: str,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        normalized_ref = self._normalize_lot_reference(lot_reference)
        if not normalized_ref:
            return {"error": "Référence de lot invalide."}

        query_lot = """
            SELECT
                lo.id_lot,
                lo.reference,
                lo.variete,
                {supplier_select},
                lo.quantite_initiale,
                lo.quantite_restante,
                lo.date_reception,
                lo.date_recolte,
                lo.campagne_id,
                h.nom AS huilerie_nom
            FROM lot_olives lo
            JOIN huilerie h ON h.id_huilerie = lo.huilerie_id
            {supplier_join}
            WHERE (LOWER(lo.reference) = LOWER(%s)
               OR CAST(lo.id_lot AS CHAR) = %s)
        """

        params_lot: list[Any] = [normalized_ref, normalized_ref]
        if enterprise_id is not None:
            query_lot += " AND h.entreprise_id = %s"
            params_lot.append(enterprise_id)
        query_lot += " LIMIT 1"

        query_exec = """
            SELECT reference, date_debut, date_fin_reelle, statut, rendement
            FROM execution_production
            WHERE lot_olives_id = %s
            ORDER BY date_debut ASC, id_execution_production ASC
        """

        query_analyse = """
            SELECT reference, date_analyse, acidite_huile_pourcent, indice_peroxyde_meq_o2_kg, k270
            FROM analyse_laboratoire
            WHERE lot_id = %s
            ORDER BY date_analyse ASC, id_analyse ASC
        """

        query_stock = """
            SELECT sm.reference, sm.date_mouvement, sm.type_mouvement, sm.commentaire
            FROM stock_movement sm
            WHERE sm.lot_id = %s
            ORDER BY sm.date_mouvement ASC, sm.id_stock_movement ASC
        """

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            supplier_select, supplier_join = self._resolve_lot_supplier_select(cursor)
            query_lot = query_lot.format(
                supplier_select=supplier_select, supplier_join=supplier_join
            )
            cursor.execute(query_lot, tuple(params_lot))
            lot_row = cursor.fetchone()
            if not lot_row:
                return {"error": f"Aucun lot trouvé pour {normalized_ref}."}

            lot_id = lot_row.get("id_lot")
            lot_info = {
                "id_lot": lot_id,
                "reference": lot_row.get("reference"),
                "variete": lot_row.get("variete"),
                "fournisseur_nom": lot_row.get("fournisseur_nom"),
                "quantite_initiale": to_float(lot_row.get("quantite_initiale"), 0.0),
                "quantite_restante": to_float(lot_row.get("quantite_restante"), 0.0),
                "date_reception": lot_row.get("date_reception"),
                "date_recolte": lot_row.get("date_recolte"),
                "campagne_id": lot_row.get("campagne_id"),
                "huilerie_nom": lot_row.get("huilerie_nom"),
            }

            steps: list[dict[str, Any]] = []
            if lot_info.get("date_reception"):
                steps.append(
                    {
                        "etape": "reception",
                        "date": lot_info["date_reception"],
                        "details": f"Réception du lot {lot_info.get('reference')} par {lot_info.get('fournisseur_nom') or 'fournisseur inconnu'}",
                    }
                )

            cursor.execute(query_exec, (lot_id,))
            exec_rows = cursor.fetchall() or []
            for row in exec_rows:
                steps.append(
                    {
                        "etape": "production",
                        "date": row.get("date_debut"),
                        "details": f"Exécution {row.get('reference')} - statut {row.get('statut')}",
                        "rendement": to_float(row.get("rendement"), 0.0),
                        "reference": row.get("reference"),
                    }
                )

            cursor.execute(query_analyse, (lot_id,))
            analyse_rows = cursor.fetchall() or []
            for row in analyse_rows:
                steps.append(
                    {
                        "etape": "analyse_labo",
                        "date": row.get("date_analyse"),
                        "details": f"Analyse {row.get('reference') or ''}".strip(),
                        "acidite_huile_pourcent": to_float(
                            row.get("acidite_huile_pourcent"), 0.0
                        ),
                        "indice_peroxyde_meq_o2_kg": to_float(
                            row.get("indice_peroxyde_meq_o2_kg"), 0.0
                        ),
                        "k270": to_float(row.get("k270"), 0.0),
                        "reference": row.get("reference"),
                    }
                )

            cursor.execute(query_stock, (lot_id,))
            stock_rows = cursor.fetchall() or []
            for row in stock_rows:
                steps.append(
                    {
                        "etape": "stock",
                        "date": row.get("date_mouvement"),
                        "details": row.get("commentaire") or row.get("type_mouvement"),
                        "type_mouvement": row.get("type_mouvement"),
                        "reference": row.get("reference"),
                    }
                )

            return {"lot": lot_info, "steps": steps}
        except Exception as exc:
            logger.exception("Error while reading lot lifecycle: %s", exc)
            return {"error": "Impossible de récupérer le cycle de vie du lot."}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()
