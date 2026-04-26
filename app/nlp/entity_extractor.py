import re
from typing import Any
from app.repositories.huilerie_repository import HuilerieRepository


class EntityExtractor:
    def __init__(self):
        self.huilerie_repo = HuilerieRepository()

    def extract(self, message: str) -> dict[str, Any]:
        text = message.lower()
        entities: dict[str, Any] = {}

        for name in self.huilerie_repo.list_names():
            if name.lower() in text:
                entities["huilerie"] = name
                break

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

        if "semaine dernière" in text or "semaine derniere" in text:
            entities["period_label"] = "last_week"
        elif "cette semaine" in text:
            entities["period_label"] = "this_week"
        elif "ce mois" in text:
            entities["period_label"] = "this_month"
        elif "aujourd" in text:
            entities["period_label"] = "today"
        elif "hier" in text:
            entities["period_label"] = "yesterday"
        elif "mars 2026" in text:
            entities["period_label"] = "march_2026"
        elif "avril 2026" in text:
            entities["period_label"] = "april_2026"

        return entities
