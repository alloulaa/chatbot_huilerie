"""
Implémentation Groq de l'analyseur NLP.
Renommé depuis analyseur_llm.py pour plus de clarté.
"""
import json
import logging
import os
import httpx
from dotenv import load_dotenv

from app.nlp.base import NLPAnalyzer
from app.domain.intent import NLPResult, Intent, Period


load_dotenv()
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", os.getenv("GROK_API_KEY", ""))
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

SYSTEM_PROMPT = """
Tu es un analyseur de langage naturel pour un systeme de gestion d'huilerie d'olive en Tunisie.
Analyse le message de l'utilisateur et retourne UNIQUEMENT un objet JSON valide.
Ne retourne rien d'autre que ce JSON.
Pas de texte avant, pas de texte apres, pas de balises markdown, pas de backticks.
Ne recopie jamais la question de l'utilisateur.
Ne fournis jamais d'explication, d'exemple ou de texte narratif.
Si une valeur est inconnue, utilise null.

Structure JSON attendue :
{
  "intention": "stock|production|machine|machines_utilisees|rendement|qualite|diagnostic|prediction|reception|campagne|fournisseur|lot_cycle_vie|lot_liste|analyse_labo|mouvement_stock|comparaison|explication|inconnu",
  "confiance": nombre entre 0.0 et 1.0,
  "huilerie": "nom exact ou null",
  "periode": "aujourd_hui|hier|cette_semaine|semaine_derniere|ce_mois|mois_dernier|annee_2025|annee_2026|null",
  "type_huile": "vierge extra|vierge|lampante|null",
  "variete": "variete d'olive detectee ou null",
  "code_lot": "reference du lot detecte (ex: LO07, LO08) ou null",
  "reference_lot": "reference du lot detecte (ex: LO07, LO08) ou null",
  "lot_reference": "reference du lot detecte (ex: LO07, LO08) ou null",
  "campagne_annee": "annee detectee pour la campagne (ex: 2025, 2025-2026) ou null"
}

Huileries connues : zitouneya, Moulin Sfax, Moulin Sousse, Moulin Artisanal.

================================================================================
REGLES CRITIQUES — À RESPECTER ABSOLUMENT :
================================================================================

PRIORITE 1 - STOCK (JAMAIS confondre avec fournisseur ou lot_liste) :
- Si le message contient : "stock" / "stock actuel" / "inventaire" / "quantite disponible" / "reserve"
  ET N'EXISTE PAS : "liste", "lots", "tracabilite" / "qui livre"
  → TOUJOURS "stock"

PRIORITE 2 - LOT_LISTE (quand on demande la LISTE des lots) :
- Si le message contient : "liste des lots" / "liste lot" / "tous les lots" / "lots recus" / "lots non conformes"
  → TOUJOURS "lot_liste"

PRIORITE 3 - FOURNISSEUR (SEULEMENT si parle explicitement de fournisseurs) :
- Si le message contient : "meilleur fournisseur" / "classement fournisseur" / "top fournisseur"
  / "qui livre" / "qui livre mieux" / "performance fournisseur" / "fournisseur le plus"
  ET EXISTE "stock" SEUL (pas "liste lot" ou "lots")
  → "fournisseur"
  Sinon si "stock" est present → TOUJOURS "stock"

PRIORITE 4 - COMPARAISON (questions comparatives entre plusieurs entités ou périodes) :
- Si le message contient une comparaison explicite entre plusieurs entités différentes ou une
  question sur "la meilleure/plus grande/plus petite" parmi des campagnes, huileries ou périodes :
  "quelle campagne a eu la plus grande production ?"
  "compare la campagne 2024 et 2025"
  "quelle huilerie produit le plus ?"
  "compare la production ce mois vs le mois dernier"
  "meilleure campagne en terme de rendement / olives"
  "compare les huileries"
  → TOUJOURS "comparaison"
  MAIS "quel est le meilleur fournisseur ?" sans comparer avec une autre entité → "fournisseur"

PRIORITE 5 - EXPLICATION (questions causales sur un lot SPECIFIQUE) :
- Si le message demande POURQUOI ou une EXPLICATION concernant un lot precis (avec reference) :
  "pourquoi la qualite du lot LO17 etait mauvaise ?"
  "explique-moi le lot LO07"
  "qu'est-ce qui a cause la mauvaise qualité du lot 3 ?"
  "pourquoi le lot LO05 a une acidite elevee ?"
  "analyse le lot LO12"
  → TOUJOURS "explication" ET extraire code_lot / reference_lot
  NE PAS confondre avec :
    - "lot_cycle_vie" (historique/timeline, pas d'explication causale)
    - "diagnostic"   (analyse agregee sur une periode, pas un lot precis)
    - "analyse_labo" (liste brute des resultats, pas d'explication)

Regles de detection d'intention (ordre respecte) :
- stock / inventaire / olives disponibles / reserve / quantite disponible    -> "stock" (SAUF si "lots"/"liste" present)
- production / huile produite / litres produits / fabrication / extraction   -> "production"
- machine / panne / maintenance / equipement / broyeur / etat machine        -> "machine"
- quelles machines utilisees / machine la plus utilisee / frequence machine
  / combien de fois machine / usage machine                                  -> "machines_utilisees"
- rendement / performance / taux d'extraction / efficacite                   -> "rendement"
- qualite / analyse / acidite / peroxyde / laboratoire / grade huile         -> "qualite"
- pourquoi mauvaise qualite / diagnostic / cause / probleme qualite          -> "diagnostic"
- prediction / prevision / estimation future / prevoir rendement             -> "prediction"
- reception / arrivage / pesee / livraison / bon de pesee                    -> "reception"
- campagne / saison / annee de campagne                                      -> "campagne"
- meilleur fournisseur / classement fournisseur / top fournisseur
  / qui livre mieux / qualite fournisseur / fournisseur le plus performant   -> "fournisseur"
  (SEULEMENT si "stock" seul n'est pas le keyword primaire)
- compare / comparaison / quelle campagne / quelle huilerie (superlative)
  / meilleure campagne / vs / versus / par rapport a                         -> "comparaison"
- pourquoi lot / explique lot / cause qualite lot / analyse lot (avec ref)   -> "explication"
- cycle de vie lot / historique lot / parcours lot / trajet lot
  / suivi lot / etapes du lot / que s'est-il passe pour le lot               -> "lot_cycle_vie"
- liste des lots / lots non conformes / tracabilite lots / tous les lots
  / lots recus / lots de la periode                                          -> "lot_liste"
- analyse laboratoire / resultats labo / k270 / k232 / polyphenols
  / indice peroxyde / acidite huile                                          -> "analyse_labo"
- mouvement stock / transfert stock / entree stock / sortie stock
  / ajustement stock / historique stock                                      -> "mouvement_stock"
- Sinon                                                                      -> "inconnu"

Regles de detection de periode :
- aujourd'hui / auj / ce jour              -> "aujourd_hui"
- hier                                     -> "hier"
- cette semaine / semaine en cours         -> "cette_semaine"
- semaine derniere / semaine passee        -> "semaine_derniere"
- ce mois / mois en cours / mois-ci        -> "ce_mois"
- mois dernier / mois passe                -> "mois_dernier"
- 2026 / cette annee                       -> "annee_2026"
- 2025 / annee derniere                    -> "annee_2025"
- Aucune periode mentionnee                -> null

Regles de detection de code_lot et reference_lot :
- Si le message contient LO07, LO08, lot 7, lot7, lot numero 7 -> extraire la reference (format LO + numero)
- Mettre la meme valeur dans "code_lot" et "reference_lot"

Regles de detection de campagne :
- Si le message contient une annee explicite apres campagne / saison / campagne olivicole -> l'exposer dans "campagne_annee"
- Exemples : "campagne 2025", "campagne 2025-2026", "saison 2024"
""".strip()


