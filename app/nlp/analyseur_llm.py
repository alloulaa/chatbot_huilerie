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
  "intention": "stock|production|machine|rendement|qualite|diagnostic|prediction|reception|campagne|inconnu",
  "confiance": nombre entre 0.0 et 1.0,
  "huilerie": "nom exact ou null",
  "periode": "aujourd_hui|hier|cette_semaine|semaine_derniere|ce_mois|mois_dernier|annee_2025|annee_2026|null",
  "type_huile": "vierge extra|vierge|lampante|null",
  "variete": "variete d'olive detectee ou null",
  "code_lot": "code de lot detecte ou null"
}

Huileries connues : Nour, Zitouneya, Sahel.

Regles de detection d'intention :
- stock / inventaire / olives / reserve / disponible / quantite  -> "stock"
- production / huile produite / litres / fabrication             -> "production"
- machine / panne / maintenance / equipement / broyeur           -> "machine"
- rendement / performance / taux d'extraction / efficacite       -> "rendement"
- qualite / analyse / acidite / peroxyde / laboratoire           -> "qualite"
- pourquoi mauvaise qualite / diagnostic / cause / probleme      -> "diagnostic"
- prediction / prevision / estimation / prevoir                  -> "prediction"
- reception / arrivage / pesee / livraison / fournisseur         -> "reception"
- campagne / saison / annee de campagne                          -> "campagne"
- Sinon                                                          -> "inconnu"

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
""".strip()


def _normaliser_resultat(resultat: dict) -> dict:
    intention = str(resultat.get("intention") or "inconnu").strip().lower()
    try:
        confiance = float(resultat.get("confiance", 0.5))
    except (TypeError, ValueError):
        confiance = 0.5

    if confiance < 0.0:
        confiance = 0.0
    if confiance > 1.0:
        confiance = 1.0

    return {
        "intention": intention,
        "confiance": confiance,
        "huilerie": resultat.get("huilerie"),
        "periode": resultat.get("periode"),
        "type_huile": resultat.get("type_huile"),
        "variete": resultat.get("variete"),
        "code_lot": resultat.get("code_lot"),
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
    """Repli minimal sur des regles simples si Grok est indisponible."""
    texte = message.lower().strip()
    intention = "inconnu"
    if any(m in texte for m in ["stock", "inventaire", "olive", "reserve", "quantite"]):
        intention = "stock"
    elif any(m in texte for m in ["production", "huile", "litre", "produit"]):
        intention = "production"
    elif any(m in texte for m in ["machine", "panne", "maintenance"]):
        intention = "machine"
    elif any(m in texte for m in ["rendement", "performance", "taux"]):
        intention = "rendement"
    elif any(m in texte for m in ["qualite", "acidite", "peroxyde"]):
        intention = "qualite"

    return {
        "intention": intention,
        "confiance": 0.4,
        "huilerie": None,
        "periode": None,
        "type_huile": None,
        "variete": None,
        "code_lot": None,
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
