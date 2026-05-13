import logging
from typing import Any

from app.database import get_db_connection
from app.repositories.machine_repository import MachineRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.lot_repository import LotRepository


logger = logging.getLogger(__name__)


class ChatbotService:
    def __init__(self):
        self.machine_repository = MachineRepository(db_connection_factory=get_db_connection)
        self.metrics_repository = MetricsRepository(db_connection_factory=get_db_connection)
        self.lot_repository = LotRepository(db_connection_factory=get_db_connection)

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
            "vierge",
            "vierge extra",
            "vierge supérieure",
        }:
            return "Bonne"

        if text in {"moyenne", "moyen", "moyenne qualite", "moyenne qualité", "b"}:
            return "Moyenne"

        if text in {"mauvaise", "mauvais", "mauvaise qualite", "mauvaise qualité", "c", "d", "lampante", "raffinee", "raffinée"}:
            return "Mauvaise"

        return "Inconnue"

    # Machine delegations
    def get_all_machines(self, huilerie: str | None = None, enterprise_id: int | None = None) -> dict[str, Any]:
        return self.machine_repository.get_all_machines(huilerie, enterprise_id)

    def get_machines(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
        status_filter: str | None = None,
    ) -> dict[str, Any]:
        return self.machine_repository.get_machines(huilerie, start_date, end_date, enterprise_id, status_filter)

    def get_machines_utilisees(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
    ) -> dict[str, Any]:
        return self.machine_repository.get_machines_utilisees(huilerie, start_date, end_date, enterprise_id)

    # Metrics delegations
    def get_stock(self, huilerie: str | None = None, start_date: str | None = None, end_date: str | None = None, enterprise_id: int | None = None) -> dict[str, Any]:
        return self.metrics_repository.get_stock(huilerie, start_date, end_date, enterprise_id)

    def get_production(self, huilerie: str | None = None, start_date: str | None = None, end_date: str | None = None, enterprise_id: int | None = None) -> dict[str, Any]:
        return self.metrics_repository.get_production(huilerie, start_date, end_date, enterprise_id)

    def get_rendement(self, huilerie: str | None = None, start_date: str | None = None, end_date: str | None = None, enterprise_id: int | None = None) -> dict[str, Any]:
        return self.metrics_repository.get_rendement(huilerie, start_date, end_date, enterprise_id)

    def get_prediction(self, huilerie: str | None = None, start_date: str | None = None, end_date: str | None = None, enterprise_id: int | None = None) -> dict[str, Any]:
        return self.metrics_repository.get_prediction(huilerie, start_date, end_date, enterprise_id)

    def get_qualite(self, huilerie: str | None = None, start_date: str | None = None, end_date: str | None = None, enterprise_id: int | None = None) -> dict[str, Any]:
        return self.metrics_repository.get_qualite(huilerie, start_date, end_date, enterprise_id)

    def diagnostic_qualite(self, huilerie: str | None = None, start_date: str | None = None, end_date: str | None = None, enterprise_id: int | None = None) -> dict[str, Any]:
        return self.metrics_repository.diagnostic_qualite(huilerie, start_date, end_date, enterprise_id)

    # Lot/campaign delegations
    def get_meilleur_fournisseur(self, huilerie: str | None = None, start_date: str | None = None, end_date: str | None = None, enterprise_id: int | None = None) -> dict[str, Any]:
        return self.lot_repository.get_meilleur_fournisseur(huilerie, start_date, end_date, enterprise_id)

    def get_lot_cycle_vie(self, lot_reference: str, enterprise_id: int | None = None) -> dict[str, Any]:
        return self.lot_repository.get_lot_cycle_vie(lot_reference, enterprise_id)

    def get_lot_liste(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
        variete: str | None = None,
        non_conformes_only: bool = False,
    ) -> dict[str, Any]:
        return self.lot_repository.get_lot_liste(huilerie, start_date, end_date, enterprise_id, variete, non_conformes_only)

    def get_campagnes(self, huilerie: str | None = None, enterprise_id: int | None = None, annee: str | None = None) -> dict[str, Any]:
        return self.lot_repository.get_campagnes(huilerie, enterprise_id, annee)

    def get_analyse_labo(
        self,
        huilerie: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        enterprise_id: int | None = None,
        lot_reference: str | None = None,
    ) -> dict[str, Any]:
        return self.lot_repository.get_analyse_labo(huilerie, start_date, end_date, enterprise_id, lot_reference)

    def get_mouvements_stock(self, huilerie: str | None = None, start_date: str | None = None, end_date: str | None = None, enterprise_id: int | None = None) -> dict[str, Any]:
        return self.lot_repository.get_mouvements_stock(huilerie, start_date, end_date, enterprise_id)

    def get_reception(self, huilerie: str | None = None, start_date: str | None = None, end_date: str | None = None, enterprise_id: int | None = None) -> dict[str, Any]:
        return self.lot_repository.get_reception(huilerie, start_date, end_date, enterprise_id)
