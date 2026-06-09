# Tests Unitaires - Service IA Chatbot

Ce dossier contient les tests unitaires minimum pour le service IA chatbot.

## Structure des Tests

- `test_chat_service.py` - Tests du service principal ChatService (5 tests)
- `test_nlp_factory.py` - Tests de la factory NLP (6 tests)
- `test_domain_models.py` - Tests des modèles de domaine (8 tests)
- `test_normalizer.py` - Tests du normalizer de périodes (7 tests)
- `test_permission_service.py` - Tests du service de permissions RBAC (12 tests)

**Total: 38 tests unitaires**

## Prérequis

Python 3.9+ et les dépendances du projet.

## Installation des Dépendances de Test

```bash
# Depuis le répertoire racine du projet
pip install -r test/requirements-test.txt
```

Ou installer manuellement:
```bash
pip install pytest>=8.0.0 pytest-asyncio>=0.23.0 pytest-mock>=3.12.0
```

## Exécution des Tests

### Exécuter tous les tests
```bash
# Depuis le répertoire racine
pytest test/
```

### Exécuter un fichier de test spécifique
```bash
pytest test/test_chat_service.py
pytest test/test_nlp_factory.py
pytest test/test_domain_models.py
pytest test/test_normalizer.py
pytest test/test_permission_service.py
```

### Exécuter avec détails verbeux
```bash
pytest test/ -v
```

### Exécuter avec rapport de couverture
```bash
pytest test/ --cov=app --cov-report=html
```

### Exécuter uniquement les tests qui échouent
```bash
pytest test/ --lf
```

## Résultat Attendu

Un build succès devrait afficher:
```
============================== 38 passed in X.XXs ==============================
```

## Dépannage

### Erreur: ModuleNotFoundError
Assurez-vous que vous exécutez les tests depuis le répertoire racine du projet (`chatbot_huilerie`).

### Erreur: Import errors
Vérifiez que toutes les dépendances du projet sont installées:
```bash
pip install -r requirements.txt
```

### Tests asynchrones qui échouent
Les tests asynchrones nécessitent `pytest-asyncio`. Installez-le:
```bash
pip install pytest-asyncio
```

## Notes Importantes

- Les tests utilisent des mocks pour éviter les appels externes (API, base de données)
- Les tests sont conçus pour être rapides et indépendants
- Aucune configuration de base de données réelle n'est requise
- Les tests couvrent les chemins critiques du système sans surcharger
