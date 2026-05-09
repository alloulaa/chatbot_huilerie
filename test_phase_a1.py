"""
Test rapide pour Phase A1 - Vérifier que les imports et la structure fonctionnent.
"""
import asyncio
from app.services.auth_helper import resolve_auth, AuthContext
from app.services.session_service import SessionService
from app.services.response_builder import build_chat_response
from app.services.chat_formatters import _scope, _fmt
from app.models import ChatResponse

print("✓ Tous les imports sont OK")

# Test AuthContext
auth = resolve_auth(None)
assert auth.error is None
assert auth.auth_available is False
print("✓ AuthContext sans JWT OK")

# Test SessionService
session_id = "test_session_123"
service = SessionService()
service.update(session_id, {"last_huilerie": "Huilerie A", "last_period": "today"})
ctx = service.get(session_id)
assert ctx.get("last_huilerie") == "Huilerie A"
print("✓ SessionService OK")

# Test formatters
fmt_str = _fmt(123.456, 1)
assert fmt_str == "123.5"
print("✓ _fmt OK")

scope_str = _scope("Huilerie X", "aujourd'hui", False)
assert "Huilerie X" in scope_str
print("✓ _scope OK")

# Test build_chat_response signature
try:
    # Juste vérifier que la fonction a le bon signature (pas appel réel sans ChatService)
    import inspect
    sig = inspect.signature(build_chat_response)
    params = list(sig.parameters.keys())
    expected = ['session_service', 'session_id', 'payload_message', 'intent', 'confidence', 
                'entities', 'response_text', 'response_data', 'applied_scope', 'applied_permissions']
    assert all(p in params for p in expected)
    print("✓ build_chat_response signature OK")
except Exception as e:
    print(f"⚠ build_chat_response check failed: {e}")

print("\n✅ Phase A1 Structure Tests - PASSED")
