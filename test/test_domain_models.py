"""
Tests unitaires pour les modèles de domaine - ChatQuery et IntentResult
"""
import pytest
from app.domain.chat import ChatQuery, IntentResult
from app.domain.intent import Intent


class TestChatQuery:
    """Tests pour ChatQuery"""

    def test_from_raw_creation(self):
        """Test 1: ChatQuery.from_raw() création et validation"""
        query = ChatQuery.from_raw(
            message="Test message",
            session_id="test-session",
            intent=Intent.STOCK,
            confidence=0.9,
            huilerie="test_huilerie",
            enterprise_id=1,
            permissions=["STOCK"],
            period_label="aujourd_hui",
            explicit_period=True,
            start_date="2025-01-01",
            end_date="2025-01-31",
            extra_context={"custom": "value"}
        )
        
        assert query.message == "Test message"
        assert query.session_id == "test-session"
        assert query.intent == Intent.STOCK
        assert query.confidence == 0.9
        assert query.huilerie == "test_huilerie"
        assert query.enterprise_id == 1
        assert query.permissions == ["STOCK"]
        assert query.period_label == "aujourd_hui"
        assert query.explicit_period == True
        assert query.start_date == "2025-01-01"
        assert query.end_date == "2025-01-31"
        assert query.extra_context == {"custom": "value"}

    def test_from_raw_defaults(self):
        """Test 2: ChatQuery.from_raw() avec valeurs par défaut"""
        query = ChatQuery.from_raw(
            message="Test message",
            session_id="test-session",
            intent=Intent.PRODUCTION
        )
        
        assert query.message == "Test message"
        assert query.session_id == "test-session"
        assert query.intent == Intent.PRODUCTION
        assert query.confidence == 0.5  # Valeur par défaut
        assert query.huilerie is None
        assert query.enterprise_id is None
        assert query.permissions == []
        assert query.period_label is None
        assert query.explicit_period == False
        assert query.start_date is None
        assert query.end_date is None
        assert query.extra_context == {}


class TestIntentResult:
    """Tests pour IntentResult"""

    def test_has_chart_with_valid_data(self):
        """Test 3: IntentResult.has_chart() avec données valides"""
        result = IntentResult(
            text="Test response",
            data={"items": []},
            structured_payload={
                "labels": ["A", "B", "C"],
                "datasets": [{"data": [1, 2, 3]}]
            }
        )
        
        assert result.has_chart() == True

    def test_has_chart_without_data(self):
        """Test 4: IntentResult.has_chart() sans données graphiques"""
        result = IntentResult(
            text="Test response",
            data={"items": []},
            structured_payload=None
        )
        
        assert result.has_chart() == False

    def test_has_chart_with_incomplete_data(self):
        """Test 5: IntentResult.has_chart() avec données incomplètes"""
        result = IntentResult(
            text="Test response",
            data={"items": []},
            structured_payload={
                "labels": ["A", "B", "C"]
                # Manque "datasets"
            }
        )
        
        assert result.has_chart() == False

    def test_is_multi_item_with_list(self):
        """Test 6: IntentResult.is_multi_item() avec liste multiple"""
        result = IntentResult(
            text="Test response",
            data=[{"id": 1}, {"id": 2}, {"id": 3}]
        )
        
        assert result.is_multi_item() == True

    def test_is_multi_item_with_single_item(self):
        """Test 7: IntentResult.is_multi_item() avec un seul item"""
        result = IntentResult(
            text="Test response",
            data=[{"id": 1}]
        )
        
        assert result.is_multi_item() == False

    def test_is_multi_item_without_list(self):
        """Test 8: IntentResult.is_multi_item() sans liste"""
        result = IntentResult(
            text="Test response",
            data={"single": "item"}
        )
        
        assert result.is_multi_item() == False
