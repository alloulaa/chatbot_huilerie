import pytest

import app.services.query_service as cs


class FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.executed = None

    def execute(self, query, params=None):
        self.executed = (query, params)

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def close(self):
        pass


class FakeConnection:
    def __init__(self, rows=None):
        self._cursor = FakeCursor(rows)

    def cursor(self, dictionary=True):
        return self._cursor

    def is_connected(self):
        return True

    def close(self):
        pass


def test_get_machines_utilisees_aggregation(monkeypatch):
    rows = [
        {
            "nom_machine": "Presse A",
            "machine_ref": "REF-1",
            "nb_executions": 2,
            "rendement_moyen": 45.5,
            "total_produit": 100.0,
        },
        {
            "nom_machine": "Broyeur B",
            "machine_ref": "REF-2",
            "nb_executions": 5,
            "rendement_moyen": 39.0,
            "total_produit": 250.0,
        },
    ]

    fake_conn = FakeConnection(rows=rows)

    # Patch the get_db_connection symbol used in the service module
    monkeypatch.setattr(cs, "get_db_connection", lambda: fake_conn)

    service = cs.ChatbotService()
    result = service.get_machines_utilisees(huilerie="H1", enterprise_id=123)

    assert isinstance(result, dict)
    assert "value" in result
    assert isinstance(result["value"], list)
    assert len(result["value"]) == 2

    first = result["value"][0]
    assert first["nomMachine"] == "Presse A"
    assert first["machineRef"] == "REF-1"
    assert first["nbExecutions"] == 2
    assert abs(first["rendementMoyen"] - 45.5) < 1e-6
    assert abs(first["totalProduit"] - 100.0) < 1e-6

