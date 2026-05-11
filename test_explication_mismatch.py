from app.services.intent.explication import _rule_based_explanation


def test_lo01_mismatch_detection():
    """Cas LO01 : analyses indiquent un grade acceptable mais le produit_final est enregistré 'lampante'.
    Le générateur rule-based doit signaler une incohérence et favoriser l'état observé en production.
    """
    lot_data = {
        "lot": {"reference": "LO01", "duree_stockage_jours": 3, "methode_recolte": "gaulage", "acidite_olives_pourcent": 2.0},
        "executions": [{
            "reference": "EP1",
            "temperature_malaxage": 27.0,
            "duree_malaxage_minutes": 50,
            "presence_ajout_eau": 1,
            "quantite_eau_ajoutee": 10,
            "date_debut": "2026-05-04",
        }],
        "analyses": [{
            "acidite_huile_pourcent": 1.5,
            "indice_peroxyde_meq_o2_kg": 10.0,
            "k270": 0.30,
            "k232": 1.8,
            "polyphenols_mg_kg": 50,
            "date_analyse": "2026-05-04"
        }],
        "production_outputs": [{
            "id_produit": 1,
            "reference": "PF01",
            "date_production": "2026-05-04",
            "nom_produit": "Huile Chemlali",
            "qualite": "lampante",
            "quantite_produite": 175,
            "execution_production_id": 1,
        }],
        "benchmark": {}
    }

    text = _rule_based_explanation(lot_data, "Pourquoi la qualité du lot LO01 est mauvaise ?")

    tl = text.lower()
    # Doit indiquer un jugement mauvaise et contenir les valeurs causales clés
    assert "est mauvaise" in tl or "mauvaise" in tl, "Le jugement final doit être 'mauvaise'"
    assert "délai de 3 jour" in tl, "Le résumé doit inclure le délai"
    assert "gaulage" in tl, "Le résumé doit inclure la méthode de récolte"
    assert "2.00 %" in text or "2,00 %" in text, "Le résumé doit inclure l'acidité des olives"
    assert "27.0" in text or "27,0" in text, "Le résumé doit inclure la température de malaxage"
    assert "50 min" in tl, "Le résumé doit inclure la durée de malaxage"
    assert "10 l" in tl, "Le résumé doit inclure l'ajout d'eau"


def test_lo14_uses_lot_specific_fields_and_method():
    """LO14: vérifier que les colonnes spécifiques du lot sont prises en compte dans l'explication."""
    lot_data = {
        "lot": {
            "reference": "LO14",
            "methode_recolte": "manuelle",
            "acidite_olives_pourcent": 2.0,
            "temps_depuis_recolte_heures": 70,
            "duree_stockage_jours": 0,
            "maturite": 4,
        },
        "executions": [{"reference": "EP14", "date_debut": "2026-05-11"}],
        "analyses": [{
            "acidite_huile_pourcent": 0.60,
            "indice_peroxyde_meq_o2_kg": 8.0,
            "k270": 0.180,
            "k232": 1.8,
            "polyphenols_mg_kg": 150,
            "date_analyse": "2026-05-11",
        }],
        "production_outputs": [{
            "id_produit": 2,
            "reference": "PF14",
            "date_production": "2026-05-11",
            "nom_produit": "Huile Chemlali",
            "qualite": "lampante",
            "quantite_produite": 175,
            "execution_production_id": 14,
        }],
        "benchmark": {},
    }

    text = _rule_based_explanation(lot_data, "pk la qualite de production de lot 14 est mauvaise")
    tl = text.lower()

    assert "lot lo14 est enregistré comme lampante" in tl
    assert "délai de 3 jour" in tl
    assert "récolte par manuelle" in tl
    assert "2.00 %" in text or "2,00 %" in text
    assert "éviter le gaulage" not in tl, "Ne pas recommander d'éviter le gaulage si la récolte est manuelle"
