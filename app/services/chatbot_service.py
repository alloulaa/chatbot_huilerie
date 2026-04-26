import logging
from typing import Any

from app.database import get_db_connection


logger = logging.getLogger(__name__)


class ChatbotService:
    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def get_prediction_from_model(self, data: dict[str, Any]):
        # Placeholder for future ML API integration.
        pass

    @staticmethod
    def _normalize_quality_label(value: Any) -> str:
        text = (str(value).strip().lower() if value is not None else "")

        if text in {
            "bonne",
            "bon",
            "bonne qualite",
            "bonne qualité",
            "excellente",
            "excellent",
            "extra",
            "top",
            "a",
        }:
            return "Bonne"

        if text in {
            "moyenne",
            "moyen",
            "acceptable",
            "standard",
            "b",
        }:
            return "Moyenne"

        if text in {
            "mauvaise",
            "mauvais",
            "faible",
            "mediocre",
            "médiocre",
            "non conforme",
            "c",
        }:
            return "Mauvaise"

        return "Inconnue"

    def get_stock(self) -> dict[str, Any]:
        query = """
            SELECT variete, SUM(quantite_restante) AS total_stock
            FROM lot_olives
            GROUP BY variete
            ORDER BY variete
        """
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall() or []

            normalized = []
            for row in rows:
                normalized.append(
                    {
                        "variete": row.get("variete") or "Inconnue",
                        "total_stock": self._to_float(row.get("total_stock"), 0.0),
                    }
                )

            return {"value": normalized}
        except Exception as exc:
            logger.exception("Error while reading stock: %s", exc)
            return {"value": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_production(self) -> dict[str, Any]:
        query = """
            SELECT SUM(quantite_produite) AS total_production
            FROM produit_final
        """
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            row = cursor.fetchone()
            value = self._to_float(row.get("total_production") if row else None, 0.0)
            return {"value": value}
        except Exception as exc:
            logger.exception("Error while reading production: %s", exc)
            return {"value": 0.0}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_machines(self) -> dict[str, Any]:
        query = """
            SELECT *
            FROM vue_machines_probleme
        """
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall() or []

            normalized = []
            for row in rows:
                machine_name = row.get("nom_machine") or row.get("machine") or "Machine inconnue"
                machine_state = row.get("etat_machine") or row.get("probleme") or row.get("etat") or "INCONNU"
                normalized.append({"nom_machine": machine_name, "etat_machine": machine_state})

            return {"value": normalized}
        except Exception as exc:
            logger.exception("Error while reading machine issues: %s", exc)
            return {"value": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_rendement(self) -> dict[str, Any]:
        query = """
            SELECT AVG(rendement) AS rendement_moyen
            FROM execution_production
        """
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            row = cursor.fetchone()
            value = self._to_float(row.get("rendement_moyen") if row else None, 0.0)
            return {"value": value}
        except Exception as exc:
            logger.exception("Error while reading rendement: %s", exc)
            return {"value": 0.0}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_prediction(self) -> dict[str, Any]:
        query = """
            SELECT
                AVG(rendement_predit_pourcent) AS rendement_predit,
                AVG(quantite_huile_recalculee_litres) AS quantite_estimee
            FROM prediction
        """
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            row = cursor.fetchone()

            rendement_predit = self._to_float(row.get("rendement_predit") if row else None, 0.0)
            quantite_estimee = self._to_float(row.get("quantite_estimee") if row else None, 0.0)

            return {"rendement_predit": rendement_predit, "quantite_estimee": quantite_estimee}
        except Exception as exc:
            logger.exception("Error while reading prediction: %s", exc)
            return {"rendement_predit": 0.0, "quantite_estimee": 0.0}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def get_qualite(self) -> dict[str, Any]:
        query = """
            SELECT qualite, COUNT(*) AS total
            FROM produit_final
            GROUP BY qualite
        """
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall() or []

            normalized = []
            summary = {
                "Bonne": 0,
                "Moyenne": 0,
                "Mauvaise": 0,
                "Inconnue": 0,
            }

            for row in rows:
                total = int(row.get("total") or 0)
                qualite_normalisee = self._normalize_quality_label(row.get("qualite"))
                summary[qualite_normalisee] = summary.get(qualite_normalisee, 0) + total

                normalized.append(
                    {
                        "qualite": row.get("qualite"),
                        "qualite_normalisee": qualite_normalisee,
                        "total": total,
                    }
                )

            return {
                "value": normalized,
                "summary": summary,
            }
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

    def diagnostic_qualite(self) -> dict[str, Any]:
        query = """
            SELECT acidite_huile_pourcent, indice_peroxyde_meq_o2_kg, k270
            FROM analyse_laboratoire
        """
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall() or []

            issues: list[str] = []
            for row in rows:
                acidite = self._to_float(row.get("acidite_huile_pourcent"), 0.0)
                peroxyde = self._to_float(row.get("indice_peroxyde_meq_o2_kg"), 0.0)
                k270 = self._to_float(row.get("k270"), 0.0)

                if acidite > 0.8:
                    issues.append("acidite elevee")
                if peroxyde > 20:
                    issues.append("indice de peroxyde eleve")
                if k270 > 0.22:
                    issues.append("k270 eleve")

            # Preserve order while removing duplicates.
            unique_issues = list(dict.fromkeys(issues))
            return {"issues": unique_issues, "rows": rows}
        except Exception as exc:
            logger.exception("Error while running quality diagnostic: %s", exc)
            return {"issues": [], "rows": []}
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()
