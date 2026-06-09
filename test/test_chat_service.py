"""
Tests unitaires pour ChatService - Service principal du chatbot
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.chat_service import ChatService
from app.domain.intent import Intent
from app.domain.chat import ChatQuery, IntentResult


@pytest.fixture
def mock_nlp_analyzer():
    """Mock pour l'analyseur NLP"""
    analyzer = Mock()
    analyzer.analyze = AsyncMock()
    return analyzer


@pytest.fixture
def mock_chatbot_service():
    """Mock pour le ChatbotService"""
    service = Mock()
    return service


@pytest.fixture
def chat_service(mock_nlp_analyzer):
    """Fixture pour ChatService avec NLP mocké"""
    with patch('app.services.chat_service.ChatbotService'):
        service = ChatService(nlp_analyzer=mock_nlp_analyzer)
        return service


class TestChatService:
    """Tests pour ChatService"""

    @pytest.mark.asyncio
    async def test_process_message_simple_intent(self, chat_service, mock_nlp_analyzer):
        """Test 1: process_message avec intent simple (STOCK)"""
        from app.domain.intent import NLPResult, Period
        
        # Configurer le mock NLP
        mock_nlp_analyzer.analyze.return_value = NLPResult(
            intention=Intent.STOCK,
            confiance=0.9,
            huilerie="test_huilerie",
            periode=Period.AUJOURD_HUI,
            type_huile=None,
            variete=None,
            code_lot=None,
            reference_lot=None,
            lot_reference=None,
            campagne_annee=None
        )
        
        # Mock le handler
        mock_handler = AsyncMock()
        mock_handler.handle.return_value = IntentResult(
            text="Réponse de test",
            data={"items": []}
        )
        chat_service._handlers[Intent.STOCK] = mock_handler
        
        # Exécuter
        result = await chat_service.process_message(
            message="Quel est le stock?",
            session_id="test-session",
            huilerie="test_huilerie",
            enterprise_id=1,
            permissions=["STOCK"],
            user_is_admin=False,
            auth_available=False
        )
        
        # Vérifier
        assert result["intent"] == "stock"
        assert result["confidence"] == 0.9
        assert result["text"] == "Réponse de test"
        assert result["data"] == {"items": []}

    @pytest.mark.asyncio
    async def test_intent_override_machine_keyword(self, chat_service, mock_nlp_analyzer):
        """Test 2: Vérification des overrides d'intent (keywords machine)"""
        from app.domain.intent import NLPResult, Period
        
        # Configurer le mock NLP pour retourner un intent différent
        mock_nlp_analyzer.analyze.return_value = NLPResult(
            intention=Intent.PRODUCTION,  # Intent initial
            confiance=0.8,
            huilerie=None,
            periode=None,
            type_huile=None,
            variete=None,
            code_lot=None,
            reference_lot=None,
            lot_reference=None,
            campagne_annee=None
        )
        
        # Mock le handler
        mock_handler = AsyncMock()
        mock_handler.handle.return_value = IntentResult(
            text="Liste des machines",
            data=[]
        )
        chat_service._handlers[Intent.MACHINE] = mock_handler
        
        # Exécuter avec keyword machine
        result = await chat_service.process_message(
            message="Quelle est la liste des machines?",
            session_id="test-session",
            auth_available=False
        )
        
        # Vérifier que l'override a fonctionné
        assert result["intent"] == "machine"

    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, chat_service, mock_nlp_analyzer):
        """Test 3: Gestion des erreurs/exceptions dans les handlers"""
        from app.domain.intent import NLPResult, Period
        
        # Configurer le mock NLP
        mock_nlp_analyzer.analyze.return_value = NLPResult(
            intention=Intent.STOCK,
            confiance=0.9,
            huilerie=None,
            periode=None,
            type_huile=None,
            variete=None,
            code_lot=None,
            reference_lot=None,
            lot_reference=None,
            campagne_annee=None
        )
        
        # Mock le handler qui lève une exception
        mock_handler = AsyncMock()
        mock_handler.handle.side_effect = Exception("Test error")
        chat_service._handlers[Intent.STOCK] = mock_handler
        
        # Exécuter
        result = await chat_service.process_message(
            message="Test message",
            session_id="test-session",
            auth_available=False
        )
        
        # Vérifier que l'erreur est gérée
        assert result["text"] == "Une erreur s'est produite lors du traitement de votre requête."
        assert result["data"] is None

    @pytest.mark.asyncio
    async def test_rbac_permission_denied(self, chat_service, mock_nlp_analyzer):
        """Test 4: Validation RBAC (permission denied)"""
        from app.domain.intent import NLPResult, Period
        
        # Configurer le mock NLP
        mock_nlp_analyzer.analyze.return_value = NLPResult(
            intention=Intent.STOCK,
            confiance=0.9,
            huilerie=None,
            periode=None,
            type_huile=None,
            variete=None,
            code_lot=None,
            reference_lot=None,
            lot_reference=None,
            campagne_annee=None
        )
        
        # Exécuter sans permission
        result = await chat_service.process_message(
            message="Quel est le stock?",
            session_id="test-session",
            permissions=[],  # Pas de permission
            user_is_admin=False,
            auth_available=True
        )
        
        # Vérifier que l'accès est refusé
        assert result["error"] == "permission_denied"
        assert "Accès refusé" in result["text"]

    def test_has_period_keyword(self):
        """Test 5: Vérification des keywords de période"""
        assert ChatService._has_period_keyword("aujourd'hui") == True
        assert ChatService._has_period_keyword("hier") == True
        assert ChatService._has_period_keyword("cette semaine") == True
        assert ChatService._has_period_keyword("ce mois") == True
        assert ChatService._has_period_keyword("2025") == True
        assert ChatService._has_period_keyword("message sans période") == False
