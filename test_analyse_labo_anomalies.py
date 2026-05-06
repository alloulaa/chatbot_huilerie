import asyncio

from app.domain.chat import ChatQuery
from app.domain.intent import Intent
from app.services.intent.analyse_labo import AnalyseLaboHandler


class FakeService:
    def get_analyse_labo(self, huilerie, start_date, end_date, enterprise_id, lot_ref):
        return {
            "value": [
                {
                    "lot_ref": "LO06",
                    "date_analyse": "2026-05-06",
                    "acidite_huile_pourcent": 3.0,
                    "indice_peroxyde_meq_o2_kg": 8,
                    "k270": 0.2,
                    "k232": 2.0,
                    "polyphenols_mg_kg": 300,
                },
                {
                    "lot_ref": "LO01",
                    "date_analyse": "2026-05-04",
                    "acidite_huile_pourcent": 0.6,
                    "indice_peroxyde_meq_o2_kg": 8,
                    "k270": 0.18,
                    "k232": 2.1,
                    "polyphenols_mg_kg": 250,
                },
                {
                    "lot_ref": "LO99",
                    "date_analyse": "2026-05-03",
                    "acidite_huile_pourcent": 6.0,
                    "indice_peroxyde_meq_o2_kg": 8,
                    "k270": 0.18,
                    "k232": 2.1,
                    "polyphenols_mg_kg": 250,
                },
            ]
        }


def test_analyse_labo_filters_only_anormales_when_requested():
    service = FakeService()
    handler = AnalyseLaboHandler(service)
    query = ChatQuery(
        message="Y a-t-il des analyses anormales cette semaine ?",
        session_id="s1",
        intent=Intent.ANALYSE_LABO,
        confidence=0.9,
        huilerie=None,
        enterprise_id=12,
        permissions=[],
        period_label="cette_semaine",
        explicit_period=True,
        start_date="2026-05-01",
        end_date="2026-05-06",
        extra_context={},
    )

    result = asyncio.run(handler.handle(query))

    # With new thresholds (acidite > 0.8), both LO06 (3.0) and LO99 (6.0) are anomalous
    assert len(result.data) == 2
    assert result.data[0]["lot_ref"] == "LO06"
    assert result.data[1]["lot_ref"] == "LO99"
    assert "LO01" not in result.text  # LO01 (0.6) is normal, should not appear
    assert "LO06" in result.text
    assert "LO99" in result.text
