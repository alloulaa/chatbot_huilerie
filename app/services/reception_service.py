from app.repositories.reception_repository import ReceptionRepository


class ReceptionService:
    def __init__(self):
        self.repo = ReceptionRepository()

    def total_reception(self, start_date: str, end_date: str, period_text: str, huilerie: str | None = None):
        row = self.repo.total_reception(start_date, end_date, huilerie)
        total = round(row["total"], 2)
        target = f" pour l'huilerie {huilerie}" if huilerie else ""
        return {
            "text": f"La quantité totale d'olives reçues{target} sur {period_text} est de {total} kg.",
            "data": {"metric": "reception_olives", "value": total, "unit": "kg"},
        }
