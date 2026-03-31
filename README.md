# DocuFlow AI — Traitement Intelligent de Documents Commerciaux

> Application d'extraction automatique de données depuis des factures et bons de livraison, propulsée par **Ollama (Qwen3-VL)** et orchestrée par **n8n**.

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Streamlit   │────▶│     n8n      │────▶│   Ollama     │
│  (Port 8501) │     │  (Port 5678) │     │ (Port 11434) │
│  Interface   │◀────│  Orchestrate │◀────│  qwen3-vl:8b │
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
- **8 Go de RAM** minimum (recommandé : 16 Go pour le modèle VLM)

### Lancement

```bash
# 1. Cloner/ouvrir le dossier du projet
cd pfa_ollama

# 2. Lancer tous les services
docker compose up -d --build

# 3. Attendre le téléchargement du modèle (~5 Go, première fois uniquement)
docker logs -f pfa_ollama_pull

# 4. Vérifier que tout fonctionne
docker compose ps
```

### Accès aux services

| Service      | URL                           | Identifiants        |
| ------------ | ----------------------------- | ------------------- |
| **Streamlit** | http://localhost:8501         | —                   |
| **n8n**       | http://localhost:5678         | admin / admin123    |
| **Ollama**    | http://localhost:11434        | —                   |
| **PostgreSQL**| localhost:5432                | pfa_user / (voir .env) |

### Importer le workflow n8n

1. Ouvrir **n8n** → http://localhost:5678
2. Menu **Workflows** → **Import from File**
3. Sélectionner `workflows/invoice_extraction.json`
4. **Activer** le workflow (toggle en haut à droite)
5. Le webhook `POST /webhook/invoice-extract` est maintenant prêt

### Tester l'extraction

1. Ouvrir **Streamlit** → http://localhost:8501
2. Uploader une image de facture (PNG, JPG, PDF)
3. Cliquer sur **🚀 Extraire les données**
4. Les données extraites s'affichent en temps réel

## 📁 Structure du projet

```
pfa_ollama/
├── docker-compose.yml          # Orchestration des services
├── Dockerfile.streamlit        # Image Streamlit
├── .env                        # Variables d'environnement
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

## ⚙️ Configuration GPU (optionnel)

Si vous avez un **GPU NVIDIA**, décommentez les lignes suivantes dans `docker-compose.yml` sous le service `ollama` :

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

## 🛑 Arrêter les services

```bash
docker compose down        # Arrêter (conserver les données)
docker compose down -v     # Arrêter + supprimer les volumes
```
