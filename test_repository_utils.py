from app.utils.shared import (
    fmt_number,
    is_chart_request,
    normalize_choice,
    normalize_quality_label,
    safe_float,
    scope_text,
)


def test_shared_helpers_cover_common_normalization_cases():
    assert safe_float("12.5") == 12.5
    assert safe_float(None, 3.0) == 3.0
    assert normalize_quality_label("Bon") == "Bonne"
    assert normalize_quality_label("médiocre") == "Mauvaise"
    assert normalize_choice("graphique") == "graphique"
    assert is_chart_request("Peux-tu faire un histogramme ?") is True
    assert scope_text("H1", "aujourd'hui") == "de l'huilerie **H1** pour aujourd'hui"
    assert fmt_number(1234.5, 1) == "1 234.5"
