# Frontend - Unified Ranking Design

## Overview
Le backend a été refactorisé pour appliquer un **design unifié multi-dataset** à 4 types de classements (rankings). Le frontend peut maintenant afficher de manière cohérente tous ces classements avec texte ET graphiques interactifs.

---

## 🎯 Les 4 Intents Concernés

### 1. **fournisseur** - Classement des fournisseurs
- **Données clés**: `kg` (quantité), `acidity` (acidité %), `rendement` (rendement %), `lots` (nb lots)
- **Datasets graphique**:
  - Quantité totale (kg) - bar
  - Acidité moyenne (%) - line
  - Rendement moyen (%) - line
- **Status flags**: 🚨 acidité out of range, rendement out of range

### 2. **machines_utilisees** - Machines les plus utilisées
- **Données clés**: `nbExecutions` (nb exécutions), `rendementMoyen` (%), `totalProduit` (L)
- **Datasets graphique**:
  - Exécutions - bar
  - Rendement moyen (%) - line
  - Production (L) - bar
- **Classement**: Par ordre de nb exécutions décroissant

### 3. **lot_liste** - Liste des lots
- **Données clés**: `reference` (ref lot), `variete`, `fournisseur_nom`, `quantite_initiale` (kg), `qualite_huile`
- **Datasets graphique**:
  - Quantité (kg) - bar
- **Filtrage**: Peut inclure les lots non-conformes

### 4. **analyse_labo** - Analyses laboratoires
- **Données clés**: `lot_ref`, `date_analyse`, `acidite_huile_pourcent`, `indice_peroxyde_meq_o2_kg`, `k270`
- **Datasets graphique**:
  - Acidité (%) - bar
  - Peroxyde (meq O2/kg) - line
  - K270 - line
- **Status flags**: 🚨 acidité/peroxyde/K270 out of range

---

## 📊 Backend Response Format (2-Step Flow)

### 🚨 Critical Rules

⚠️ **DO NOT** send Step 1 and Step 2 in a single response — they **must be two separate API calls**.

⚠️ **ALWAYS** include `intent` field so frontend knows which ranking type to display.

⚠️ **ALWAYS** mark `type: "choice"` for initial ranking responses.

⚠️ For text mode, send `type: "text"` with data.  
   For chart mode, send `type: "chart"` with data.

⚠️ **NEVER** send ranking data without first sending the choice prompt.

---

### Step 1: Choice Prompt (Backend → Frontend)

When a ranking question is detected, **always respond with a choice prompt first**:

```json
{
  "type": "choice",
  "intent": "fournisseur",
  "message": "Souhaitez-vous voir les résultats sous forme de texte ou de graphique ?",
  "response": "Souhaitez-vous voir les résultats sous forme de texte ou de graphique ?",
  "options": ["texte", "graphique"],
  "confidence": 0.95,
  "applied_scope": {
    "huilerie": "Zitouneya",
    "period_label": "aujourd_hui"
  },
  "data": null,
  "entities": {},
  "applied_permissions": null
}
```

**Key Points:**
- `type` **must be** `"choice"`
- `intent` must be one of: `fournisseur`, `machines_utilisees`, `lot_liste`, `analyse_labo`
- Send `options: ["texte", "graphique"]` to display the buttons
- Set `data: null` — don't include actual ranking data yet
- Frontend will ask user to choose, then make a new request with their choice

---

### Step 2a: Text Results (User chose "Texte")

When user clicks "Texte" button, backend receives the same request but now should respond with:

```json
{
  "type": "text",
  "intent": "fournisseur",
  "message": "Classement fournisseurs de l'huilerie Zitouneya pour aujourd'hui :\n1. **Supplier A** — 5 lot(s), 1 000 kg, rendement 22,5 %, acidité 0,50 %",
  "response": "Classement fournisseurs...",
  "selected_option": "texte",
  "confidence": 0.95,
  "applied_scope": {
    "huilerie": "Zitouneya",
    "period_label": "aujourd_hui"
  },
  "data": {
    "items": [
      {
        "id": "f_1",
        "name": "Supplier A",
        "kg": 1000,
        "lots": 5,
        "acidity": 0.5,
        "rendement": 22.5,
        "acidityOutOfRange": false,
        "rendementOutOfRange": false
      },
      {
        "id": "f_2",
        "name": "Supplier B",
        "kg": 800,
        "lots": 4,
        "acidity": 1.8,
        "rendement": 28,
        "acidityOutOfRange": true,
        "rendementOutOfRange": false
      }
    ]
  },
  "entities": {},
  "applied_permissions": null
}
```

