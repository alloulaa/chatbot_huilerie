"""
Analyseur NLP par expressions régulières.
Implémentation du fallback quand Groq n'est pas disponible.
"""
import re
import logging
from app.nlp.base import NLPAnalyzer
from app.domain.intent import NLPResult, Intent, Period

logger = logging.getLogger(__name__)


class RegexAnalyzer(NLPAnalyzer):
    """Analyseur NLP basé sur des règles regex simples."""
    
    async def analyze(self, message: str) -> NLPResult:
        """Analyser un message avec des règles regex."""
        return self._apply_rules(message)
    
    @staticmethod
    def _apply_rules(message: str) -> NLPResult:
        """Appliquer les règles regex pour détecter l'intention."""
        import re
        texte = message.lower().strip()
        intention = Intent.INCONNU
        
        # --- EXPLICATION (avant diagnostic et lot_cycle_vie) ---
        # Doit avoir un mot causal/explicatif ET une référence de lot
        has_lot_ref = bool(re.search(r"\blo\s*\d+\b|\blot\s*\d+\b", texte))
        has_causal = any(m in texte for m in [
            "pourquoi", "explique", "expliquer", "cause", "raison",
            "qu'est-ce qui", "qu est-ce qui", "analyser", "analyse le lot",
            "comment expliquer",
        ])
        if has_lot_ref and has_causal:
            intention = Intent.EXPLICATION
        
        # --- COMPARAISON (avant campagne et fournisseur) ---
        elif any(m in texte for m in [
            "compare", "comparaison", "comparer",
            "quelle campagne", "quelle huilerie",
            "meilleure campagne", "la plus grande production",
            "le plus de production", "le plus produit",
            " vs ", " versus ", "par rapport",
            "huilerie la plus", "campagne la plus",
        ]):
            intention = Intent.COMPARAISON
        
        # Intents spécifiques EN PREMIER (avant stock/production génériques)
        if any(m in texte for m in [
            "meilleur fournisseur", "classement fournisseur", "top fournisseur",
            "fournisseur le plus", "qui livre", "performance fournisseur"
        ]):
            intention = Intent.FOURNISSEUR
        
        elif any(m in texte for m in [
            "cycle de vie", "historique lot", "parcours lot",
            "suivi lot", "etapes lot", "cycle lot"
        ]):
            intention = Intent.LOT_CYCLE_VIE
        
        elif any(m in texte for m in [
            "machines utilisees", "machine la plus utilisee",
            "usage machine", "frequence machine", "machines les plus"
        ]):
            intention = Intent.MACHINES_UTILISEES
        
        elif any(m in texte for m in [
            "liste lot", "liste des lots", "lots non conformes",
            "tracabilite", "tous les lots", "lots de", "lots recus",
            "lots zitouneya", "lots huilerie", "lots moulin",
        ]):
            intention = Intent.LOT_LISTE
        
        elif any(m in texte for m in [
            "analyse labo", "resultat labo", "k270", "k232",
            "polyphenol", "indice peroxyde", "analyses laboratoire"
        ]):
            intention = Intent.ANALYSE_LABO
        
        elif any(m in texte for m in [
            "mouvement stock", "transfert stock",
            "entree stock", "sortie stock", "historique stock"
        ]):
            intention = Intent.MOUVEMENT_STOCK
        
        elif (
            any(m in texte for m in ["stock", "inventaire", "quantite disponible", "reserve"])
            and not any(m in texte for m in ["liste lot", "lots", "tracabilite"])
        ):
            intention = Intent.STOCK
        
        elif any(m in texte for m in [
            "production", "huile produite", "litres produits", "fabrication"
        ]):
            intention = Intent.PRODUCTION
        
        elif any(m in texte for m in ["machine", "panne", "maintenance", "equipement"]):
            intention = Intent.MACHINE
        
        elif any(m in texte for m in ["rendement", "performance", "taux extraction"]):
            intention = Intent.RENDEMENT
        
        elif any(m in texte for m in [
            "qualite", "acidite", "peroxyde", "grade huile"
        ]):
            intention = Intent.QUALITE
        
        elif any(m in texte for m in ["pourquoi", "diagnostic", "cause", "probleme qualite"]):
            intention = Intent.DIAGNOSTIC
        
        elif any(m in texte for m in ["prediction", "prevision", "estimation future"]):
            intention = Intent.PREDICTION
        
        elif any(m in texte for m in ["reception", "arrivage", "pesee", "livraison"]):
            intention = Intent.RECEPTION
        
        elif any(m in texte for m in ["campagne", "saison"]):
            intention = Intent.CAMPAGNE
        
        # Extraction reference lot
        ref_lot = None
        m = re.search(r"\blo\s*(\d+)\b", texte)
        if m:
            ref_lot = f"LO{int(m.group(1)):02d}"
        else:
            m = re.search(r"\blot\s*(\d+)\b", texte)
            if m:
                ref_lot = f"LO{int(m.group(1)):02d}"
        
        # Extraction période
        periode = None
        if any(w in texte for w in ["aujourd", "auj", "ce jour"]):
            periode = Period.AUJOURD_HUI
        elif "hier" in texte:
            periode = Period.HIER
        elif any(w in texte for w in ["cette semaine", "semaine en cours"]):
            periode = Period.CETTE_SEMAINE
        elif any(w in texte for w in ["semaine derniere", "semaine passee"]):
            periode = Period.SEMAINE_DERNIERE
        elif any(w in texte for w in ["ce mois", "mois en cours", "mois-ci"]):
            periode = Period.CE_MOIS
        elif any(w in texte for w in ["mois dernier", "mois passe"]):
            periode = Period.MOIS_DERNIER
        elif "2026" in texte or "cette annee" in texte:
            periode = Period.ANNEE_2026
        elif "2025" in texte or "annee derniere" in texte:
            periode = Period.ANNEE_2025
        
        # Extraction campagne
        campagne_annee = None
        if any(mot in texte for mot in ["campagne", "saison", "annee de campagne", "campagne olivicole"]):
            m = re.search(r"\b(20\d{2}(?:\s*-\s*20\d{2})?)\b", texte)
            if m:
                campagne_annee = re.sub(r"\s*[-/]\s*", "-", m.group(1)).strip()
        
        return NLPResult(
            intention=intention,
            confiance=0.4,
            huilerie=None,
            periode=periode,
            type_huile=None,
            variete=None,
            code_lot=ref_lot,
            reference_lot=ref_lot,
            lot_reference=ref_lot,
            campagne_annee=campagne_annee,
        )
