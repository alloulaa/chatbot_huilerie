#!/usr/bin/env python3
"""Debug NLP detection for lot explication"""
from app.nlp import analyser_message_sync

messages = [
    "Pourquoi le lot LO16 a une mauvaise qualité ?",
    "Pourquoi le lot LO16 a une qualité mauvaise",
    "Explique pourquoi LO16 est lampante",
    "Pourquoi le lot LO07 est mauvais ?",
]

print("=== NLP Intent Detection ===\n")
for msg in messages:
    result = analyser_message_sync(msg)
    intent = result.get("intention", "inconnu")
    confiance = result.get("confiance", 0.0)
    print(f"Message: {msg}")
    print(f"  Intent: {intent} (confiance: {confiance})")
    print(f"  code_lot: {result.get('code_lot')}, reference_lot: {result.get('reference_lot')}")
    print()
