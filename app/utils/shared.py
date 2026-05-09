from __future__ import annotations

from typing import Any


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    return safe_float(value, default)


def normalize_quality_label(value: Any) -> str:
    text = str(value).strip().lower() if value is not None else ""
    if text in {
        "bonne",
        "bon",
        "bonne qualite",
        "bonne qualité",
        "excellente",
        "excellent",
        "extra",
        "top",
        "a",
    }:
        return "Bonne"
    if text in {"moyenne", "moyen", "acceptable", "standard", "b"}:
        return "Moyenne"
    if text in {
        "mauvaise",
        "mauvais",
        "faible",
        "mediocre",
        "médiocre",
        "non conforme",
        "c",
    }:
        return "Mauvaise"
    return "Inconnue"


def fmt_number(value: float | int | None, decimals: int = 0) -> str:
    number = float(value or 0)
    return f"{number:,.{decimals}f}".replace(",", " ")


def scope_text(
    huilerie: str | None, period_text: str, enterprise_scoped: bool = False
) -> str:
    if huilerie:
        return f"de l'huilerie **{huilerie}** pour {period_text}"
    if enterprise_scoped:
        return f"pour {period_text} (toutes vos huileries)"
    return f"pour {period_text} (toutes huileries)"


def is_chart_request(message: str) -> bool:
    texte = message.lower()
    return any(
        mot in texte
        for mot in (
            "graphique",
            "chart",
            "diagramme",
            "courbe",
            "histogramme",
            "visualisation",
        )
    )


def normalize_choice(message: str) -> str | None:
    texte = message.strip().lower()
    if texte in {"texte", "text", "résumé", "resume"}:
        return "texte"
    if texte in {"graphique", "chart", "diagramme", "courbe", "barre", "bar"}:
        return "graphique"
    return None
