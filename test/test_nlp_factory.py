"""
Tests unitaires pour NLPFactory - Factory pour créer les analyseurs NLP
"""
import pytest
from unittest.mock import patch
from app.nlp.factory import NLPFactory
from app.nlp.base import NLPAnalyzer


class TestNLPFactory:
    """Tests pour NLPFactory"""

    def test_create_groq_analyzer(self):
        """Test 1: create() avec type groq"""
        analyzer = NLPFactory.create("groq")
        assert analyzer is not None
        assert isinstance(analyzer, NLPAnalyzer)
        
    def test_create_regex_analyzer(self):
        """Test 2: create() avec type regex"""
        analyzer = NLPFactory.create("regex")
        assert analyzer is not None
        assert isinstance(analyzer, NLPAnalyzer)

    def test_create_default_analyzer(self):
        """Test 3: create() sans type (default)"""
        analyzer = NLPFactory.create()
        assert analyzer is not None
        assert isinstance(analyzer, NLPAnalyzer)

    def test_get_instance_singleton(self):
        """Test 4: get_instance() singleton pattern"""
        # Reset instance
        NLPFactory._instance = None
        
        # Premier appel
        instance1 = NLPFactory.get_instance()
        # Deuxième appel
        instance2 = NLPFactory.get_instance()
        
        # Vérifier que c'est la même instance
        assert instance1 is instance2

    def test_set_analyzer_type(self):
        """Test 5: set_analyzer_type() change le type"""
        # Définir le type
        NLPFactory.set_analyzer_type("regex")
        
        # Créer avec le type défini
        analyzer = NLPFactory.create()
        assert analyzer is not None
        
        # Reset
        NLPFactory._analyzer_type = None
        NLPFactory._instance = None

    @patch.dict('os.environ', {'NLP_ANALYZER': 'regex'})
    def test_create_from_env_variable(self):
        """Test 6: create() utilise la variable d'environnement"""
        analyzer = NLPFactory.create()
        assert analyzer is not None
        assert isinstance(analyzer, NLPAnalyzer)
