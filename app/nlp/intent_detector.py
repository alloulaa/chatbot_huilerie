from typing import Tuple

INTENT_PATTERNS = [
    ("stock", ["stock"]),
    ("production", ["production"]),
    ("machines", ["machine", "panne", "probleme", "problème"]),
    ("rendement", ["rendement"]),
]


def detect_intent(message: str) -> Tuple[str, float]:
    text = message.lower().strip()
    for intent, keywords in INTENT_PATTERNS:
        for keyword in keywords:
            if keyword in text:
                return intent, 0.9
    return "demande_precision", 0.3
