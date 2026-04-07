"""
DocuFlow AI — Fixtures pytest
Mocks pour la BDD, l'API Mistral, et les données de test.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Ajouter le répertoire streamlit_app au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "streamlit_app"))


# ── Données de test ─────────────────────────────────────────────────

@pytest.fixture
def sample_extraction():
    """Données d'extraction typiques pour une facture tunisienne."""
    return {
        "fournisseur": {
            "nom": "Société ABC SARL",
            "adresse": "12 Rue de Carthage, Tunis 1000",
            "telephone": "+216 71 123 456",
            "email": "contact@abc.tn",
            "matricule_fiscal": "1234567/A/B/C/000"
        },
        "client": {
            "nom": "Client XYZ",
            "adresse": "45 Avenue de la République, Sfax"
        },
        "facture": {
            "numero": "FAC-2025-001",
            "date": "2025-03-15",
            "devise": "TND"
        },
        "articles": [
            {
                "designation": "Service de consultation",
                "quantite": 2,
                "prix_unitaire": 150.000,
                "total_ligne": 300.000
            },
            {
                "designation": "Licence logiciel annuelle",
                "quantite": 1,
                "prix_unitaire": 500.000,
                "total_ligne": 500.000
            }
        ],
        "totaux": {
            "total_ht": 800.000,
            "total_tva": 152.000,
            "total_ttc": 952.000,
            "timbre_fiscal": 1.000,
            "tva_details": [
                {"taux_pourcent": 19, "montant": 152.000}
            ]
        }
    }


@pytest.fixture
def sample_extraction_invalid():
    """Extraction avec des incohérences intentionnelles."""
    return {
        "fournisseur": {"nom": None, "adresse": None},
        "client": {"nom": "", "adresse": ""},
        "facture": {"numero": None, "date": None, "devise": "TND"},
        "articles": [
            {
                "designation": "Produit A",
                "quantite": 3,
                "prix_unitaire": 100.000,
                "total_ligne": 250.000  # Incohérent: 3 × 100 = 300 ≠ 250
            }
        ],
        "totaux": {
            "total_ht": 250.000,
            "total_tva": 100.000,
            "total_ttc": 400.000,  # Incohérent: 250 + 100 = 350 ≠ 400
            "timbre_fiscal": None,
            "tva_details": [
                {"taux_pourcent": 25, "montant": 100.000}  # Taux non standard
            ]
        }
    }


@pytest.fixture
def sample_ocr_text():
    """Exemple de texte OCR brut."""
    return """
    SOCIETE ABC SARL
    12 Rue de Carthage, Tunis 1000
    Tél: +216 71 123 456
    MF: 1234567/A/B/C/000

    FACTURE N° FAC-2025-001
    Date: 15/03/2025

    Client: Client XYZ
    45 Avenue de la République, Sfax

    Désignation          Qté  P.U.     Total
    Service consultation  2    150,000  300,000
    Licence logiciel      1    500,000  500,000

    Total HT:   800,000 TND
    TVA 19%:    152,000 TND
    Total TTC:  952,000 TND
    Timbre:       1,000 TND
    """


@pytest.fixture
def sample_result(sample_extraction, sample_ocr_text):
    """Résultat complet d'extraction (tel que retourné par extract_with_mistral)."""
    return {
        "success": True,
        "extraction": sample_extraction,
        "ocr_text": sample_ocr_text,
        "metadata": {
            "source_file": "facture_test.pdf",
            "file_type": "application/pdf",
            "extraction_date": "2025-03-15T10:00:00",
            "model_used": "mistral-ocr-latest + mistral-small-latest",
            "validation_warnings": [],
            "is_valid": True,
            "nombre_articles": 2,
            "ocr_text_length": 450,
            "mode": "mistral_ocr",
        }
    }


@pytest.fixture
def sample_document_db(sample_extraction):
    """Document tel que stocké en BDD (structure plate)."""
    return {
        "id": 1,
        "user_id": 1,
        "file_name": "facture_test.pdf",
        "file_type": "application/pdf",
        "document_type": "facture",
        "fournisseur_nom": "Société ABC SARL",
        "fournisseur_adresse": "12 Rue de Carthage, Tunis 1000",
        "fournisseur_telephone": "+216 71 123 456",
        "fournisseur_email": "contact@abc.tn",
        "fournisseur_matricule_fiscal": "1234567/A/B/C/000",
        "client_nom": "Client XYZ",
        "client_adresse": "45 Avenue de la République, Sfax",
        "facture_numero": "FAC-2025-001",
        "facture_date": "2025-03-15",
        "facture_devise": "TND",
        "total_ht": 800.000,
        "total_tva": 152.000,
        "total_ttc": 952.000,
        "timbre_fiscal": 1.000,
        "raw_json": sample_extraction,
        "model_used": "mistral-ocr-latest",
        "is_valid": True,
        "confidence_score": 0.85,
        "document_class": "facture",
        "created_at": "2025-03-15 10:00:00",
    }


@pytest.fixture
def mock_mistral_client():
    """Mock du client Mistral pour les tests sans API."""
    mock = MagicMock()

    # Mock OCR response
    mock_page = MagicMock()
    mock_page.markdown = "FACTURE N° 001\nTotal TTC: 952,000 TND"
    mock_ocr_response = MagicMock()
    mock_ocr_response.pages = [mock_page]
    mock.ocr.process.return_value = mock_ocr_response

    # Mock Chat response
    mock_choice = MagicMock()
    mock_choice.message.content = '{"type": "facture", "confidence": 0.95, "raison": "test"}'
    mock_chat_response = MagicMock()
    mock_chat_response.choices = [mock_choice]
    mock.chat.complete.return_value = mock_chat_response

    return mock
