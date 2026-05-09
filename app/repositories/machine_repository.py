import logging
from typing import Any

from app.database import get_db_connection
from app.utils.shared import to_float

logger = logging.getLogger(__name__)


class MachineRepository:
    def __init__(self, db_connection_factory=None):
        self._get_db_connection = db_connection_factory or get_db_connection

    def get_all_machines(
        self,
        huilerie: str | None = None,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT
                m.nom_machine,
                m.categorie_machine,
                m.type_machine,
                m.etat_machine,
                COALESCE(u.nb_executions, 0) AS nb_executions,
                h.nom AS huilerie_nom
            FROM machine m
            JOIN huilerie h ON h.id_huilerie = m.huilerie_id
            LEFT JOIN (
                SELECT
                    et.machine_id,
                    COUNT(DISTINCT ep.id_execution_production) AS nb_executions
                FROM etape_production et
                JOIN guide_production gp ON gp.id_guide_production = et.guide_production_id
                JOIN execution_production ep ON ep.guide_production_id = gp.id_guide_production
                JOIN lot_olives lo ON lo.id_lot = ep.lot_olives_id
                JOIN huilerie h2 ON h2.id_huilerie = lo.huilerie_id
                WHERE et.machine_id IS NOT NULL
                GROUP BY et.machine_id
            ) u ON u.machine_id = m.id_machine
            WHERE 1=1
        """
        params: list[Any] = []
        if enterprise_id is not None:
            query += " AND h.entreprise_id = %s"
            params.append(enterprise_id)
        if huilerie:
            query += " AND LOWER(h.nom) = LOWER(%s)"
            params.append(huilerie)
        query += " ORDER BY h.nom, m.nom_machine"

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall() or []

            normalized = []
            for row in rows:
                machine_name = (
                    row.get("nom_machine")
                    or row.get("nomMachine")
                    or row.get("machine")
                    or "Machine inconnue"
                )
                huilerie_nom = row.get("huilerie_nom") or "Huilerie inconnue"
                normalized.append(
                    {
                        "nomMachine": machine_name,
                        "categorieMachine": row.get("categorie_machine")
                        or row.get("categorieMachine")
                        or "Inconnue",
                        "typeMachine": row.get("type_machine")
                        or row.get("typeMachine")
                        or "Inconnu",
                        "nbExecutions": int(
                            row.get("nb_executions") or row.get("nbExecutions") or 0
                        ),
                        "etatMachine": row.get("etat_machine")
                        or row.get("etatMachine")
                        or "INCONNU",
                        "huilerie": huilerie_nom,
                    }
                )

            return {"value": normalized}
        except Exception as exc:
            logger.exception("Error while reading all machines: %s", exc)
            return {"value": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_machines(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
        status_filter: str | None = None,
    ) -> dict[str, Any]:
        normalized_status = status_filter.strip().lower() if status_filter else None
        if normalized_status in {"panne", "en panne"}:
            normalized_status = "maintenance"
        normalized_status_value = (
            normalized_status.replace("_", " ").replace("-", " ").strip()
            if normalized_status
            else None
        )

        query = """
            SELECT DISTINCT m.nom_machine, m.etat_machine, m.reference, m.capacite
            FROM machine m
            JOIN huilerie h ON h.id_huilerie = m.huilerie_id
            WHERE 1=1
        """
        params: list[Any] = []
        if normalized_status:
            state_expr = "REPLACE(REPLACE(LOWER(COALESCE(m.etat_machine, '')), '_', ' '), '-', ' ')"
            if normalized_status == "maintenance":
                query += f" AND {state_expr} IN ('maintenance', 'en maintenance')"
            else:
                query += f" AND {state_expr} = %s"
                params.append(normalized_status_value)

        if enterprise_id is not None:
            query += " AND h.entreprise_id = %s"
            params.append(enterprise_id)
        if huilerie:
            query += " AND LOWER(h.nom) = LOWER(%s)"
            params.append(huilerie)
        query += " ORDER BY m.nom_machine"

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall() or []

            normalized = []
            for row in rows:
                machine_name = (
                    row.get("nom_machine")
                    or row.get("nomMachine")
                    or row.get("machine")
                    or "Machine inconnue"
                )
                machine_state = (
                    row.get("etat_machine")
                    or row.get("etatMachine")
                    or row.get("probleme")
                    or row.get("etat")
                    or "INCONNU"
                )
                normalized.append(
                    {"nomMachine": machine_name, "etatMachine": machine_state}
                )

            return {"value": normalized}
        except Exception as exc:
            logger.exception("Error while reading machine issues: %s", exc)
            return {"value": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_machines_utilisees(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT
                m.nom_machine,
                m.reference AS machine_ref,
                COALESCE(u.nb_executions, 0) AS nb_executions,
                COALESCE(u.rendement_moyen, 0) AS rendement_moyen,
                COALESCE(u.total_produit, 0) AS total_produit
            FROM machine m
            JOIN huilerie h ON h.id_huilerie = m.huilerie_id
            LEFT JOIN (
                SELECT
                    et.machine_id,
                    COUNT(DISTINCT ep.id_execution_production) AS nb_executions,
                    AVG(ep.rendement) AS rendement_moyen,
                    SUM(COALESCE(pf.quantite_produite, 0)) AS total_produit
                FROM etape_production et
                JOIN guide_production gp ON gp.id_guide_production = et.guide_production_id
                JOIN execution_production ep ON ep.guide_production_id = gp.id_guide_production
                LEFT JOIN produit_final pf ON pf.execution_production_id = ep.id_execution_production
                JOIN lot_olives lo ON lo.id_lot = ep.lot_olives_id
                JOIN huilerie h2 ON h2.id_huilerie = lo.huilerie_id
                WHERE et.machine_id IS NOT NULL
        """
        subquery_params: list[Any] = []
        subquery_filters: list[str] = []
        if enterprise_id is not None:
            subquery_filters.append("h2.entreprise_id = %s")
            subquery_params.append(enterprise_id)
        if huilerie:
            subquery_filters.append("LOWER(h2.nom) = LOWER(%s)")
            subquery_params.append(huilerie)
        if start_date and end_date:
            subquery_filters.append("ep.date_debut BETWEEN %s AND %s")
            subquery_params.extend([start_date, end_date])

        if subquery_filters:
            query += " AND " + " AND ".join(subquery_filters)
        query += " GROUP BY et.machine_id ) u ON u.machine_id = m.id_machine"
        query += " WHERE 1=1"
        outer_params: list[Any] = []
        if enterprise_id is not None:
            query += " AND h.entreprise_id = %s"
            outer_params.append(enterprise_id)
        if huilerie:
            query += " AND LOWER(h.nom) = LOWER(%s)"
            outer_params.append(huilerie)
        query += " ORDER BY m.nom_machine ASC"

        params: list[Any] = subquery_params + outer_params

        connection = None
        cursor = None
        try:
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall() or []

            normalized = []
            for row in rows:
                nom = (
                    row.get("nom_machine")
                    or row.get("nomMachine")
                    or row.get("nom")
                    or "Machine inconnue"
                )
                machine_ref = (
                    row.get("machine_ref")
                    or row.get("machineRef")
                    or row.get("reference")
                    or "N/D"
                )
                nb_exec = int(row.get("nb_executions") or row.get("nbExecutions") or 0)
                rend_moy = to_float(
                    row.get("rendement_moyen") or row.get("rendementMoyen"), 0.0
                )
                total_prod = to_float(
                    row.get("total_produit") or row.get("totalProduit"), 0.0
                )
                normalized.append(
                    {
                        "nomMachine": nom,
                        "machineRef": machine_ref,
                        "nbExecutions": nb_exec,
                        "rendementMoyen": rend_moy,
                        "totalProduit": total_prod,
                    }
                )

            return {"value": normalized}
        except Exception as exc:
            logger.exception("Error while reading machine usage: %s", exc)
            return {"value": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()
