import httpx
import os

from dotenv import load_dotenv
from app.nlp.analyseur_llm import INVITE_SYSTEME


load_dotenv()

reponse = httpx.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY', os.getenv('GROK_API_KEY', ''))}",
        "Content-Type": "application/json",
    },
    json={
        "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        "max_tokens": 200,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": INVITE_SYSTEME},
            {"role": "user", "content": "stock huilerie nour cette semaine"},
        ],
    },
)

print("Statut :", reponse.status_code)
donnees = reponse.json()
if reponse.status_code == 200 and donnees.get("choices"):
    print("Reponse :", donnees["choices"][0]["message"]["content"])
else:
    print("Erreur API :", donnees)
