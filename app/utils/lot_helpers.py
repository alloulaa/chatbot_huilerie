"""
Helpers utilitaires pour manipulation et formatage des données de lots.
"""
from typing import Any
import re


def _safe_float(value: Any, default: float = 0.0) -> float:
    """
    Convertit une valeur en float, retourne default si conversion impossible.
    
    Args:
        value: Valeur à convertir
        default: Valeur par défaut en cas d'erreur
    
    Returns:
        float : la valeur convertie ou default
    """
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _fmt(value: Any, decimals: int = 2) -> str:
    """
    Formate un nombre avec séparateur de milliers (espace) et décimales.
    
    Args:
        value: Valeur à formater
        decimals: Nombre de décimales (défaut 2)
    
    Returns:
        str : nombre formaté avec espaces comme séparateur de milliers
    """
    try:
        return f"{_safe_float(value):,.{decimals}f}".replace(",", " ")
    except Exception:
        return str(value or "N/D")


def _normalize_lot_reference(text: str | None) -> str | None:
    """
    Normalise une référence de lot vers le format standard LO##.
    
    Accepte :
    - LO01, LO02, etc. (déjà normalisé)
    - LOT 1, LOT 01, LOT 001
    - L 1, L 01
    - 1, 01, 001 (numéro simple)
    
    Args:
        text: Référence brute
    
    Returns:
        str : Référence normalisée (LO##) ou None si texte vide
    """
    if not text:
        return None
    t = str(text).strip().upper()
    if re.fullmatch(r"LO\d+", t):
        return f"LO{int(t[2:]):02d}"
    match = re.fullmatch(r"(?:LOT|L)\s*(\d+)", t)
    if match:
        return f"LO{int(match.group(1)):02d}"
    if re.fullmatch(r"\d+", t):
        return f"LO{int(t):02d}"
    return t


def _date_sort_key(value: Any) -> tuple[int, str]:
    """
    Crée une clé de tri pour dates (avec fallback pour valeurs vides).
    
    Args:
        value: Date (string ou autre) 
    
    Returns:
        tuple[int, str] : (0 ou 1 pour ordre, date_string_tronquée)
        Les dates vides sont classées en dernier (1, "")
    """
    text = str(value or "").strip()
    if not text:
        return (1, "")
    return (0, text[:19])


def _latest_by(items: list[dict], key: str) -> dict | None:
    """
    Retourne l'élément avec la date la plus récente (clé spécifiée).
    
    Args:
        items: Liste de dictionnaires
        key: Clé date à utiliser pour tri
    
    Returns:
        dict : dernier élément chronologiquement, ou None si liste vide
    """
    if not items:
        return None
    ordered = sorted(items, key=lambda item: _date_sort_key(item.get(key)))
    return ordered[-1] if ordered else None


def _first_by(items: list[dict], key: str) -> dict | None:
    """
    Retourne l'élément avec la date la plus ancienne (clé spécifiée).
    
    Args:
        items: Liste de dictionnaires
        key: Clé date à utiliser pour tri
    
    Returns:
        dict : premier élément chronologiquement, ou None si liste vide
    """
    if not items:
        return None
    ordered = sorted(items, key=lambda item: _date_sort_key(item.get(key)))
    return ordered[0] if ordered else None


def _parse_boolish(value: Any) -> bool:
    """
    Parse une valeur "boolish" (1/0, true/false, yes/no, oui/non, on/off).
    
    Args:
        value: Valeur à interpréter comme booléen
    
    Returns:
        bool : True si la valeur represente un "oui", False sinon
    """
    return str(value).strip().lower() in {"1", "true", "yes", "oui", "on"}
