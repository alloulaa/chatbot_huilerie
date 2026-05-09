from app.repositories.lot_repository import LotRepository
from app.repositories.machine_repository import MachineRepository
from app.repositories.metrics_repository import MetricsRepository


class FakeCursor:
    def __init__(self, fetchall_responses=None, fetchone_responses=None):
        self.fetchall_responses = list(fetchall_responses or [])
        self.fetchone_responses = list(fetchone_responses or [])
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        if self.fetchall_responses:
            return self.fetchall_responses.pop(0)
        return []

    def fetchone(self):
        if self.fetchone_responses:
            return self.fetchone_responses.pop(0)
        return None

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, dictionary=True):
        return self._cursor

    def is_connected(self):
        return True

    def close(self):
        pass


def test_machine_repository_get_all_machines_uses_injected_connection():
    cursor = FakeCursor(
        fetchall_responses=[
            [
                {
                    "nom_machine": "Presse A",
                    "categorie_machine": "Pressage",
                    "type_machine": "Hydraulique",
                    "nb_executions": 3,
                    "etat_machine": "EN SERVICE",
                    "huilerie_nom": "H1",
                }
            ]
        ]
    )
    repo = MachineRepository(db_connection_factory=lambda: FakeConnection(cursor))

    result = repo.get_all_machines(enterprise_id=7)

    assert result["value"][0]["nomMachine"] == "Presse A"
    assert result["value"][0]["nbExecutions"] == 3
    assert "h.entreprise_id = %s" in cursor.executed[0][0]
    assert cursor.executed[0][1] == (7,)


def test_metrics_repository_get_qualite_normalizes_labels():
    cursor = FakeCursor(
        fetchall_responses=[
            [
                {"qualite": "Bon", "total": 4},
                {"qualite": "médiocre", "total": 2},
            ]
        ]
    )
    repo = MetricsRepository(db_connection_factory=lambda: FakeConnection(cursor))

    result = repo.get_qualite(huilerie="H1")

    assert result["summary"]["Bonne"] == 4
    assert result["summary"]["Mauvaise"] == 2
    assert result["value"][0]["qualite_normalisee"] == "Bonne"
    assert result["value"][1]["qualite_normalisee"] == "Mauvaise"


def test_lot_repository_get_reception_reads_supplier_from_describe_and_returns_total():
    cursor = FakeCursor(
        fetchall_responses=[
            [{"Field": "fournisseur_nom"}],
            [
                {
                    "reference": "LO01",
                    "variete": "Arbequina",
                    "fournisseur_nom": "Fournisseur X",
                    "quantite_initiale": 1200,
                    "date_reception": "2026-05-04",
                    "huilerie_nom": "H1",
                }
            ],
        ]
    )
    repo = LotRepository(db_connection_factory=lambda: FakeConnection(cursor))

    result = repo.get_reception(huilerie="H1")

    assert result["total_kg"] == 1200.0
    assert result["value"][0]["fournisseur_nom"] == "Fournisseur X"
    assert cursor.executed[0][0].startswith("DESCRIBE lot_olives")
    assert "LOWER(h.nom) = LOWER(%s)" in cursor.executed[1][0]
