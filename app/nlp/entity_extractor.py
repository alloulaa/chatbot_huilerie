import re
import unicodedata
from datetime import date
from typing import Any
from app.repositories.huilerie_repository import HuilerieRepository


class EntityExtractor:
    def __init__(self):
        self.huilerie_repo = HuilerieRepository()

    def extract(self, message: str) -> dict[str, Any]:
        text = message.lower()
        text_ascii = self._strip_accents(text)
        entities: dict[str, Any] = {}

        for name in self.huilerie_repo.list_names():
            if self._strip_accents(name.lower()) in text_ascii:
                entities["huilerie"] = name
                break

        if "huilerie" not in entities:
            huilerie_match = re.search(r"\bhuilerie\s+([a-z0-9_-]+)", text_ascii)
            if huilerie_match:
                entities["huilerie"] = huilerie_match.group(1)

        machine_match = re.search(r"\b(m\d+)\b", text, re.IGNORECASE)
        if machine_match:
            entities["machine"] = machine_match.group(1).upper()

        lot_match = re.search(r"\b([lsz]\d{3})\b", text, re.IGNORECASE)
        if lot_match:
            entities["lot_code"] = lot_match.group(1).upper()

        if "vierge extra" in text:
            entities["type_huile"] = "vierge extra"
        elif re.search(r"\bvierge\b", text):
            entities["type_huile"] = "vierge"

        period_label = self._extract_period_label(text_ascii)
        if period_label:
            entities["period_label"] = period_label

        return entities

    @staticmethod
    def _strip_accents(value: str) -> str:
        normalized = unicodedata.normalize("NFD", value)
        return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")

    def _extract_period_label(self, text_ascii: str) -> str | None:
        current_year = date.today().year

        month_names = {
            "janvier": 1,
            "fevrier": 2,
            "mars": 3,
            "avril": 4,
            "mai": 5,
            "juin": 6,
            "juillet": 7,
            "aout": 8,
            "septembre": 9,
            "octobre": 10,
            "novembre": 11,
            "decembre": 12,
        }

        # Custom range: du 01/03 au 15/03 (year assumed current year)
        range_match = re.search(r"du\s+(\d{2})[/-](\d{2})\s+au\s+(\d{2})[/-](\d{2})", text_ascii)
        if range_match:
            d1, m1, d2, m2 = range_match.groups()
            start = f"{current_year}-{int(m1):02d}-{int(d1):02d}"
            end = f"{current_year}-{int(m2):02d}-{int(d2):02d}"
            return f"custom_range_{start}_{end}"

        # month/year: 03/2026 or 3-2026
        month_year_match = re.search(r"\b(\d{1,2})[/-](\d{4})\b", text_ascii)
        if month_year_match:
            month = int(month_year_match.group(1))
            year = int(month_year_match.group(2))
            if 1 <= month <= 12:
                return f"month_{year}_{month:02d}"

        # Named month with optional year: mars or mars 2026
        month_pattern = "|".join(month_names.keys())
        month_match = re.search(rf"\b({month_pattern})(?:\s+(\d{{4}}))?\b", text_ascii)
        if month_match:
            month = month_names[month_match.group(1)]
            year = int(month_match.group(2)) if month_match.group(2) else current_year
            return f"month_{year}_{month:02d}"

        if "aujourd" in text_ascii or re.search(r"\bauj\b", text_ascii):
            return "today"
        if "hier" in text_ascii:
            return "yesterday"
        if "cette semaine" in text_ascii or "semaine en cours" in text_ascii:
            return "this_week"
        if "semaine derniere" in text_ascii or "semaine precedente" in text_ascii:
            return "last_week"
        if "ce mois" in text_ascii or "mois en cours" in text_ascii:
            return "this_month"
        if "mois dernier" in text_ascii:
            return "last_month"
        if "cette annee" in text_ascii:
            return f"year_{current_year}"
        if "7 derniers jours" in text_ascii or "7 dernier jours" in text_ascii:
            return "last_7_days"
        if "30 derniers jours" in text_ascii or "30 dernier jours" in text_ascii:
            return "last_30_days"

        year_match = re.search(r"\b(20\d{2})\b", text_ascii)
        if year_match:
            return f"year_{year_match.group(1)}"

        return None
