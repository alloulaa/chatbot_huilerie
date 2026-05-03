"""
Modèles de domaine pour les requêtes et réponses de chat.
"""
from typing import Any
from dataclasses import dataclass, field

from app.domain.intent import Intent


@dataclass
class ChatQuery:
    """Représentation d'une requête de chat traitée."""
    message: str
    session_id: str
    intent: Intent
    confidence: float
    huilerie: str | None = None
    enterprise_id: int | None = None
    permissions: list[str] = field(default_factory=list)
    period_label: str | None = None
    explicit_period: bool = False
    start_date: str | None = None
    end_date: str | None = None
    extra_context: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_raw(cls, message: str, session_id: str, intent: Intent, **kwargs) -> "ChatQuery":
        """Créer depuis les données brutes."""
        return cls(
            message=message,
            session_id=session_id,
            intent=intent,
            confidence=kwargs.get("confidence", 0.5),
            huilerie=kwargs.get("huilerie"),
            enterprise_id=kwargs.get("enterprise_id"),
            permissions=kwargs.get("permissions", []),
            period_label=kwargs.get("period_label"),
            explicit_period=kwargs.get("explicit_period", False),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
            extra_context=kwargs.get("extra_context", {}),
        )


@dataclass
class IntentResult:
    """Résultat du traitement d'un intent."""
    text: str
    data: Any = None
    structured_payload: dict[str, Any] | None = None
    chart_data: dict[str, Any] | None = None
    
    def has_chart(self) -> bool:
        """Vérifier si le résultat contient des données graphiques."""
        return (
            self.structured_payload is not None
            and "labels" in self.structured_payload
            and "datasets" in self.structured_payload
        )
    
    def is_multi_item(self) -> bool:
        """Vérifier s'il y a plusieurs items (pour proposer choice)."""
        if isinstance(self.data, list):
            return len(self.data) > 1
        return False
