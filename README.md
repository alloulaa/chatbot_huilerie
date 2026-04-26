# Chatbot Huilerie - Prototype enrichi

Prototype FastAPI prêt à tester pour une plateforme web de gestion des huileries.

## Fonctionnalités incluses
- Interface web de chat
- Détection d'intentions par règles
- Extraction d'entités (huilerie, machine, lot, période, type d'huile)
- Gestion du contexte conversationnel par session
- Contrôle de portée selon le rôle utilisateur
- Base SQLite de démonstration initialisée automatiquement
- Réponses textuelles + données structurées
- Historique de conversation

## Intentions déjà prises en charge
- consulter_production_totale
- consulter_stock_huile
- consulter_rendement_moyen
- consulter_pannes_machine
- consulter_etat_machine
- consulter_kpi_global
- consulter_reception_olives
- consulter_qualite_moyenne
- consulter_lots_non_conformes
- consulter_alertes
- predire_qualite_lot
- predire_quantite_produite
- expliquer_prediction
- salutation
- aide_chatbot
- continuer_contexte

## Lancement
```bash
python -m venv .venv
source .venv/bin/activate
# Sous Windows:
# .venv\Scripts\activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Puis ouvrir :
```text
http://127.0.0.1:8000/
```

## API
### POST /chat/ask
```json
{
  "message": "Quelle est la production de l'huilerie Nour ce mois-ci ?",
  "user_id": 1,
  "session_id": "demo-session"
}
```

### GET /chat/history/{session_id}
Retourne l'historique des échanges.

## Utilisateurs de démonstration
- 1 : Direction (global)
- 2 : Responsable Nour (restreint à Nour)
- 3 : Maintenance Nour (restreint à Nour)
- 4 : Qualité Sahel (restreint à Sahel)

## Remarques
- Les prédictions sont heuristiques dans ce prototype.
- La base SQLite peut ensuite être remplacée par MySQL/PostgreSQL.
- Le moteur NLP peut ensuite évoluer vers un classificateur ou un LLM avec garde-fous.
