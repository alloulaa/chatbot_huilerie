import logging
from typing import Any

from app.database import get_db_connection
from app.utils.shared import normalize_quality_label, to_float

logger = logging.getLogger(__name__)


class MetricsRepository:
    def __init__(self, db_connection_factory=None):
        self._get_db_connection = db_connection_factory or get_db_connection

    def get_stock(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT
                s.reference AS reference_stock,
                s.type_stock,
                s.variete,
                SUM(s.quantite_disponible) AS total_stock,
                GROUP_CONCAT(DISTINCT lo.reference ORDER BY lo.reference SEPARATOR ', ') AS references_lots
            FROM stock s
            LEFT JOIN lot_olives lo ON lo.id_lot = s.lot_id
            LEFT JOIN huilerie h ON h.id_huilerie = lo.huilerie_id
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
        query += " GROUP BY s.reference, s.type_stock, s.variete ORDER BY s.reference, s.variete"

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall() or []
            normalized = [
                {
                    "reference_stock": row.get("reference_stock") or "N/D",
                    "type_stock": row.get("type_stock") or "N/D",
                    "variete": row.get("variete") or "Inconnue",
                    "total_stock": to_float(row.get("total_stock"), 0.0),
                    "quantite_disponible": to_float(row.get("total_stock"), 0.0),
                    "references_lots": row.get("references_lots") or "",
                    "lot_reference": row.get("references_lots") or "",
                }
                for row in rows
            ]
            return {"value": normalized}
        except Exception as exc:
            logger.exception("Error while reading stock: %s", exc)
            return {"value": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_production(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT SUM(pf.quantite_produite) AS total_production
            FROM produit_final pf
            JOIN execution_production ep ON ep.id_execution_production = pf.execution_production_id
            JOIN lot_olives lo ON lo.id_lot = ep.lot_olives_id
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
            query += " AND pf.date_production BETWEEN %s AND %s"
            params.extend([start_date, end_date])

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            return {
                "value": to_float(row.get("total_production") if row else None, 0.0)
            }
        except Exception as exc:
            logger.exception("Error while reading production: %s", exc)
            return {"value": 0.0}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_rendement(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT AVG(ep.rendement) AS rendement_moyen
            FROM execution_production ep
            JOIN lot_olives lo ON lo.id_lot = ep.lot_olives_id
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
            query += " AND ep.date_debut BETWEEN %s AND %s"
            params.extend([start_date, end_date])

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            return {"value": to_float(row.get("rendement_moyen") if row else None, 0.0)}
        except Exception as exc:
            logger.exception("Error while reading rendement: %s", exc)
            return {"value": 0.0}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_prediction(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT
                AVG(p.rendement_predit_pourcent) AS rendement_predit,
                AVG(p.quantite_huile_recalculee_litres) AS quantite_estimee
            FROM prediction p
            JOIN execution_production ep ON ep.id_execution_production = p.execution_production_id
            JOIN lot_olives lo ON lo.id_lot = ep.lot_olives_id
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
            query += " AND ep.date_debut BETWEEN %s AND %s"
            params.extend([start_date, end_date])

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            rendement_predit = to_float(
                row.get("rendement_predit") if row else None, 0.0
            )
            quantite_estimee = to_float(
                row.get("quantite_estimee") if row else None, 0.0
            )
            return {
                "rendement_predit": rendement_predit,
                "quantite_estimee": quantite_estimee,
            }
        except Exception as exc:
            logger.exception("Error while reading prediction: %s", exc)
            return {"rendement_predit": 0.0, "quantite_estimee": 0.0}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_qualite(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT pf.qualite, COUNT(*) AS total
            FROM produit_final pf
            JOIN execution_production ep ON ep.id_execution_production = pf.execution_production_id
            JOIN lot_olives lo ON lo.id_lot = ep.lot_olives_id
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
            query += " AND pf.date_production BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        query += " GROUP BY pf.qualite"

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall() or []

            normalized = []
            summary = {"Bonne": 0, "Moyenne": 0, "Mauvaise": 0, "Inconnue": 0}
            for row in rows:
                total = int(row.get("total") or 0)
                qualite_normalisee = normalize_quality_label(row.get("qualite"))
                summary[qualite_normalisee] = summary.get(qualite_normalisee, 0) + total
                normalized.append(
                    {
                        "qualite": row.get("qualite"),
                        "qualite_normalisee": qualite_normalisee,
                        "total": total,
                    }
                )

            return {"value": normalized, "summary": summary}
        except Exception as exc:
            logger.exception("Error while reading quality distribution: %s", exc)
            return {
                "value": [],
                "summary": {"Bonne": 0, "Moyenne": 0, "Mauvaise": 0, "Inconnue": 0},
            }
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def diagnostic_qualite(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT al.acidite_huile_pourcent, al.indice_peroxyde_meq_o2_kg, al.k270, al.k232, al.polyphenols_mg_kg
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

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall() or []

            issues: list[str] = []
            for row in rows:
                acidite = to_float(row.get("acidite_huile_pourcent"), 0.0)
                peroxyde = to_float(row.get("indice_peroxyde_meq_o2_kg"), 0.0)
                k270 = to_float(row.get("k270"), 0.0)
                k232 = to_float(row.get("k232"), 0.0)
                polyphenols = to_float(row.get("polyphenols_mg_kg"), 0.0)

                if acidite < 0.1 or acidite > 5:
                    issues.append("acidite hors intervalle standard")
                if peroxyde < 5 or peroxyde > 40:
                    issues.append("indice de peroxyde hors intervalle standard")
                if k270 < 0.1 or k270 > 0.5:
                    issues.append("k270 hors intervalle standard")
                if k232 < 1.5 or k232 > 3.5:
                    issues.append("k232 hors intervalle standard")
                if polyphenols and (polyphenols < 100 or polyphenols > 800):
                    issues.append("polyphenols hors intervalle standard")

            return {"issues": list(dict.fromkeys(issues)), "rows": rows}
        except Exception as exc:
            logger.exception("Error while running quality diagnostic: %s", exc)
            return {"issues": [], "rows": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()
