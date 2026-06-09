"""
Tests d'integration minimum pour l'API du chatbot Huilerie.
"""
import os

os.environ["NLP_ANALYZER"] = "regex"

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import app
from app.nlp.factory import NLPFactory
from app.services.session_service import SessionService

_CHAT_RESPONSE_KEYS = {
    "type", "message", "intent", "confidence", "entities",
    "response", "applied_scope", "applied_permissions",
}


@pytest.fixture(autouse=True)
def reset_state():
    NLPFactory._analyzer_type = "regex"
    NLPFactory._instance = None
    SessionService._store = {}
    yield
    NLPFactory._instance = None
    SessionService._store = {}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ask_greeting_returns_valid_schema(client):
    response = client.post(
        "/chat/ask",
        json={"message": "bonjour", "session_id": "it-greeting"},
    )
    assert response.status_code == 200
    body = response.json()
    assert _CHAT_RESPONSE_KEYS.issubset(body.keys())
    assert body["intent"] == "inconnu"
    assert isinstance(body["confidence"], float)
    assert isinstance(body["entities"], dict)
    assert body["message"] == body["response"]


def test_ask_missing_message_returns_422(client):
    response = client.post("/chat/ask", json={"session_id": "it-invalid"})
    assert response.status_code == 422


def test_ask_stock_intent_detected_end_to_end(client):
    response = client.post(
        "/chat/ask",
        json={"message": "quel est le stock ?", "session_id": "it-stock"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "stock"
    assert isinstance(body["message"], str) and body["message"]


def test_ask_machine_intent_detected(client):
    response = client.post(
        "/chat/ask",
        json={"message": "liste des machines", "session_id": "it-machine"},
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "machine"


def test_intent_override_machine_keyword_via_http(client):
    response = client.post(
        "/chat/ask",
        json={"message": "quelle machine est en panne", "session_id": "it-override"},
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "machine"


def test_session_context_persisted_across_requests(client):
    session_id = "it-session"
    first = client.post(
        "/chat/ask",
        json={"message": "production ce mois", "session_id": session_id},
    )
    second = client.post(
        "/chat/ask",
        json={"message": "et le stock", "session_id": session_id},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert "applied_scope" in first.json()
    assert "applied_scope" in second.json()
    assert second.json()["intent"] == "stock"


def test_rbac_permission_denied_via_http(client):
    auth_data = {
        "utilisateur": {"profil": "user"},
        "permissions": [{"module": "GUIDE_PRODUCTION", "canRead": True}],
    }
    with patch(
        "app.services.auth_helper.get_user_permissions", return_value=auth_data
    ), patch(
        "app.services.auth_helper.get_user_huilerie", return_value=None
    ):
        response = client.post(
            "/chat/ask",
            json={"message": "quel est le stock", "session_id": "it-rbac-deny"},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "stock"
    assert "refus" in body["message"].lower() or "acces" in body["message"].lower()


def test_rbac_admin_allows_access(client):
    auth_data = {"utilisateur": {"profil": "admin"}, "permissions": []}
    with patch(
        "app.services.auth_helper.get_user_permissions", return_value=auth_data
    ), patch(
        "app.services.auth_helper.get_user_huilerie", return_value=None
    ):
        response = client.post(
            "/chat/ask",
            json={"message": "quel est le stock", "session_id": "it-rbac-admin"},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "stock"
    assert "refus" not in body["message"].lower()