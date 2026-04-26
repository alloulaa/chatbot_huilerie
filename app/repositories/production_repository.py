from app.repositories.base import BaseRepository


class ProductionRepository(BaseRepository):
    def total_production(self, start_date: str, end_date: str, huilerie: str | None = None):
        params = []
        query = """
            SELECT production_totale AS total
            FROM vue_production_totale
            WHERE 1=1
        """
        if huilerie:
            query += " AND LOWER(huilerie) = LOWER(%s)"
            params.append(huilerie)
        query += " LIMIT 1"
        return self._fetchone(query, tuple(params))

    def average_yield(self, start_date: str, end_date: str, huilerie: str | None = None):
        params = []
        query = """
            SELECT rendement_moyen AS avg_yield
            FROM vue_rendement
            WHERE 1=1
        """
        if huilerie:
            query += " AND LOWER(huilerie) = LOWER(%s)"
            params.append(huilerie)
        query += " LIMIT 1"
        return self._fetchone(query, tuple(params))

    def quality_distribution(self, start_date: str, end_date: str, huilerie: str | None = None):
        return []

    def non_compliant_lots(self, start_date: str, end_date: str, huilerie: str | None = None):
        return []

    def lot_features(self, lot_code: str):
        return None

    def global_kpis(self, start_date: str, end_date: str, huilerie: str | None = None):
        production = self.total_production(start_date, end_date, huilerie)
        rendement = self.average_yield(start_date, end_date, huilerie)
        return {
            "production_totale": production["total"] if production else 0,
            "rendement_moyen": rendement["avg_yield"] if rendement else 0,
            "nb_lots": 0,
            "nb_extra": 0,
        }
