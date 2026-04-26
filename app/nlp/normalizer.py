from datetime import date, timedelta

TODAY = date(2026, 4, 17)


def resolve_period(label: str | None):
    label = label or "today"
    if label == "today":
        return "2026-04-17", "2026-04-17", "aujourd'hui"
    if label == "yesterday":
        return "2026-04-16", "2026-04-16", "hier"
    if label == "this_week":
        return "2026-04-11", "2026-04-17", "cette semaine"
    if label == "last_week":
        return "2026-04-04", "2026-04-10", "la semaine dernière"
    if label == "this_month":
        return "2026-04-01", "2026-04-17", "ce mois-ci"
    if label == "march_2026":
        return "2026-03-01", "2026-03-31", "mars 2026"
    if label == "april_2026":
        return "2026-04-01", "2026-04-30", "avril 2026"
    return "2026-04-17", "2026-04-17", "aujourd'hui"
