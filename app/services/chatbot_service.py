import logging
from typing import Any

from app.database import get_db_connection


logger = logging.getLogger(__name__)


class ChatbotService:
    def get_stock(self) -> dict[str, Any]:
        query_by_type = """
            SELECT total_stock
            FROM vue_stock_total
            WHERE LOWER(type_stock) = %s
            LIMIT 1
        """
        query_any = """
            SELECT total_stock
            FROM vue_stock_total
            LIMIT 1
        """
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query_by_type, ("olive",))
            row = cursor.fetchone()

            if not row:
                logger.info("No stock row for type_stock='olive', fallback to first row")
                cursor.execute(query_any)
                row = cursor.fetchone()

            if not row:
                logger.warning("No stock row found in vue_stock_total")
                return {"message": "Aucune donnee de stock disponible pour le moment.", "value": None}

            value = row.get("total_stock")
            if value is None:
                logger.warning("Stock row has null total_stock")
                return {"message": "Aucune donnee de stock disponible pour le moment.", "value": None}

            return {"message": f"Le stock actuel est de {value} litres", "value": value}
        except Exception as exc:
            logger.exception("Error while reading stock: %s", exc)
            return {"message": "Impossible de recuperer le stock actuellement.", "value": None}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_production(self) -> dict[str, Any]:
        query = """
            SELECT total_production
            FROM vue_production_totale
            LIMIT 1
        """
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            row = cursor.fetchone()

            if not row:
                logger.warning("No production row found in vue_production_totale")
                return {"message": "Aucune donnee de production disponible pour le moment.", "value": None}

            value = row.get("total_production")
            if value is None:
                logger.warning("Production row has null total_production")
                return {"message": "Aucune donnee de production disponible pour le moment.", "value": None}

            return {"message": f"La production totale est de {value} litres", "value": value}
        except Exception as exc:
            logger.exception("Error while reading production: %s", exc)
            return {"message": "Impossible de recuperer la production actuellement.", "value": None}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_machines(self) -> dict[str, Any]:
        query = """
            SELECT nom_machine, etat_machine
            FROM vue_machines_probleme
        """
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                logger.warning("No machine issue rows found in vue_machines_probleme")
                return {"message": "Aucune machine en probleme actuellement.", "value": []}

            machine_labels: list[str] = []
            for row in rows:
                machine = row.get("nom_machine") or "Machine inconnue"
                probleme = row.get("etat_machine")
                if probleme:
                    machine_labels.append(f"{machine} ({probleme})")
                else:
                    machine_labels.append(str(machine))

            response_text = "Machines necessitant attention : " + ", ".join(machine_labels)
            return {"message": response_text, "value": rows}
        except Exception as exc:
            logger.exception("Error while reading machine issues: %s", exc)
            return {"message": "Impossible de recuperer les informations machines actuellement.", "value": None}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_rendement(self) -> dict[str, Any]:
        query = """
            SELECT rendement_moyen
            FROM vue_rendement
            LIMIT 1
        """
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            row = cursor.fetchone()

            if not row:
                logger.warning("No rendement row found in vue_rendement")
                return {"message": "Aucune donnee de rendement disponible pour le moment.", "value": None}

            value = row.get("rendement_moyen")
            if value is None:
                logger.warning("Rendement row has null rendement_moyen")
                return {"message": "Aucune donnee de rendement disponible pour le moment.", "value": None}

            return {"message": f"Le rendement moyen est de {value} %", "value": value}
        except Exception as exc:
            logger.exception("Error while reading rendement: %s", exc)
            return {"message": "Impossible de recuperer le rendement actuellement.", "value": None}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()
