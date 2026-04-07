"""
DocuFlow AI — Tests du moteur OCR
Tests de parsing JSON, MIME types, pipeline.
"""

import pytest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "streamlit_app"))


# ═════════════════════════════════════════════════════════════════════
#  Tests des MIME types
# ═════════════════════════════════════════════════════════════════════

class TestMimeType:
    """Tests de la détection MIME type."""

    def test_pdf_mime(self):
        from ocr_engine import get_mime_type
        assert get_mime_type("facture.pdf") == "application/pdf"

    def test_png_mime(self):
        from ocr_engine import get_mime_type
        assert get_mime_type("scan.png") == "image/png"

    def test_jpg_mime(self):
        from ocr_engine import get_mime_type
        assert get_mime_type("photo.jpg") == "image/jpeg"

    def test_jpeg_mime(self):
        from ocr_engine import get_mime_type
        assert get_mime_type("photo.jpeg") == "image/jpeg"

    def test_tiff_mime(self):
        from ocr_engine import get_mime_type
        assert get_mime_type("scan.tiff") == "image/tiff"

    def test_webp_mime(self):
        from ocr_engine import get_mime_type
        assert get_mime_type("image.webp") == "image/webp"

    def test_unknown_extension_uses_fallback(self):
        from ocr_engine import get_mime_type
        result = get_mime_type("file.xyz", "application/octet-stream")
        assert result == "application/octet-stream"

    def test_no_extension_uses_fallback(self):
        from ocr_engine import get_mime_type
        result = get_mime_type("noext")
        assert result == "image/jpeg"  # Default fallback


# ═════════════════════════════════════════════════════════════════════
#  Tests du parsing JSON structuré
# ═════════════════════════════════════════════════════════════════════

class TestExtractStructuredData:
    """Tests de extract_structured_data via mock."""

    def test_parses_clean_json(self, mock_mistral_client):
        """Parse correctement une réponse JSON propre."""
        from ocr_engine import extract_structured_data

        # Configurer le mock pour retourner du JSON valide
        mock_mistral_client.chat.complete.return_value.choices[0].message.content = json.dumps({
            "fournisseur": {"nom": "Test SARL"},
            "client": {"nom": "Client Test"},
            "facture": {"numero": "F-001", "date": "2025-01-01", "devise": "TND"},
            "articles": [],
            "totaux": {"total_ht": 100, "total_tva": 19, "total_ttc": 119}
        })

        result = extract_structured_data(mock_mistral_client, "texte OCR test")
        assert result["fournisseur"]["nom"] == "Test SARL"
        assert result["totaux"]["total_ttc"] == 119

    def test_parses_json_with_markdown_wrapper(self, mock_mistral_client):
        """Parse du JSON enveloppé dans des balises markdown ```json ... ```."""
        from ocr_engine import extract_structured_data

        mock_mistral_client.chat.complete.return_value.choices[0].message.content = \
            '```json\n{"fournisseur": {"nom": "ABC"}, "facture": {"numero": "001"}, "articles": [], "totaux": {}}\n```'

        result = extract_structured_data(mock_mistral_client, "texte")
        assert result["fournisseur"]["nom"] == "ABC"

    def test_raises_on_no_json(self, mock_mistral_client):
        """Lève une erreur si la réponse ne contient pas de JSON."""
        from ocr_engine import extract_structured_data

        mock_mistral_client.chat.complete.return_value.choices[0].message.content = \
            "Désolé, je ne peux pas extraire les données de ce document."

        with pytest.raises(ValueError, match="Pas de JSON"):
            extract_structured_data(mock_mistral_client, "texte")


# ═════════════════════════════════════════════════════════════════════
#  Tests du pipeline complet
# ═════════════════════════════════════════════════════════════════════

class TestExtractWithMistral:
    """Tests du pipeline complet extract_with_mistral."""

    def test_fails_without_api_key(self):
        """Retourne une erreur si la clé API est manquante."""
        from unittest.mock import patch
        from ocr_engine import extract_with_mistral

        with patch("ocr_engine.MISTRAL_API_KEY", ""):
            result = extract_with_mistral(b"fake_bytes", "test.pdf", "application/pdf")
            assert result["success"] is False
            assert "Clé API" in result["error"]

    def test_success_result_structure(self, mock_mistral_client):
        """Vérifie la structure du résultat en cas de succès."""
        from unittest.mock import patch
        from ocr_engine import extract_with_mistral

        # Setup mock pour retourner un JSON valide
        mock_mistral_client.chat.complete.return_value.choices[0].message.content = json.dumps({
            "fournisseur": {"nom": "Test"},
            "client": {"nom": "Client"},
            "facture": {"numero": "001", "date": "2025-01-01", "devise": "TND"},
            "articles": [{"designation": "Item", "quantite": 1, "prix_unitaire": 100, "total_ligne": 100}],
            "totaux": {"total_ht": 100, "total_tva": 19, "total_ttc": 119}
        })

        with patch("ocr_engine.MISTRAL_API_KEY", "test_key"):
            with patch("ocr_engine.Mistral", return_value=mock_mistral_client):
                result = extract_with_mistral(b"fake_bytes", "test.pdf", "application/pdf")

        assert result["success"] is True
        assert "extraction" in result
        assert "metadata" in result
        assert "ocr_text" in result
        assert result["metadata"]["mode"] == "mistral_ocr"


# ═════════════════════════════════════════════════════════════════════
#  Tests de la configuration
# ═════════════════════════════════════════════════════════════════════

class TestConfig:
    """Tests de la configuration de l'application."""

    def test_supported_formats(self):
        from config import SUPPORTED_FORMATS
        assert "pdf" in SUPPORTED_FORMATS
        assert "png" in SUPPORTED_FORMATS
        assert "jpg" in SUPPORTED_FORMATS

    def test_document_types(self):
        from config import DOCUMENT_TYPES
        assert "facture" in DOCUMENT_TYPES
        assert "bon_livraison" in DOCUMENT_TYPES
        assert "recu" in DOCUMENT_TYPES

    def test_tva_rates(self):
        from config import TVA_RATES_TUNISIA
        assert 19 in TVA_RATES_TUNISIA
        assert 7 in TVA_RATES_TUNISIA
        assert 0 in TVA_RATES_TUNISIA
