-- =====================================================================
--  DocuFlow AI — Script d'initialisation PostgreSQL
--  Tables : users, documents, articles, tva_details, audit_logs
-- =====================================================================

-- ── Table des utilisateurs ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'lecteur'
        CHECK (role IN ('admin', 'comptable', 'lecteur')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- ── Table principale des documents traités ──────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    file_name VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    document_type VARCHAR(50) DEFAULT 'facture',

    -- Données fournisseur
    fournisseur_nom VARCHAR(500),
    fournisseur_adresse TEXT,
    fournisseur_telephone VARCHAR(100),
    fournisseur_email VARCHAR(255),
    fournisseur_matricule_fiscal VARCHAR(100),

    -- Données client
    client_nom VARCHAR(500),
    client_adresse TEXT,

    -- Données facture
    facture_numero VARCHAR(100),
    facture_date DATE,
    facture_devise VARCHAR(10) DEFAULT 'TND',

    -- Totaux
    total_ht DECIMAL(15, 3),
    total_tva DECIMAL(15, 3),
    total_ttc DECIMAL(15, 3),
    timbre_fiscal DECIMAL(15, 3),

    -- Métadonnées IA
    raw_json JSONB,
    model_used VARCHAR(100) DEFAULT 'mistral-ocr-latest',
    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN DEFAULT false,
    validation_warnings TEXT[],
    confidence_score DECIMAL(3, 2),
    document_class VARCHAR(50) DEFAULT 'facture',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Table des articles/lignes de chaque document ────────────────────
CREATE TABLE IF NOT EXISTS document_articles (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    reference VARCHAR(200),
    designation VARCHAR(1000) NOT NULL,
    quantite DECIMAL(15, 3),
    prix_unitaire DECIMAL(15, 3),
    total_ligne DECIMAL(15, 3),
    ligne_numero INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Table des détails TVA ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS document_tva_details (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    taux_pourcent DECIMAL(5, 2),
    montant DECIMAL(15, 3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Table des logs d'audit ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Index de performance ────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_fournisseur ON documents(fournisseur_nom);
CREATE INDEX IF NOT EXISTS idx_documents_facture_numero ON documents(facture_numero);
CREATE INDEX IF NOT EXISTS idx_documents_facture_date ON documents(facture_date);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_class ON documents(document_class);
CREATE INDEX IF NOT EXISTS idx_articles_document_id ON document_articles(document_id);
CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at);

-- L'utilisateur admin est créé automatiquement au démarrage de l'application
