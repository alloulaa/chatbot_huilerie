from typing import Tuple

INTENT_PATTERNS = [
    ("diagnostic", ["pourquoi", "qualité", "qualite", "mauvaise"]),
    ("prediction", ["prediction", "prévision", "prevision", "prévu", "prevu"]),
    ("qualite", ["qualité", "qualite"]),
    ("machine", ["machine", "panne", "probleme", "problème", "maintenance", "surveillance"]),
    ("rendement", ["rendement", "performance"]),
    ("stock", ["stock", "olive", "olives", "matiere", "matière"]),
    ("production", ["production", "huile", "produit"]),
]


def detect_intent(message: str) -> Tuple[str, float]:
    text = message.lower().strip()

    best_intent = "unknown"
    best_score = 0

    for intent, keywords in INTENT_PATTERNS:
        score = sum(1 for keyword in keywords if keyword in text)

        if intent == "diagnostic":
            # Keep diagnostic for explicit root-cause questions and avoid
            # shadowing standard quality intent.
            if score < 2 and "pourquoi" not in text:
                continue

        if score > best_score:
            best_intent = intent
            best_score = score

    if best_score == 0:
        return "unknown", 0.3

    confidence = min(0.6 + 0.1 * best_score, 0.95)
    return best_intent, confidence