class GroqAnalyzer(NLPAnalyzer):
    """Analyseur NLP utilisant l'API Groq."""
    
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.url = GROQ_URL
        self.model = GROQ_MODEL
    
    async def analyze(self, message: str) -> NLPResult:
        """Analyser un message avec Groq API."""
        if not self.api_key:
            logger.warning("GROQ_API_KEY absent. Utilisation du fallback regex.")
            from app.nlp.regex_analyzer import RegexAnalyzer
            return await RegexAnalyzer().analyze(message)
        
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    self.url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 300,
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": message},
                        ],
                    },
                )
                response.raise_for_status()
                data = response.json()
                raw_text = data["choices"][0]["message"]["content"].strip()
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                result = json.loads(raw_text)
                
                if not isinstance(result, dict):
                    raise ValueError("Groq response is not a dict")
                
                return self._normalize_result(result)
                
        except Exception as error:
            logger.warning("Groq analysis failed: %s - falling back to regex", error)
            from app.nlp.regex_analyzer import RegexAnalyzer
            return await RegexAnalyzer().analyze(message)
    
    @staticmethod
    def _normalize_result(result: dict) -> NLPResult:
        """Normaliser la réponse Groq vers NLPResult."""
        import re
        
        intention_str = str(result.get("intention") or "inconnu").strip().lower()
        try:
            intention = Intent(intention_str)
        except ValueError:
            intention = Intent.INCONNU
        
        try:
            confidence = float(result.get("confiance", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))
        
        # Normaliser reference_lot
        ref_lot = result.get("reference_lot") or result.get("code_lot")
        if ref_lot:
            ref_lot = str(ref_lot).strip().upper()
            if re.match(r"^\d+$", ref_lot):
                ref_lot = f"LO{int(ref_lot):02d}"
            m = re.match(r"^LOT\s*(\d+)$", ref_lot)
            if m:
                ref_lot = f"LO{int(m.group(1)):02d}"
        
        period_str = result.get("periode")
        periode = None
        if period_str:
            try:
                periode = Period(period_str)
            except ValueError:
                periode = None
        
        return NLPResult(
            intention=intention,
            confiance=confidence,
            huilerie=result.get("huilerie"),
            periode=periode,
            type_huile=result.get("type_huile"),
            variete=result.get("variete"),
            code_lot=ref_lot,
            reference_lot=ref_lot,
            lot_reference=ref_lot,
            campagne_annee=result.get("campagne_annee"),
        )
