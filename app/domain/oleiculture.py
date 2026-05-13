"""
Domaine agronomique et seuils normatifs (COI/IOC).
Données de référence sur les variétés tunisiennes et les standards de qualité.
"""

# Seuils COI pour la classification des huiles
SEUILS_VIERGE_EXTRA = {
    "acidite_huile_pourcent":        {"min": 0.0,  "max": 0.8,  "label": "Acidité libre (%)"},
    "indice_peroxyde_meq_o2_kg":    {"min": 0.0,  "max": 20.0, "label": "Indice de peroxyde (meq O₂/kg)"},
    "k270":                          {"min": 0.0,  "max": 0.22, "label": "K270"},
    "k232":                          {"min": 1.5,  "max": 2.50, "label": "K232"},
    "polyphenols_mg_kg":             {"min": 100.0,"max": 800.0,"label": "Polyphénols (mg/kg)"},
}

SEUILS_VIERGE = {
    "acidite_huile_pourcent":        {"min": 0.0,  "max": 2.0},
    "indice_peroxyde_meq_o2_kg":    {"min": 0.0,  "max": 20.0},
    "k270":                          {"min": 0.0,  "max": 0.25},
}

# Connaissance agronomique : variétés tunisiennes et leur profil
VARIETES_PROFIL = {
    "chemlali":  {"acidite_naturelle": "faible", "polyphenols": "élevés", "sensibilite_gel": "haute",   "maturite_optimale": "tard"},
    "chétoui":   {"acidite_naturelle": "faible", "polyphenols": "très élevés", "sensibilite_gel": "moyenne", "maturite_optimale": "tôt"},
    "oueslati":  {"acidite_naturelle": "moyenne","polyphenols": "moyens",  "sensibilite_gel": "basse",  "maturite_optimale": "milieu"},
    "sayali":    {"acidite_naturelle": "faible", "polyphenols": "moyens",  "sensibilite_gel": "haute",  "maturite_optimale": "tard"},
    "gerboui":   {"acidite_naturelle": "moyenne","polyphenols": "faibles", "sensibilite_gel": "basse",  "maturite_optimale": "tôt"},
    "arbequina": {"acidite_naturelle": "faible", "polyphenols": "faibles", "sensibilite_gel": "moyenne","maturite_optimale": "tôt"},
    "koroneiki": {"acidite_naturelle": "faible", "polyphenols": "très élevés","sensibilite_gel": "haute","maturite_optimale": "tôt"},
}


def _grade_huile(acid: float, perox: float, k270: float) -> str:
    """
    Calcule le grade COI (Conseil Oléicole International) d'une huile d'olive
    basé sur ses paramètres analytiques.
    
    Args:
        acid: Acidité libre en %
        perox: Indice de peroxyde en meq O₂/kg
        k270: Absorption à 270 nm
    
    Returns:
        Grade COI : "Vierge Extra", "Vierge", "Vierge Courante", ou "Lampante"
    """
    if acid <= 0.8 and perox <= 20 and k270 <= 0.22:
        return "Vierge Extra"
    if acid <= 2.0 and perox <= 20 and k270 <= 0.25:
        return "Vierge"
    if acid <= 3.3:
        return "Vierge Courante"
    return "Lampante (non comestible brut)"


def _get_variete_profil(variete: str | None) -> dict:
    """
    Retrouve le profil agronomique d'une variété d'olive.
    
    Args:
        variete: Nom de la variété (sensible à la casse partiellement)
    
    Returns:
        Dictionnaire contenant acidité naturelle, polyphénols, sensibilité au gel, maturité optimale.
        Retourne {} si la variété n'est pas reconnue.
    """
    if not variete:
        return {}
    v = variete.strip().lower()
    for key, profil in VARIETES_PROFIL.items():
        if key in v or v in key:
            return profil
    return {}
