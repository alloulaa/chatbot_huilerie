"""
Factory pour créer les analyseurs NLP.
Centralise le choix entre Groq, Regex, etc.
"""
import os
from app.nlp.base import NLPAnalyzer


class NLPFactory:
    """Factory pour créer les bonnes instances d'analyseurs NLP."""
    
    _analyzer_type: str | None = None
    _instance: NLPAnalyzer | None = None
    
    @classmethod
    def set_analyzer_type(cls, analyzer_type: str) -> None:
        """Définir le type d'analyseur à utiliser."""
        cls._analyzer_type = analyzer_type
        cls._instance = None  # Reset instance
    
    @classmethod
    def create(cls, analyzer_type: str | None = None) -> NLPAnalyzer:
        """
        Créer une instance d'analyseur NLP.
        
        Args:
            analyzer_type: "groq", "regex", ou None pour utiliser config env
            
        Returns:
            Instance d'une classe implémentant NLPAnalyzer
        """
        analyzer_type = analyzer_type or cls._analyzer_type or os.getenv("NLP_ANALYZER", "groq")
        
        if analyzer_type == "groq":
            from app.nlp.groq import GroqAnalyzer
            return GroqAnalyzer()
        elif analyzer_type == "regex":
            from app.nlp.regex_analyzer import RegexAnalyzer
            return RegexAnalyzer()
        else:
            # Default fallback
            from app.nlp.groq import GroqAnalyzer
            return GroqAnalyzer()
    
    @classmethod
    def get_instance(cls) -> NLPAnalyzer:
        """
        Obtenir une instance singleton (réutilisation).
        """
        if cls._instance is None:
            cls._instance = cls.create()
        return cls._instance
