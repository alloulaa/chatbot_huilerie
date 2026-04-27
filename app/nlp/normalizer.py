import calendar
from datetime import date, timedelta


MONTH_NAMES_FR = {
    1: "janvier",
    2: "fevrier",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "aout",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "decembre",
}


def _fmt(value: date) -> str:
    return value.strftime("%Y-%m-%d")


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def resolve_period(label: str | None) -> tuple[str, str, str]:
    today = date.today()
    normalized = (label or "aujourd_hui").lower()

    if normalized in {"aujourd_hui", "today"}:
        return _fmt(today), _fmt(today), "aujourd'hui"

    if normalized in {"hier", "yesterday"}:
        yesterday = today - timedelta(days=1)
        return _fmt(yesterday), _fmt(yesterday), "hier"

    if normalized in {"cette_semaine", "this_week"}:
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return _fmt(start), _fmt(end), "cette semaine"

    if normalized in {"semaine_derniere", "last_week"}:
        this_week_start = today - timedelta(days=today.weekday())
        end = this_week_start - timedelta(days=1)
        start = end - timedelta(days=6)
        return _fmt(start), _fmt(end), "la semaine derniere"

    if normalized in {"ce_mois", "this_month"}:
        start = date(today.year, today.month, 1)
        _, end = _month_bounds(today.year, today.month)
        return _fmt(start), _fmt(end), "ce mois-ci"

    if normalized in {"mois_dernier", "last_month"}:
        year = today.year
        month = today.month - 1
        if month == 0:
            month = 12
            year -= 1
        start, end = _month_bounds(year, month)
        return _fmt(start), _fmt(end), "le mois dernier"

    if normalized == "annee_2026":
        return "2026-01-01", "2026-12-31", "en 2026"

    if normalized == "annee_2025":
        return "2025-01-01", "2025-12-31", "en 2025"

    if normalized == "last_7_days":
        start = today - timedelta(days=7)
        return _fmt(start), _fmt(today), "les 7 derniers jours"

    if normalized == "last_30_days":
        start = today - timedelta(days=30)
        return _fmt(start), _fmt(today), "les 30 derniers jours"

    if normalized.startswith("month_"):
        # format: month_YYYY_MM
        parts = normalized.split("_")
        if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            year = int(parts[1])
            month = int(parts[2])
            if 1 <= month <= 12:
                start, end = _month_bounds(year, month)
                return _fmt(start), _fmt(end), f"{MONTH_NAMES_FR[month]} {year}"

    if normalized.startswith("year_"):
        # format: year_YYYY
        year_text = normalized.split("_", 1)[1]
        if year_text.isdigit():
            year = int(year_text)
            return f"{year}-01-01", f"{year}-12-31", f"{year}"

    if normalized.startswith("annee_"):
        year_text = normalized.split("_", 1)[1]
        if year_text.isdigit():
            year = int(year_text)
            return f"{year}-01-01", f"{year}-12-31", f"en {year}"

    if normalized.startswith("custom_range_"):
        # format: custom_range_YYYY-MM-DD_YYYY-MM-DD
        parts = normalized.split("_")
        if len(parts) >= 4:
            start = parts[2]
            end = parts[3]
            return start, end, f"du {start} au {end}"

    return _fmt(today), _fmt(today), "aujourd'hui"
