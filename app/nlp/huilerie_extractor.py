import logging
import re
import unicodedata
from typing import Any

from app.database import get_db_connection

logger = logging.getLogger(__name__)

_STATIC_HUILERIES = [
    "zitouneya",
    "moulin sfax",
    "moulin sousse",
    "moulin artisanal",
]

_HUILERIE_CACHE: list[str] | None = None


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.lower().split())


def _load_known_huileries() -> list[str]:
    global _HUILERIE_CACHE
    if _HUILERIE_CACHE is not None:
        return _HUILERIE_CACHE

    huileries: list[str] = []
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT nom FROM huilerie")
        rows = cursor.fetchall() or []
        for row in rows:
            if isinstance(row, tuple):
                name = row[0]
            elif isinstance(row, dict):
                name = row.get("nom")
            else:
                name = str(row)
            if name:
                huileries.append(str(name).strip())
    except Exception as exc:
        logger.warning("Unable to load huilerie names from database: %s", exc)
    finally:
        try:
            if cursor is not None:
                cursor.close()
        except NameError:
            pass
        try:
            if connection is not None and connection.is_connected():
                connection.close()
        except NameError:
            pass

    if not huileries:
        huileries = _STATIC_HUILERIES

    _HUILERIE_CACHE = huileries
    return _HUILERIE_CACHE


def extract_huilerie_from_text(text: str) -> str | None:
    normalized_text = _normalize_text(text)
    for huilerie_name in _load_known_huileries():
        if not huilerie_name:
            continue
        normalized_name = _normalize_text(huilerie_name)
        if re.search(rf"\b{re.escape(normalized_name)}\b", normalized_text):
            return huilerie_name
    return None