---

### Step 2b: Chart Results (User chose "Graphique")

When user clicks "Graphique" button, respond with:

```json
{
  "type": "chart",
  "chart_type": "bar",
  "intent": "fournisseur",
  "message": "Voici le graphique des fournisseurs classés par quantité livrée.",
  "response": "Voici le graphique...",
  "selected_option": "graphique",
  "confidence": 0.95,
  "applied_scope": {
    "huilerie": "Zitouneya",
    "period_label": "aujourd_hui"
  },
  "data": {
    "labels": ["Supplier A", "Supplier B", "Supplier C"],
    "datasets": [
      {
        "label": "Quantité totale (kg)",
        "data": [1000, 800, 600],
        "type": "bar"
      },
      {
        "label": "Rendement moyen (%)",
        "data": [22.5, 28, 19.5],
        "type": "line"
      },
      {
        "label": "Acidité moyenne (%)",
        "data": [0.5, 1.8, 0.6],
        "type": "line"
      }
    ],
    "items": [
      {
        "id": "f_1",
        "name": "Supplier A",
        "kg": 1000,
        "lots": 5,
        "acidity": 0.5,
        "rendement": 22.5,
        "acidityOutOfRange": false,
        "rendementOutOfRange": false
      },
      {
        "id": "f_2",
        "name": "Supplier B",
        "kg": 800,
        "lots": 4,
        "acidity": 1.8,
        "rendement": 28,
        "acidityOutOfRange": true,
        "rendementOutOfRange": false
      },
      {
        "id": "f_3",
        "name": "Supplier C",
        "kg": 600,
        "lots": 3,
        "acidity": 0.6,
        "rendement": 19.5,
        "acidityOutOfRange": false,
        "rendementOutOfRange": false
      }
    ]
  },
  "entities": {},
  "applied_permissions": null
}
```

**Key Points:**
- `type` is `"chart"`
- `chart_type` specifies the primary chart type: `"bar"` for most rankings
- `datasets` array contains multi-dataset structure for Chart.js
- `items` array contains the detailed data for rendering lists/tooltips
- Both `labels` and `datasets[].data` must have **same length**

---

## 🎨 Frontend Implementation

### 1. Detect Ranking Intents

```typescript
const RANKING_INTENTS = ['fournisseur', 'machines_utilisees', 'lot_liste', 'analyse_labo'];

function isRankingResponse(response: ChatResponse): boolean {
  return RANKING_INTENTS.includes(response.intent);
}
```

### 2. Handle Choice Prompt (Step 1)

When `type === "choice"` and `options` includes "texte" and "graphique":

```typescript
if (response.type === 'choice' && response.options?.includes('texte')) {
  // Display two buttons: [Texte] [Graphique]
  // On click, make new request:
  // POST /ask with same message + session_id
  // Frontend will automatically detect user's choice somehow
  // (either via UI state or by sending selected_option param)
}
```

### 3. Render Text Results (Step 2a)

When `type === "text"` and `data.items` exists:

```typescript
function renderRankingText(response: ChatResponse) {
  const items = response.data?.items || [];
  
  // Display the message
  console.log(response.message);
  
  // Render as table or list
  items.forEach((item, index) => {
    console.log(`${index + 1}. ${item.name}`);
    
    // Render fields based on intent
    if (response.intent === 'fournisseur') {
      console.log(`  • ${item.kg.toLocaleString()} kg`);
      console.log(`  • Rendement: ${item.rendement.toFixed(1)}% ${item.rendementOutOfRange ? '🚨' : ''}`);
      console.log(`  • Acidité: ${item.acidity.toFixed(2)}% ${item.acidityOutOfRange ? '🚨' : ''}`);
    } else if (response.intent === 'machines_utilisees') {
      console.log(`  • ${item.nbExecutions} exécutions`);
      console.log(`  • Rendement: ${item.rendementMoyen.toFixed(1)}%`);
      console.log(`  • Production: ${item.totalProduit.toLocaleString()} L`);
    }
    // ... etc for other intents
  });
}
```

### 4. Render Chart Results (Step 2b)

When `type === "chart"` and `data.datasets` exists:

