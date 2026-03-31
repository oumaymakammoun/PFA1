-- =====================================================================
--  PFA Ollama — Script d'initialisation PostgreSQL
--  Crée la table pour stocker les extractions de documents
-- =====================================================================

-- Table principale des documents traités
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
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
    
    -- Métadonnées
    raw_json JSONB,
    model_used VARCHAR(100) DEFAULT 'qwen3-vl:8b',
    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN DEFAULT false,
    validation_warnings TEXT[],
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des articles/lignes de chaque document
CREATE TABLE IF NOT EXISTS document_articles (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    designation VARCHAR(1000) NOT NULL,
    quantite DECIMAL(15, 3),
    prix_unitaire DECIMAL(15, 3),
    total_ligne DECIMAL(15, 3),
    ligne_numero INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des détails TVA
CREATE TABLE IF NOT EXISTS document_tva_details (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    taux_pourcent DECIMAL(5, 2),
    montant DECIMAL(15, 3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour les recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_documents_fournisseur ON documents(fournisseur_nom);
CREATE INDEX IF NOT EXISTS idx_documents_facture_numero ON documents(facture_numero);
CREATE INDEX IF NOT EXISTS idx_documents_facture_date ON documents(facture_date);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_articles_document_id ON document_articles(document_id);
