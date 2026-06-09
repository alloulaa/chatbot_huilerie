"""
Tests unitaires pour le normalizer - Résolution des périodes
"""
import pytest
from datetime import date
from app.nlp.normalizer import resolve_period


class TestNormalizer:
    """Tests pour resolve_period"""

    def test_resolve_period_aujourd_hui(self):
        """Test 1: resolve_period() pour aujourd'hui"""
        today = date.today()
        start, end, label = resolve_period("aujourd_hui")
        
        assert start == today.strftime("%Y-%m-%d")
        assert end == today.strftime("%Y-%m-%d")
        assert label == "aujourd'hui"

    def test_resolve_period_hier(self):
        """Test 2: resolve_period() pour hier"""
        yesterday = date.today() - __import__('datetime').timedelta(days=1)
        start, end, label = resolve_period("hier")
        
        assert start == yesterday.strftime("%Y-%m-%d")
        assert end == yesterday.strftime("%Y-%m-%d")
        assert label == "hier"

    def test_resolve_period_cette_semaine(self):
        """Test 3: resolve_period() pour cette semaine"""
        today = date.today()
        start_of_week = today - __import__('datetime').timedelta(days=today.weekday())
        end_of_week = start_of_week + __import__('datetime').timedelta(days=6)
        
        start, end, label = resolve_period("cette_semaine")
        
        assert start == start_of_week.strftime("%Y-%m-%d")
        assert end == end_of_week.strftime("%Y-%m-%d")
        assert label == "cette semaine"

    def test_resolve_period_ce_mois(self):
        """Test 4: resolve_period() pour ce mois"""
        today = date.today()
        start_of_month = date(today.year, today.month, 1)
        
        import calendar
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_of_month = date(today.year, today.month, last_day)
        
        start, end, label = resolve_period("ce_mois")
        
        assert start == start_of_month.strftime("%Y-%m-%d")
        assert end == end_of_month.strftime("%Y-%m-%d")
        assert label == "ce mois-ci"

    def test_resolve_period_annee_2025(self):
        """Test 5: resolve_period() pour l'année 2025"""
        start, end, label = resolve_period("annee_2025")
        
        assert start == "2025-01-01"
        assert end == "2025-12-31"
        assert label == "en 2025"

    def test_resolve_period_default(self):
        """Test 6: resolve_period() avec valeur None (default)"""
        today = date.today()
        start, end, label = resolve_period(None)
        
        assert start == today.strftime("%Y-%m-%d")
        assert end == today.strftime("%Y-%m-%d")
        assert label == "aujourd'hui"

    def test_resolve_period_last_7_days(self):
        """Test 7: resolve_period() pour les 7 derniers jours"""
        today = date.today()
        seven_days_ago = today - __import__('datetime').timedelta(days=7)
        
        start, end, label = resolve_period("last_7_days")
        
        assert start == seven_days_ago.strftime("%Y-%m-%d")
        assert end == today.strftime("%Y-%m-%d")
        assert label == "les 7 derniers jours"
