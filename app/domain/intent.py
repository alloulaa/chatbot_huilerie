"""
Enums et types pour les intents du chatbot.
"""
from enum import Enum
from typing import NamedTuple


class Intent(str, Enum):
    """Énumération de tous les intents supportés."""
    STOCK = "stock"
    PRODUCTION = "production"
    MACHINE = "machine"
    MACHINES_UTILISEES = "machines_utilisees"
    RENDEMENT = "rendement"
    QUALITE = "qualite"
    DIAGNOSTIC = "diagnostic"
    PREDICTION = "prediction"
    RECEPTION = "reception"
    CAMPAGNE = "campagne"
    FOURNISSEUR = "fournisseur"
    LOT_CYCLE_VIE = "lot_cycle_vie"
    LOT_LISTE = "lot_liste"
    ANALYSE_LABO = "analyse_labo"
    MOUVEMENT_STOCK = "mouvement_stock"
    COMPARAISON = "comparaison"
    EXPLICATION = "explication"
    INCONNU = "inconnu"


class Period(str, Enum):
    """Énumération des périodes supportées."""
    AUJOURD_HUI = "aujourd_hui"
    HIER = "hier"
    CETTE_SEMAINE = "cette_semaine"
    SEMAINE_DERNIERE = "semaine_derniere"
    CE_MOIS = "ce_mois"
    MOIS_DERNIER = "mois_dernier"
    ANNEE_2025 = "annee_2025"
    ANNEE_2026 = "annee_2026"


class NLPResult(NamedTuple):
    """Résultat d'analyse NLP."""
    intention: Intent
    confiance: float
    huilerie: str | None
    periode: Period | None
    type_huile: str | None
    variete: str | None
    code_lot: str | None
    reference_lot: str | None
    lot_reference: str | None
    campagne_annee: str | None


# Intents avec période explicite
RANKING_INTENTS = {
    Intent.STOCK,
    Intent.MACHINES_UTILISEES,
    Intent.LOT_LISTE,
    Intent.ANALYSE_LABO,
    Intent.FOURNISSEUR,
}

# Intents qui supportent le filtrage par date
TIME_FILTERED_INTENTS = {
    Intent.PRODUCTION,
    Intent.RENDEMENT,
    Intent.QUALITE,
    Intent.FOURNISSEUR,
    Intent.LOT_LISTE,
    Intent.MACHINES_UTILISEES,
    Intent.RECEPTION,
}
