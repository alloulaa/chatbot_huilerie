import json
import logging
import os

import httpx
from dotenv import load_dotenv


load_dotenv()
journaliseur = logging.getLogger(__name__)

CLE_API_GROQ = os.getenv("GROQ_API_KEY", os.getenv("GROK_API_KEY", ""))
URL_GROQ = "https://api.groq.com/openai/v1/chat/completions"
MODELE_GROQ = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

INVITE_SYSTEME = """
Tu es un analyseur de langage naturel pour un systeme de gestion d'huilerie d'olive en Tunisie.
Analyse le message de l'utilisateur et retourne UNIQUEMENT un objet JSON valide.
Ne retourne rien d'autre que ce JSON.
Pas de texte avant, pas de texte apres, pas de balises markdown, pas de backticks.
Ne recopie jamais la question de l'utilisateur.
Ne fournis jamais d'explication, d'exemple ou de texte narratif.
Si une valeur est inconnue, utilise null.

Structure JSON attendue :
{
  "intention": "stock|production|machine|machines_utilisees|rendement|qualite|diagnostic|prediction|reception|campagne|fournisseur|lot_cycle_vie|lot_liste|analyse_labo|mouvement_stock|inconnu",
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
  Exemples :
    "stock zitouneya" → "stock"
    "stock actuel" → "stock"
    "reserve d'olive" → "stock"
    "stock avec lots" → "lot_liste" (contains "lots")

PRIORITE 2 - LOT_LISTE (quand on demande la LISTE des lots) :
- Si le message contient : "liste des lots" / "liste lot" / "tous les lots" / "lots recus" / "lots non conformes"
  → TOUJOURS "lot_liste"
  Exemples :
    "liste des lots zitouneya" → "lot_liste"
    "tous les lots recus" → "lot_liste"

PRIORITE 3 - FOURNISSEUR (SEULEMENT si parle explicitement de fournisseurs) :
- Si le message contient : "meilleur fournisseur" / "classement fournisseur" / "top fournisseur"
  / "qui livre" / "qui livre mieux" / "performance fournisseur" / "fournisseur le plus"
  ET EXISTE "stock" SEUL (pas "liste lot" ou "lots")
  → "fournisseur"
  Sinon si "stock" est present → TOUJOURS "stock"
  Exemples :
    "meilleur fournisseur" → "fournisseur"
    "qui livre les meilleures olives" → "fournisseur"
    "stock du meilleur fournisseur" → "stock" (car le keyword primaire est "stock")

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


def _normaliser_resultat(resultat: dict) -> dict:
    intention = str(resultat.get("intention") or "inconnu").strip().lower()
    try:
        confiance = float(resultat.get("confiance", 0.5))
    except (TypeError, ValueError):
        confiance = 0.5

    confiance = max(0.0, min(1.0, confiance))

    # Normaliser reference_lot : "lot 7" -> "LO07", "lo8" -> "LO08"
    ref_lot = resultat.get("reference_lot") or resultat.get("code_lot")
    if ref_lot:
        import re
        ref_lot = str(ref_lot).strip().upper()
        # si c'est juste un numero : "7" -> "LO07"
        if re.match(r"^\d+$", ref_lot):
            ref_lot = f"LO{int(ref_lot):02d}"
        # si c'est "LOT7" ou "LOT07"
        m = re.match(r"^LOT\s*(\d+)$", ref_lot)
        if m:
            ref_lot = f"LO{int(m.group(1)):02d}"

    return {
        "intention": intention,
        "confiance": confiance,
        "huilerie": resultat.get("huilerie"),
        "periode": resultat.get("periode"),
        "type_huile": resultat.get("type_huile"),
        "variete": resultat.get("variete"),
        "code_lot": ref_lot,
        "reference_lot": ref_lot,
        "lot_reference": resultat.get("lot_reference") or ref_lot,
        "campagne_annee": resultat.get("campagne_annee"),
    }


async def analyser_message(message: str) -> dict:
    """Envoie le message a Groq et retourne les entites extraites sous forme de dict."""
    if not CLE_API_GROQ:
        journaliseur.warning("GROQ_API_KEY absente. Utilisation du repli local.")
        return _repli_regles(message)

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            reponse = await client.post(
                URL_GROQ,
                headers={
                    "Authorization": f"Bearer {CLE_API_GROQ}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODELE_GROQ,
                    "max_tokens": 300,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": INVITE_SYSTEME},
                        {"role": "user", "content": message},
                    ],
                },
            )
            reponse.raise_for_status()
            donnees = reponse.json()
            texte_brut = donnees["choices"][0]["message"]["content"].strip()
            texte_brut = texte_brut.replace("```json", "").replace("```", "").strip()
            resultat = json.loads(texte_brut)
            if not isinstance(resultat, dict):
                raise ValueError("Le JSON Groq n'est pas un objet")
            return _normaliser_resultat(resultat)
    except Exception as erreur:
        journaliseur.warning("Echec analyse Groq : %s - repli sur les regles simples", erreur)
        return _repli_regles(message)


def _repli_regles(message: str) -> dict:
    """Repli sur des regles simples si Groq est indisponible."""
    import re
    texte = message.lower().strip()
    intention = "inconnu"

    # ── Intents spécifiques EN PREMIER (avant stock/production génériques) ──

    if any(m in texte for m in [
        "meilleur fournisseur", "classement fournisseur", "top fournisseur",
        "fournisseur le plus", "qui livre", "performance fournisseur"
    ]):
        intention = "fournisseur"

    elif any(m in texte for m in [
        "cycle de vie", "historique lot", "parcours lot",
        "suivi lot", "etapes lot", "cycle lot"
    ]):
        intention = "lot_cycle_vie"

    elif any(m in texte for m in [
        "machines utilisees", "machine la plus utilisee",
        "usage machine", "frequence machine", "machines les plus"
    ]):
        intention = "machines_utilisees"

    elif any(m in texte for m in [
        "liste lot", "liste des lots", "lots non conformes",
        "tracabilite", "tous les lots", "lots de", "lots recus",
        "lots zitouneya", "lots huilerie", "lots moulin",
    ]):
        intention = "lot_liste"

    elif any(m in texte for m in [
        "analyse labo", "resultat labo", "k270", "k232",
        "polyphenol", "indice peroxyde", "analyses laboratoire"
    ]):
        intention = "analyse_labo"

    elif any(m in texte for m in [
        "mouvement stock", "transfert stock",
        "entree stock", "sortie stock", "historique stock"
    ]):
        intention = "mouvement_stock"

    # ── STOCK : mot "stock" SEUL ou avec huilerie, SANS "lot" dans la phrase ──
    elif (
        any(m in texte for m in ["stock", "inventaire", "quantite disponible", "reserve"])
        and not any(m in texte for m in ["liste lot", "lots", "tracabilite"])
    ):
        intention = "stock"

    elif any(m in texte for m in [
        "production", "huile produite", "litres produits", "fabrication"
    ]):
        intention = "production"

    elif any(m in texte for m in ["machine", "panne", "maintenance", "equipement"]):
        intention = "machine"

    elif any(m in texte for m in ["rendement", "performance", "taux extraction"]):
        intention = "rendement"

    elif any(m in texte for m in [
        "qualite", "acidite", "peroxyde", "grade huile"
    ]):
        intention = "qualite"

    elif any(m in texte for m in ["pourquoi", "diagnostic", "cause", "probleme qualite"]):
        intention = "diagnostic"

    elif any(m in texte for m in ["prediction", "prevision", "estimation future"]):
        intention = "prediction"

    elif any(m in texte for m in ["reception", "arrivage", "pesee", "livraison"]):
        intention = "reception"

    elif any(m in texte for m in ["campagne", "saison"]):
        intention = "campagne"

    # Extraction reference lot
    ref_lot = None
    campagne_annee = None
    m = re.search(r"\blo\s*(\d+)\b", texte)
    if m:
        ref_lot = f"LO{int(m.group(1)):02d}"
    else:
        m = re.search(r"\blot\s*(\d+)\b", texte)
        if m:
            ref_lot = f"LO{int(m.group(1)):02d}"

    if any(mot in texte for mot in ["campagne", "saison", "annee de campagne", "campagne olivicole"]):
        m = re.search(r"\b(20\d{2}(?:\s*-\s*20\d{2})?)\b", texte)
        if m:
            campagne_annee = re.sub(r"\s*[-/]\s*", "-", m.group(1)).strip()

    return {
        "intention": intention,
        "confiance": 0.4,
        "huilerie": None,
        "periode": None,
        "type_huile": None,
        "variete": None,
        "code_lot": ref_lot,
        "reference_lot": ref_lot,
        "lot_reference": ref_lot,
        "campagne_annee": campagne_annee,
    }


def analyser_message_sync(message: str) -> dict:
    """Version synchrone pour utilisation dans un controleur non-async."""
    import asyncio
    import concurrent.futures

    try:
        try:
            boucle = asyncio.get_event_loop()
        except RuntimeError:
            boucle = None

        if boucle and boucle.is_running():
            with concurrent.futures.ThreadPoolExecutor() as pool:
                futur = pool.submit(asyncio.run, analyser_message(message))
                return futur.result()

        return asyncio.run(analyser_message(message))
    except Exception as erreur:
        journaliseur.warning("Erreur analyse synchrone : %s - repli local", erreur)
        return _repli_regles(message)