```typescript
import Chart from 'chart.js/auto';

function renderRankingChart(response: ChatResponse) {
  const chartData = response.data;
  const ctx = document.getElementById('rankingChart').getContext('2d');
  
  const colors = [
    'rgba(54, 162, 235, 0.8)',  // blue
    'rgba(255, 159, 64, 0.8)',  // orange
    'rgba(75, 192, 75, 0.8)',   // green
    'rgba(255, 99, 132, 0.8)',  // red
  ];
  
  const chart = new Chart(ctx, {
    type: response.chart_type || 'bar',
    data: {
      labels: chartData.labels,
      datasets: chartData.datasets.map((ds, idx) => ({
        label: ds.label,
        data: ds.data,
        type: ds.type || response.chart_type,
        borderColor: colors[idx % colors.length],
        backgroundColor: colors[idx % colors.length],
        fill: false,
        tension: 0.1,
        borderWidth: 2,
      })),
    },
    options: {
      responsive: true,
      plugins: {
        title: {
          display: true,
          text: response.message,
          font: { size: 14, weight: 'bold' },
        },
        legend: {
          display: true,
          position: 'top',
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: response.intent === 'fournisseur' ? 'Values' : 'Quantity/Performance',
          },
        },
      },
    },
  });
  
  return chart;
}
```

### 5. Highlight Out-of-Range Items

```typescript
function highlightOutOfRangeItems(response: ChatResponse) {
  const items = response.data?.items || [];
  
  items.forEach((item) => {
    if (response.intent === 'fournisseur') {
      if (item.acidityOutOfRange) {
        // Apply red styling, add 🚨 badge
        console.warn(`⚠️ Acidity out of range: ${item.acidity}%`);
      }
      if (item.rendementOutOfRange) {
        console.warn(`⚠️ Rendement out of range: ${item.rendement}%`);
      }
    }
    
    if (response.intent === 'analyse_labo') {
      if (item.acidityOutOfRange) console.warn(`⚠️ Acidité: ${item.acidite_huile_pourcent}%`);
      if (item.peroxideOutOfRange) console.warn(`⚠️ Peroxyde: ${item.indice_peroxyde_meq_o2_kg}`);
      if (item.k270OutOfRange) console.warn(`⚠️ K270: ${item.k270}`);
    }
  });
}
```

### 6. Complete Interaction Flow

```typescript
async function handleRankingQuery(message: string) {
  // Step 1: Send question
  const response1 = await fetch('/chat/ask', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId }),
  }).then(r => r.json());
  
  // Step 1a: Display choice
  if (response1.type === 'choice') {
    displayChoiceButtons(['Texte', 'Graphique']);
    
    // User clicks button...
    const userChoice = await getUserChoice();
    
    // Step 2: Send same message again (frontend somehow indicates choice)
    const response2 = await fetch('/chat/ask', {
      method: 'POST',
      body: JSON.stringify({
        message,
        session_id: sessionId,
        selected_option: userChoice, // "texte" or "graphique"
      }),
    }).then(r => r.json());
    
    // Step 2a/2b: Render results
    if (response2.type === 'text') {
      renderRankingText(response2);
    } else if (response2.type === 'chart') {
      renderRankingChart(response2);
    }
  }
}
```

---

## 🔄 Complete Interaction Flow Example

### Scenario: User asks "Machines les plus utilisées?"

**Step 1 — Backend sends CHOICE prompt:**
```
Request: POST /chat/ask
{
  "message": "Machines les plus utilisées?",
  "session_id": "user-123"
}

Response:
{
  "type": "choice",
  "intent": "machines_utilisees",
  "message": "Souhaitez-vous voir les résultats sous forme de texte ou de graphique ?",
  "options": ["texte", "graphique"],
  "data": null
}
```

**Frontend displays:**
```
Bot: "Souhaitez-vous voir les résultats sous forme de texte ou de graphique ?"

[Texte] [Graphique]
```

**Step 2a — User clicks "Texte":**
```
Request: POST /chat/ask
{
  "message": "texte",
  "session_id": "user-123"
}

Response:
{
  "type": "text",
  "intent": "machines_utilisees",
  "message": "Machines les plus utilisées... Machine A — 45 exécutions...",
  "selected_option": "texte",
  "data": {
    "items": [
      {
        "id": "m_1",
        "name": "Machine A",
        "nbExecutions": 45,
        "rendementMoyen": 90.2,
        "totalProduit": 2250
      },
      {
        "id": "m_2",
        "name": "Machine B",
        "nbExecutions": 32,
        "rendementMoyen": 85.5,
        "totalProduit": 1600
      }
    ]
  }
}
```

