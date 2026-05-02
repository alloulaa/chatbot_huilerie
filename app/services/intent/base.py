"""
Base abstraite pour les handlers d'intent.
"""
from abc import ABC, abstractmethod
from typing import Any

from app.domain.chat import ChatQuery, IntentResult


class IntentHandler(ABC):
    """Interface abstraite pour traiter un intent."""
    
    @abstractmethod
    async def handle(self, query: ChatQuery) -> IntentResult:
        """
        Traiter un intent et retourner le résultat.
        
        Args:
            query: La requête traitée avec contexte
            
        Returns:
            IntentResult avec texte et données optionnelles
        """
        pass
