"""
Gestion centralisée de la session de chat.
Isole SESSION_CONTEXT du controller.
"""
from typing import Any


class SessionService:
    """Service pour gérer le contexte de session utilisateur."""
    
    _store: dict[str, dict[str, Any]] = {}
    
    @classmethod
    def get(cls, session_id: str) -> dict[str, Any]:
        """Récupérer le contexte de session."""
        return cls._store.get(session_id, {})
    
    @classmethod
    def update(cls, session_id: str, data: dict[str, Any]) -> None:
        """Mettre à jour le contexte de session."""
        current = cls._store.get(session_id, {})
        current.update(data)
        cls._store[session_id] = current
    
    @classmethod
    def get_pending_visualization(cls, session_id: str) -> dict[str, Any] | None:
        """Récupérer la visualisation en attente."""
        ctx = cls._store.get(session_id, {})
        return ctx.get("pending_visualization")
    
    @classmethod
    def set_pending_visualization(cls, session_id: str, pending: dict[str, Any]) -> None:
        """Définir une visualisation en attente."""
        current = cls._store.get(session_id, {})
        current["pending_visualization"] = pending
        cls._store[session_id] = current
    
    @classmethod
    def clear_pending_visualization(cls, session_id: str) -> None:
        """Effacer la visualisation en attente."""
        current = cls._store.get(session_id, {})
        current.pop("pending_visualization", None)
        cls._store[session_id] = current
    
    @classmethod
    def clear(cls, session_id: str) -> None:
        """Effacer le contexte de session."""
        cls._store.pop(session_id, None)