**Frontend displays:**
```
1. Machine A
  • 45 exécutions
  • Rendement: 90.2%
  • Production: 2,250 L

2. Machine B
  • 32 exécutions
  • Rendement: 85.5%
  • Production: 1,600 L
```

**OR Step 2b — User clicks "Graphique":**
```
Request: POST /chat/ask
{
  "message": "graphique",
  "session_id": "user-123"
}

Response:
{
  "type": "chart",
  "chart_type": "bar",
  "intent": "machines_utilisees",
  "message": "Voici le graphique des machines...",
  "selected_option": "graphique",
  "data": {
    "labels": ["Machine A", "Machine B"],
    "datasets": [
      {
        "label": "Exécutions",
        "data": [45, 32],
        "type": "bar"
      },
      {
        "label": "Rendement moyen (%)",
        "data": [90.2, 85.5],
        "type": "line"
      },
      {
        "label": "Production (L)",
        "data": [2250, 1600],
        "type": "bar"
      }
    ],
    "items": [
      {"id": "m_1", "name": "Machine A", "nbExecutions": 45, ...},
      {"id": "m_2", "name": "Machine B", "nbExecutions": 32, ...}
    ]
  }
}
```

**Frontend displays:**
```
[Chart.js visualization with 3 datasets as specified]
```

---

## 🎨 Design Recommendations

### Color Scheme by Intent
- **Fournisseur**: 🟦 Blue (confidence/supply chain)
- **Machines**: 🟨 Orange (equipment/industry)
- **Lots**: 🟩 Green (traceability/nature)
- **Analyses**: 🟥 Red (quality/laboratory)

### Interactions
- Display top ranks (1-3) in **bold** or with badges
- Highlight 🚨 alerts in **red**
- Limit display to **Top 8** in lists with "+ N more"

### Charts
- Use **Chart.js** with specified types (bar, line)
- **Mixed charts** (bar + line) for better readability
- Responsive and zoom on mobile

---

## ✅ Implementation Checklist

- [ ] Implement `RANKING_INTENTS` constant
- [ ] Detect `type: "choice"` and display options
- [ ] Route clicks to new requests
- [ ] Implement text rendering with data structure
- [ ] Implement Chart.js rendering
- [ ] Add styles for rank badges (1-3 bold)
- [ ] Add visual alerts for status flags 🚨
- [ ] Test all 4 intents
- [ ] Responsive design (mobile/desktop)
- [ ] Accessibility (alt text, ARIA labels)

---

## 🐛 Debugging

### Test Choice Prompt

```bash
curl -X POST http://localhost:8000/chat/ask \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Machines les plus utilisées",
    "session_id": "test-123"
  }'
```

**Expected:** `type: "choice"`, `options: ["texte", "graphique"]`, `data: null`

### Test Text Response

```bash
curl -X POST http://localhost:8000/chat/ask \
  -H "Content-Type: application/json" \
  -d '{
    "message": "texte",
    "session_id": "test-123"
  }'
```

**Expected:** `type: "text"`, `data.items` array populated

### Test Chart Response

```bash
curl -X POST http://localhost:8000/chat/ask \
  -H "Content-Type: application/json" \
  -d '{
    "message": "graphique",
    "session_id": "test-123"
  }'
```

**Expected:** `type: "chart"`, `data.labels` and `data.datasets` populated

### Common Issues

| Problem | Solution |
|---------|----------|
| Choice not showing | Check `type: "choice"` in response + `options` field present |
| Text option broken | Verify `type: "text"` + `data.items` array not empty |
| Chart not rendering | Check `data.labels.length === data.datasets[0].data.length` |
| Out-of-range not showing | Verify `acidityOutOfRange`, `rendementOutOfRange` etc are boolean true/false |
| Session lost | Verify `session_id` is same across all 3 requests (choice → texte/graphique → results) |

---

## 📋 Data Structures by Intent

### 1. Fournisseur (Suppliers)

```json
{
  "items": [
    {
      "id": "f_1",
      "name": "Supplier Name",
      "kg": 1000,
      "lots": 5,
      "acidity": 0.5,
      "rendement": 22.5,
      "acidityOutOfRange": false,
      "rendementOutOfRange": false
    }
  ]
}
```

