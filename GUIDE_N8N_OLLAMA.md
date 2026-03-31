# Guide Technique : Extraction de Factures avec n8n + Ollama (Qwen3-VL)

> **Stack** : n8n (self-hosted) · Ollama (local) · qwen3-vl:8b

---

## Table des matières

1. [Prérequis](#1-prérequis)
2. [System Prompt pour Qwen-VL](#2-system-prompt-pour-qwen-vl)
3. [Schéma JSON cible](#3-schéma-json-cible)
4. [Configuration n8n — HTTP Request vers Ollama](#4-configuration-n8n--http-request-vers-ollama)
5. [Gestion des erreurs et nettoyage de la réponse](#5-gestion-des-erreurs-et-nettoyage-de-la-réponse)
6. [Workflow complet (résumé visuel)](#6-workflow-complet)

---

## 1. Prérequis

```bash
# Vérifier qu'Ollama est lancé
ollama serve

# Télécharger le modèle vision
ollama pull qwen3-vl:8b

# Tester que le modèle répond
curl http://localhost:11434/api/tags
```

> **Important** : Si n8n et Ollama tournent dans des conteneurs Docker séparés, remplacez `localhost` par le nom du service Docker (ex. `ollama`) ou par `host.docker.internal`.

---

## 2. System Prompt pour Qwen-VL

Copiez ce prompt **tel quel** dans votre configuration n8n.

```text
Tu es un système d'extraction de données de factures commerciales. Tu dois analyser l'image de facture fournie et extraire TOUTES les informations demandées avec une précision maximale.

RÈGLES STRICTES :
1. Tu dois répondre UNIQUEMENT avec un objet JSON valide. Aucun texte avant, aucun texte après, aucune balise markdown.
2. Si une information est illisible ou absente, utilise la valeur null.
3. Pour les montants numériques, utilise des nombres décimaux (type number), PAS de chaînes de caractères. Utilise le point comme séparateur décimal.
4. Pour les articles, analyse soigneusement le tableau ligne par ligne. Chaque ligne du tableau correspond à un objet dans le tableau "articles". Fais une corrélation visuelle stricte entre chaque colonne (désignation, quantité, prix unitaire, total ligne) pour ne pas mélanger les valeurs entre les lignes.
5. Si le document contient une TVA à plusieurs taux, crée un objet par taux dans le tableau "tva_details".
6. Le champ "devise" doit refléter la devise visible sur le document (ex: "TND", "EUR", "USD").

STRUCTURE JSON ATTENDUE :
{
  "fournisseur": {
    "nom": "string",
    "adresse": "string",
    "telephone": "string | null",
    "email": "string | null",
    "matricule_fiscal": "string | null"
  },
  "client": {
    "nom": "string | null",
    "adresse": "string | null"
  },
  "facture": {
    "numero": "string",
    "date": "string (format JJ/MM/AAAA)",
    "devise": "string"
  },
  "articles": [
    {
      "designation": "string",
      "quantite": number,
      "prix_unitaire": number,
      "total_ligne": number
    }
  ],
  "totaux": {
    "total_ht": number,
    "tva_details": [
      {
        "taux_pourcent": number,
        "montant": number
      }
    ],
    "total_tva": number,
    "total_ttc": number,
    "timbre_fiscal": number | null
  }
}
```

---

## 3. Schéma JSON cible

Voici un **exemple concret** de la sortie attendue :

```json
{
  "fournisseur": {
    "nom": "STAROIL SA",
    "adresse": "Zone Industrielle, Sfax 3000, Tunisie",
    "telephone": "+216 74 123 456",
    "email": "contact@staroil.tn",
    "matricule_fiscal": "1234567/A/P/000"
  },
  "client": {
    "nom": "Société ABC",
    "adresse": "Rue de la Liberté, Tunis 1000"
  },
  "facture": {
    "numero": "FAC-2025-001234",
    "date": "15/01/2025",
    "devise": "TND"
  },
  "articles": [
    {
      "designation": "Huile moteur 5W30 - 5L",
      "quantite": 10,
      "prix_unitaire": 45.500,
      "total_ligne": 455.000
    },
    {
      "designation": "Filtre à huile REF-H200",
      "quantite": 5,
      "prix_unitaire": 12.800,
      "total_ligne": 64.000
    },
    {
      "designation": "Liquide de frein DOT4 - 1L",
      "quantite": 20,
      "prix_unitaire": 8.250,
      "total_ligne": 165.000
    }
  ],
  "totaux": {
    "total_ht": 684.000,
    "tva_details": [
      {
        "taux_pourcent": 19,
        "montant": 129.960
      }
    ],
    "total_tva": 129.960,
    "total_ttc": 813.960,
    "timbre_fiscal": 1.000
  }
}
```

---

## 4. Configuration n8n — HTTP Request vers Ollama

### 4.1 Architecture du workflow n8n

```
[Trigger / Webhook] → [Read Binary File] → [Code: Base64 Encode] → [HTTP Request: Ollama] → [Code: Clean JSON] → [Suite…]
```

### 4.2 Nœud « Code » — Encoder l'image en Base64

Ajoutez un nœud **Code** (JavaScript) juste après avoir reçu le fichier binaire :

```javascript
// ── Nœud Code : Encodage Base64 de l'image ──
// Ce nœud lit le fichier binaire entrant et le convertit en Base64

const binaryData = $input.first().binary;

// Récupérer la première clé binaire (souvent "data" ou le nom du fichier)
const binaryKey = Object.keys(binaryData)[0];
const fileBuffer = await this.helpers.getBinaryDataBuffer(0, binaryKey);

const base64Image = fileBuffer.toString('base64');
const mimeType = binaryData[binaryKey].mimeType;
const fileName = binaryData[binaryKey].fileName;

return [{
  json: {
    base64Image,
    mimeType,
    fileName
  }
}];
```

### 4.3 Nœud « HTTP Request » — Appel Ollama `/api/chat`

| Paramètre            | Valeur                                          |
| --------------------- | ----------------------------------------------- |
| **Method**            | `POST`                                          |
| **URL**               | `http://ollama:11434/api/chat`                  |
| **Body Content Type** | `JSON`                                          |
| **Options → Timeout** | `120000` (120 secondes — les VLM sont lents)    |

> **Note URL** : Remplacez `ollama` par `localhost` si Ollama tourne sur la même machine hors Docker, ou par `host.docker.internal` si n8n est dans Docker mais Ollama est sur l'hôte.

#### Corps (Body) JSON — Expression n8n :

Choisissez **« JSON »** dans Body Content Type, puis collez ceci **en mode Expression** :

```json
{
  "model": "qwen3-vl:8b",
  "stream": false,
  "messages": [
    {
      "role": "system",
      "content": "Tu es un système d'extraction de données de factures commerciales. Tu dois analyser l'image de facture fournie et extraire TOUTES les informations demandées avec une précision maximale.\n\nRÈGLES STRICTES :\n1. Tu dois répondre UNIQUEMENT avec un objet JSON valide. Aucun texte avant, aucun texte après, aucune balise markdown.\n2. Si une information est illisible ou absente, utilise la valeur null.\n3. Pour les montants numériques, utilise des nombres décimaux (type number), PAS de chaînes de caractères. Utilise le point comme séparateur décimal.\n4. Pour les articles, analyse soigneusement le tableau ligne par ligne. Chaque ligne du tableau correspond à un objet dans le tableau \"articles\". Fais une corrélation visuelle stricte entre chaque colonne (désignation, quantité, prix unitaire, total ligne) pour ne pas mélanger les valeurs entre les lignes.\n5. Si le document contient une TVA à plusieurs taux, crée un objet par taux dans le tableau \"tva_details\".\n6. Le champ \"devise\" doit refléter la devise visible sur le document (ex: \"TND\", \"EUR\", \"USD\").\n\nSTRUCTURE JSON ATTENDUE :\n{\"fournisseur\":{\"nom\":\"string\",\"adresse\":\"string\",\"telephone\":\"string|null\",\"email\":\"string|null\",\"matricule_fiscal\":\"string|null\"},\"client\":{\"nom\":\"string|null\",\"adresse\":\"string|null\"},\"facture\":{\"numero\":\"string\",\"date\":\"string (format JJ/MM/AAAA)\",\"devise\":\"string\"},\"articles\":[{\"designation\":\"string\",\"quantite\":\"number\",\"prix_unitaire\":\"number\",\"total_ligne\":\"number\"}],\"totaux\":{\"total_ht\":\"number\",\"tva_details\":[{\"taux_pourcent\":\"number\",\"montant\":\"number\"}],\"total_tva\":\"number\",\"total_ttc\":\"number\",\"timbre_fiscal\":\"number|null\"}}"
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Extrais toutes les informations de cette facture commerciale. Réponds uniquement en JSON valide."
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:{{ $json.mimeType }};base64,{{ $json.base64Image }}"
          }
        }
      ]
    }
  ],
  "options": {
    "temperature": 0.1,
    "num_predict": 4096
  }
}
```

> **Pourquoi `temperature: 0.1` ?** Une température très basse force le modèle à être déterministe et à respecter la structure JSON demandée.

> **Pourquoi `num_predict: 4096` ?** Les factures longues avec beaucoup d'articles nécessitent un espace de sortie suffisant.

> **Pourquoi `stream: false` ?** Pour recevoir la réponse complète en une seule fois au lieu d'un flux de tokens.

### 4.4 Alternative : API `/api/generate` (si `/api/chat` ne fonctionne pas)

Si votre version d'Ollama ne supporte pas le format multimodal chat, utilisez `/api/generate` :

```json
{
  "model": "qwen3-vl:8b",
  "stream": false,
  "prompt": "Tu es un système d'extraction de données de factures. Analyse cette image de facture et extrais TOUTES les informations. Réponds UNIQUEMENT en JSON valide sans aucun texte additionnel. Structure attendue: {fournisseur:{nom,adresse,telephone,email,matricule_fiscal}, client:{nom,adresse}, facture:{numero,date,devise}, articles:[{designation,quantite,prix_unitaire,total_ligne}], totaux:{total_ht,tva_details:[{taux_pourcent,montant}],total_tva,total_ttc,timbre_fiscal}}",
  "images": ["{{ $json.base64Image }}"],
  "options": {
    "temperature": 0.1,
    "num_predict": 4096
  }
}
```

> **Différence clé** : Avec `/api/generate`, les images sont passées dans un tableau `"images"` au niveau racine (Base64 brut, sans préfixe `data:`). Le prompt est une seule chaîne `"prompt"` (pas de rôles system/user).

---

## 5. Gestion des erreurs et nettoyage de la réponse

### 5.1 Nœud « Code » — Nettoyage JSON

Ajoutez ce nœud **Code** (JavaScript) juste après le HTTP Request :

```javascript
// ── Nœud Code : Nettoyage et parsing de la réponse Ollama ──

// 1. Récupérer la réponse brute du modèle
const ollamaResponse = $input.first().json;

// Selon l'endpoint utilisé :
// - /api/chat  → réponse dans ollamaResponse.message.content
// - /api/generate → réponse dans ollamaResponse.response
let rawContent = ollamaResponse.message?.content || ollamaResponse.response || '';

// 2. Supprimer les balises ```json ... ``` si présentes
rawContent = rawContent.replace(/^```json\s*/i, '');
rawContent = rawContent.replace(/^```\s*/i, '');
rawContent = rawContent.replace(/\s*```$/i, '');

// 3. Supprimer tout texte avant le premier { et après le dernier }
const firstBrace = rawContent.indexOf('{');
const lastBrace = rawContent.lastIndexOf('}');

if (firstBrace === -1 || lastBrace === -1) {
  throw new Error('ERREUR: Aucun JSON valide trouvé dans la réponse du modèle. Réponse brute: ' + rawContent.substring(0, 500));
}

rawContent = rawContent.substring(firstBrace, lastBrace + 1);

// 4. Parser le JSON
let parsedData;
try {
  parsedData = JSON.parse(rawContent);
} catch (parseError) {
  // Tentative de correction des erreurs JSON courantes
  let fixedContent = rawContent;

  // Corriger les virgules traînantes avant } ou ]
  fixedContent = fixedContent.replace(/,\s*([}\]])/g, '$1');

  // Corriger les guillemets simples → doubles
  fixedContent = fixedContent.replace(/'/g, '"');

  try {
    parsedData = JSON.parse(fixedContent);
  } catch (secondError) {
    throw new Error(
      'ERREUR: Impossible de parser le JSON même après nettoyage.\n' +
      'Erreur: ' + secondError.message + '\n' +
      'Contenu nettoyé: ' + fixedContent.substring(0, 500)
    );
  }
}

// 5. Validation minimale : vérifier les champs critiques
const validationErrors = [];

if (!parsedData.fournisseur?.nom) {
  validationErrors.push('Nom du fournisseur manquant');
}
if (!parsedData.facture?.numero) {
  validationErrors.push('Numéro de facture manquant');
}
if (!parsedData.articles || parsedData.articles.length === 0) {
  validationErrors.push('Aucun article extrait');
}
if (parsedData.totaux?.total_ttc == null) {
  validationErrors.push('Total TTC manquant');
}

// 6. Retourner le résultat structuré
return [{
  json: {
    extraction: parsedData,
    metadata: {
      source_file: $('Code_Base64').first().json.fileName || 'unknown',
      extraction_date: new Date().toISOString(),
      model_used: 'qwen3-vl:8b',
      validation_warnings: validationErrors,
      is_valid: validationErrors.length === 0,
      nombre_articles: parsedData.articles?.length || 0
    }
  }
}];
```

> **Note** : Remplacez `$('Code_Base64')` par le nom réel de votre nœud d'encodage Base64 dans n8n.

### 5.2 Gestion d'erreur globale — Nœud Error Trigger

Ajoutez un **Error Trigger** au workflow n8n pour capturer les échecs :

```javascript
// ── Dans un nœud Code connecté à l'Error Trigger ──

const error = $input.first().json;

return [{
  json: {
    status: 'ERROR',
    error_message: error.message || 'Erreur inconnue',
    timestamp: new Date().toISOString(),
    workflow_id: $workflow.id,
    execution_id: $execution.id
  }
}];
```

---

## 6. Workflow complet

```
┌─────────────────┐
│  Webhook / Form  │  ← Réception de l'image (upload)
│  Trigger         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Read Binary     │  ← Lire le fichier uploadé
│  File            │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Code:           │  ← Convertir l'image en Base64
│  Base64 Encode   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  HTTP Request    │  ← POST vers Ollama /api/chat
│  → Ollama        │     (qwen3-vl:8b)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Code:           │  ← Nettoyer + Parser le JSON
│  Clean & Parse   │     + Validation
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────────┐
│  DB /   │ │  Alerte /   │
│  Stocke │ │  Notif si   │
│         │ │  erreur     │
└────────┘ └────────────┘
```

---

## Récapitulatif rapide

| Élément                    | Détail                                                        |
| -------------------------- | ------------------------------------------------------------- |
| **Endpoint Ollama**        | `POST /api/chat` (recommandé) ou `POST /api/generate`        |
| **Modèle**                 | `qwen3-vl:8b`                                                |
| **Temperature**            | `0.1` (déterministe)                                          |
| **Timeout n8n**            | `120 000 ms` (2 min)                                          |
| **Format image**           | Base64 inline (data URI pour `/api/chat`, brut pour `/api/generate`) |
| **Nettoyage réponse**      | Strip markdown fences + extraction `{…}` + JSON.parse         |
| **Validation**             | Vérification des 4 champs critiques après parsing             |
