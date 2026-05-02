"""
Interface abstraite pour les analyseurs NLP.
Permet de basculer entre différentes implémentations (Groq, Regex, etc.)
"""
from abc import ABC, abstractmethod
from app.domain.intent import NLPResult


class NLPAnalyzer(ABC):
    """Interface abstraite pour un analyseur de langage naturel."""
    
    @abstractmethod
    async def analyze(self, message: str) -> NLPResult:
        """
        Analyser un message et retourner les entités extraites.
        
        Args:
            message: Le message utilisateur
            
        Returns:
            NLPResult avec intention, confiance, et entités extraites
        """
        pass
