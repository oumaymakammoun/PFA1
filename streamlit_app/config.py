"""
DocuFlow AI — Configuration centralisée
Toutes les variables d'environnement et constantes de l'application.
"""

import os

# ── Base de données ──────────────────────────────────────────────────
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "pfa_documents")
DB_USER = os.getenv("POSTGRES_USER", "pfa_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "pfa_secure_password_2025")

# ── Mistral AI ───────────────────────────────────────────────────────
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_OCR_MODEL = "mistral-ocr-latest"
MISTRAL_CHAT_MODEL = "mistral-small-latest"

# ── n8n ──────────────────────────────────────────────────────────────
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/facture")

# ── JWT / Authentification ───────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "docuflow-secret-key-change-in-production-2025")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# ── Rôles utilisateur ───────────────────────────────────────────────
ROLES = {
    "admin": {"label": "Administrateur", "level": 3},
    "comptable": {"label": "Comptable", "level": 2},
    "lecteur": {"label": "Lecteur", "level": 1},
}

# ── Application ─────────────────────────────────────────────────────
APP_NAME = "DocuFlow AI"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Traitement Intelligent de Documents Commerciaux"

# ── Formats supportés ───────────────────────────────────────────────
SUPPORTED_FORMATS = ["png", "jpg", "jpeg", "pdf", "tiff", "bmp", "webp"]
MAX_FILE_SIZE_MB = 10

# ── Types de documents ──────────────────────────────────────────────
DOCUMENT_TYPES = {
    "facture": "Facture",
    "bon_livraison": "Bon de Livraison",
    "recu": "Reçu",
    "autre": "Autre",
}

# ── Taux TVA Tunisie ────────────────────────────────────────────────
TVA_RATES_TUNISIA = [0, 7, 13, 19]