**Out-of-Range Thresholds:**
- `acidityOutOfRange`: `true` if `acidity < 0.2 || acidity > 1.5`
- `rendementOutOfRange`: `true` if `rendement < 10 || rendement > 30`

---

### 2. Machines Utilisées (Machines)

```json
{
  "items": [
    {
      "id": "m_1",
      "name": "Machine Name",
      "nbExecutions": 45,
      "rendementMoyen": 25.3,
      "totalProduit": 1250.5
    }
  ]
}
```

**Chart Datasets:**
- Exécutions (bar)
- Rendement moyen % (line)
- Production (L) (bar)

---

### 3. Lot Liste (Batches/Lots)

```json
{
  "items": [
    {
      "id": "l_1",
      "name": "LOT-2024-001",
      "reference": "LOT-2024-001",
      "variete": "Chemlali",
      "fournisseur_nom": "Supplier A",
      "quantite_initiale": 500,
      "qualite_huile": "Extra"
    }
  ]
}
```

**Chart Datasets:**
- Quantité (kg) (bar)

---

### 4. Analyse Labo (Laboratory Analysis)

```json
{
  "items": [
    {
      "id": "a_1",
      "name": "LOT-2024-001",
      "lot_ref": "LOT-2024-001",
      "date_analyse": "2024-05-01",
      "acidite_huile_pourcent": 0.4,
      "indice_peroxyde_meq_o2_kg": 10,
      "k270": 0.25,
      "acidityOutOfRange": false,
      "peroxideOutOfRange": false,
      "k270OutOfRange": false
    }
  ]
}
```

**Out-of-Range Thresholds:**
- `acidityOutOfRange`: `true` if `acidite_huile_pourcent < 0.2 || acidite_huile_pourcent > 0.8`
- `peroxideOutOfRange`: `true` if `indice_peroxyde_meq_o2_kg < 5 || indice_peroxyde_meq_o2_kg > 20`
- `k270OutOfRange`: `true` if `k270 < 0.2 || k270 > 0.3`

**Chart Datasets:**
- Acidité % (bar)
- Peroxyde meq O2/kg (line)
- K270 (line)

---

## 🎨 Recommandations de Design

### Couleurs par intent
- **Fournisseur**: 🟦 Bleu (confiance/supply chain)
- **Machines**: 🟨 Orange (équipements/industrie)
- **Lots**: 🟩 Vert (traçabilité/nature)
- **Analyses**: 🟥 Rouge (qualité/laboratoire)

### Interactions
- Afficher les rangements (rang 1-3) en **gras** ou avec badges
- Surligner les alertes 🚨 en **rouge**
- Limiter l'affichage à **Top 8** dans les listes avec "+ N autres"

### Graphiques
- Utiliser **Chart.js** avec les types spécifiés (bar, line)
- **Mixed charts** (bar + line) pour meilleure lisibilité
- Responsive et zoom sur mobile

---

## ✅ Checklist d'Implémentation

- [ ] Implémenter `RANKING_INTENTS` constant
- [ ] Détecter `type: "choice"` et afficher les options
- [ ] Router les clics vers nouvelles requêtes
- [ ] Implémenter rendu texte avec structure de données
- [ ] Implémenter rendu graphique Chart.js
- [ ] Ajouter styles pour rang (1-3 en gras)
- [ ] Ajouter alertes visuelles pour status flags
- [ ] Tester tous les 4 intents
- [ ] Responsive design (mobile/desktop)
- [ ] Accessibilité (alt text, ARIA labels)

---

## 🐛 Débogage

### Vérifier le payload du backend

```bash
# Terminal: Test fournisseur avec graphique
curl -X POST http://localhost:8000/chat/ask \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Graphique des fournisseurs",
    "session_id": "test-123"
  }'
```

Devrait retourner:
```json
{
  "type": "chart",
  "chart_type": "bar",
  "data": {
    "labels": [...],
    "datasets": [...]
  }
}
```

### Problèmes courants

| Problème | Solution |
|----------|----------|
| Graphique ne s'affiche pas | Vérifier que `data.labels` et `data.datasets[].data` ont même longueur |
| Requête de choix ne fonctionne pas | Vérifier que `selected_option` est envoyée dans la prochaine requête |
| Status flags invisibles | Vérifier que la logique de rendu utilise `*_status` (ex: `acidity_status`) |
| "out of range" non détecté | Backend: La validation use des seuils hardcodés (voir valeurs à adapter) |

