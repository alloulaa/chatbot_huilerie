"""
Tests unitaires pour PermissionService - Validation des permissions RBAC
"""
import pytest
from unittest.mock import Mock, patch
from app.services.permission_service import is_intent_allowed, is_admin, is_huilerie_allowed


class TestPermissionService:
    """Tests pour PermissionService"""

    def test_is_intent_allowed_with_permission(self):
        """Test 1: is_intent_allowed() avec permission valide"""
        permissions = [
            {"module": "STOCK", "canRead": True}
        ]
        
        result = is_intent_allowed("stock", permissions)
        assert result == True

    def test_is_intent_allowed_without_permission(self):
        """Test 2: is_intent_allowed() sans permission"""
        permissions = [
            {"module": "PRODUCTION", "canRead": True}
        ]
        
        result = is_intent_allowed("stock", permissions)
        assert result == False

    def test_is_intent_allowed_with_none_permissions(self):
        """Test 3: is_intent_allowed() avec permissions None"""
        result = is_intent_allowed("stock", None)
        assert result == False

    def test_is_intent_allowed_unknown_intent(self):
        """Test 4: is_intent_allowed() avec intent inconnu (autorise par défaut)"""
        permissions = []
        
        result = is_intent_allowed("unknown_intent", permissions)
        assert result == True

    def test_is_admin_true(self):
        """Test 5: is_admin() avec profil admin"""
        auth_data = {
            "utilisateur": {
                "profil": "admin"
            }
        }
        
        result = is_admin(auth_data)
        assert result == True

    def test_is_admin_false(self):
        """Test 6: is_admin() avec profil non-admin"""
        auth_data = {
            "utilisateur": {
                "profil": "user"
            }
        }
        
        result = is_admin(auth_data)
        assert result == False

    def test_is_admin_none_auth_data(self):
        """Test 7: is_admin() avec auth_data None"""
        result = is_admin(None)
        assert result == False

    @patch('app.services.permission_service.get_db_connection')
    def test_is_huilerie_allowed_none_huilerie(self, mock_db):
        """Test 8: is_huilerie_allowed() avec huilerie None (autorise)"""
        result = is_huilerie_allowed(None, enterprise_id=1)
        assert result == True
        mock_db.assert_not_called()

    @patch('app.services.permission_service.get_db_connection')
    def test_is_huilerie_allowed_none_enterprise_id(self, mock_db):
        """Test 9: is_huilerie_allowed() avec enterprise_id None (autorise)"""
        result = is_huilerie_allowed("test_huilerie", enterprise_id=None)
        assert result == True
        mock_db.assert_not_called()

    @patch('app.services.permission_service.get_db_connection')
    def test_is_huilerie_allowed_valid_match(self, mock_db):
        """Test 10: is_huilerie_allowed() avec correspondance valide"""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"entreprise_id": 1, "id_huilerie": 1}
        mock_db.return_value = mock_conn
        
        result = is_huilerie_allowed("test_huilerie", enterprise_id=1)
        assert result == True

    @patch('app.services.permission_service.get_db_connection')
    def test_is_huilerie_allowed_invalid_enterprise(self, mock_db):
        """Test 11: is_huilerie_allowed() avec entreprise différente"""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"entreprise_id": 2, "id_huilerie": 1}
        mock_db.return_value = mock_conn
        
        result = is_huilerie_allowed("test_huilerie", enterprise_id=1)
        assert result == False

    @patch('app.services.permission_service.get_db_connection')
    def test_is_huilerie_allowed_not_found(self, mock_db):
        """Test 12: is_huilerie_allowed() avec huilerie non trouvée"""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        mock_db.return_value = mock_conn
        
        result = is_huilerie_allowed("fake_huilerie", enterprise_id=1)
        assert result == False
