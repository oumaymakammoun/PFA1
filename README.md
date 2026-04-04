# DocuFlow AI — Traitement Intelligent de Documents Commerciaux

> Application d'extraction automatique de données depuis des factures et bons de livraison, propulsée par **Mistral OCR** et orchestrée par **n8n**.

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Streamlit   │────▶│     n8n      │     │  Mistral OCR │
│  (Port 8501) │     │  (Port 5678) │     │  (API Cloud) │
│  Interface   │─────┼──────────────┼────▶│  OCR + Chat  │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                     ┌──────▼───────┐
                     │  PostgreSQL  │
                     │  (Port 5432) │
                     └──────────────┘
```

## 🚀 Démarrage rapide

### Prérequis
- **Docker Desktop** installé et lancé
- **Clé API Mistral** — Créez un compte sur [console.mistral.ai](https://console.mistral.ai/) et récupérez votre clé API

### Configuration

1. Ouvrez le fichier `.env` et renseignez votre clé API Mistral :
```bash
MISTRAL_API_KEY=votre_vraie_cle_api_ici
```

### Lancement

```bash
# 1. Cloner/ouvrir le dossier du projet
cd pfa_ollama

# 2. Lancer tous les services
docker compose up -d --build

# 3. Vérifier que tout fonctionne
docker compose ps
```

### Accès aux services

| Service      | URL                           | Identifiants        |
| ------------ | ----------------------------- | ------------------- |
| **Streamlit** | http://localhost:8501         | —                   |
| **n8n**       | http://localhost:5678         | admin / admin123    |
| **PostgreSQL**| localhost:5432                | pfa_user / (voir .env) |

### Importer le workflow n8n

1. Ouvrir **n8n** → http://localhost:5678
2. Menu **Workflows** → **Import from File**
3. Sélectionner `workflows/invoice_extraction.json`
4. **Activer** le workflow (toggle en haut à droite)
5. Le webhook `POST /webhook/facture` est maintenant prêt

### Tester l'extraction

1. Ouvrir **Streamlit** → http://localhost:8501
2. Uploader une image de facture (PNG, JPG, PDF)
3. Cliquer sur **🚀 Extraire les données**
4. Les données extraites s'affichent en quelques secondes

## 📁 Structure du projet

```
pfa_ollama/
├── docker-compose.yml          # Orchestration des services
├── Dockerfile.streamlit        # Image Streamlit
├── .env                        # Variables d'environnement (clé API Mistral)
├── README.md
├── GUIDE_N8N_OLLAMA.md         # Guide technique détaillé
├── db/
│   └── init.sql                # Schéma PostgreSQL
├── workflows/
│   └── invoice_extraction.json # Workflow n8n importable
└── streamlit_app/
    ├── app.py                  # Interface utilisateur
    └── requirements.txt        # Dépendances Python
```

## 🔑 Configuration de la clé API Mistral

1. Rendez-vous sur [console.mistral.ai](https://console.mistral.ai/)
2. Créez un compte ou connectez-vous
3. Allez dans **API Keys** → **Create New Key**
4. Copiez la clé et collez-la dans `.env` :
   ```
   MISTRAL_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   ```
5. Relancez les services : `docker compose up -d --build`

## 🛑 Arrêter les services

```bash
docker compose down        # Arrêter (conserver les données)
docker compose down -v     # Arrêter + supprimer les volumes
```
