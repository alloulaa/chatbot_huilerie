from app.repositories.alert_repository import AlertRepository


class AlertService:
    def __init__(self):
        self.repo = AlertRepository()

    def active_alerts(self, huilerie: str | None = None):
        rows = self.repo.active_alerts(huilerie)
        if not rows:
            return {"text": "Aucune alerte active.", "data": []}
        summary = " ; ".join([f"[{r['priorite']}] {r['message']}" for r in rows[:3]])
        return {"text": f"Alertes actives : {summary}.", "data": [dict(r) for r in rows]}
