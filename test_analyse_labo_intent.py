import asyncio

from app.domain.chat import ChatQuery
from app.domain.intent import Intent
from app.nlp.regex_analyzer import RegexAnalyzer
from app.services.intent.analyse_labo import AnalyseLaboHandler


class FakeService:
    def __init__(self):
        self.calls = []

    def get_analyse_labo(self, huilerie, start_date, end_date, enterprise_id, lot_ref):
        self.calls.append((huilerie, start_date, end_date, enterprise_id, lot_ref))
        return {
            "value": [
                {
                    "lot_ref": lot_ref or "LO99",
                    "date_analyse": "2026-05-04",
                    "acidite_huile_pourcent": 6.0,
                    "indice_peroxyde_meq_o2_kg": 8,
                    "k270": 0.18,
                    "k232": 2.1,
                    "polyphenols_mg_kg": 250,
                },
                {
                    "lot_ref": "LO01",
                    "date_analyse": "2026-05-03",
                    "acidite_huile_pourcent": 0.6,
                    "indice_peroxyde_meq_o2_kg": 8,
                    "k270": 0.18,
                    "k232": 2.1,
                    "polyphenols_mg_kg": 250,
                }
            ]
        }


def test_regex_analyzer_routes_lab_results_questions_to_analyse_labo():
    result_1 = RegexAnalyzer._apply_rules("Quels sont les derniers résultats d'analyse pour le lot LO01 ?")
    result_2 = RegexAnalyzer._apply_rules("Acidité et peroxyde du lot LO01")

    assert result_1.intention is Intent.ANALYSE_LABO
    assert result_2.intention is Intent.ANALYSE_LABO


def test_analyse_labo_handler_keeps_only_anormales_for_lot_queries():
    service = FakeService()
    handler = AnalyseLaboHandler(service)
    query = ChatQuery(
        message="Quels sont les derniers résultats d'analyse pour le lot LO01 ?",
        session_id="s1",
        intent=Intent.ANALYSE_LABO,
        confidence=0.9,
        huilerie=None,
        enterprise_id=12,
        permissions=[],
        period_label=None,
        explicit_period=False,
        start_date="2026-05-06",
        end_date="2026-05-06",
        extra_context={"lot_reference": "LO01"},
    )

    result = asyncio.run(handler.handle(query))

    assert service.calls == [(None, None, None, 12, "LO01")]
    assert result.text.startswith("Analyses laboratoires")
    assert len(result.data) == 1
    assert result.data[0]["lot_ref"] == "LO01"
