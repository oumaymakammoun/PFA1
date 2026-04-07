"""
DocuFlow AI — Tests du moteur IA
Tests de classification, validation et scores de confiance.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "streamlit_app"))


# ═════════════════════════════════════════════════════════════════════
#  Tests de validation intelligente
# ═════════════════════════════════════════════════════════════════════

class TestValidateExtraction:
    """Tests de la fonction validate_extraction."""

    def test_valid_invoice_no_anomalies(self, sample_extraction):
        """Une facture correcte ne doit produire aucune anomalie."""
        from ai_engine import validate_extraction

        anomalies = validate_extraction(sample_extraction)
        errors = [a for a in anomalies if a["severity"] == "error"]
        assert len(errors) == 0, f"Anomalies inattendues : {errors}"

    def test_detects_ttc_mismatch(self, sample_extraction):
        """Détecte quand TTC ≠ HT + TVA."""
        from ai_engine import validate_extraction

        sample_extraction["totaux"]["total_ttc"] = 999.000
        anomalies = validate_extraction(sample_extraction)

        ttc_anomalies = [a for a in anomalies if a["field"] == "total_ttc"]
        assert len(ttc_anomalies) > 0, "L'écart TTC aurait dû être détecté"

    def test_detects_article_line_mismatch(self, sample_extraction_invalid):
        """Détecte quand quantité × prix_unitaire ≠ total_ligne."""
        from ai_engine import validate_extraction

        anomalies = validate_extraction(sample_extraction_invalid)
        article_anomalies = [a for a in anomalies if "articles" in a["field"]]
        assert len(article_anomalies) > 0, "L'incohérence article aurait dû être détectée"

    def test_detects_non_standard_tva(self, sample_extraction_invalid):
        """Détecte les taux TVA non standards en Tunisie (0, 7, 13, 19)."""
        from ai_engine import validate_extraction

        anomalies = validate_extraction(sample_extraction_invalid)
        tva_anomalies = [a for a in anomalies if "tva_details" in a["field"]]
        assert len(tva_anomalies) > 0, "Le taux TVA 25% aurait dû être signalé"

    def test_detects_negative_amounts(self):
        """Détecte les montants négatifs."""
        from ai_engine import validate_extraction

        extraction = {
            "totaux": {"total_ht": -100, "total_tva": 19, "total_ttc": -81},
            "articles": []
        }
        anomalies = validate_extraction(extraction)
        negative_anomalies = [a for a in anomalies if "négatif" in a["issue"]]
        assert len(negative_anomalies) > 0

    def test_detects_high_amount_info(self):
        """Signale les montants > 1M TND comme info."""
        from ai_engine import validate_extraction

        extraction = {
            "totaux": {
                "total_ht": 1_000_000, "total_tva": 190_000,
                "total_ttc": 1_190_000
            },
            "articles": []
        }
        anomalies = validate_extraction(extraction)
        info_anomalies = [a for a in anomalies if a["severity"] == "info"]
        assert len(info_anomalies) > 0

    def test_empty_extraction(self):
        """Une extraction vide ne doit pas crasher."""
        from ai_engine import validate_extraction

        anomalies = validate_extraction({})
        assert isinstance(anomalies, list)

    def test_tolerance_arrondi(self, sample_extraction):
        """Les écarts < 1 TND doivent être tolérés (arrondis)."""
        from ai_engine import validate_extraction

        sample_extraction["totaux"]["total_ttc"] = 952.500  # Écart de 0.5
        anomalies = validate_extraction(sample_extraction)
        ttc_anomalies = [a for a in anomalies if a["field"] == "total_ttc"]
        assert len(ttc_anomalies) == 0, "Un écart de 0.5 TND devrait être toléré"


# ═════════════════════════════════════════════════════════════════════
#  Tests des scores de confiance
# ═════════════════════════════════════════════════════════════════════

class TestConfidenceScores:
    """Tests de compute_confidence_scores."""

    def test_computes_global_score(self, sample_ocr_text, sample_extraction):
        """Le score global doit être calculé entre 0 et 1."""
        from ai_engine import compute_confidence_scores

        scores = compute_confidence_scores(sample_ocr_text, sample_extraction)
        assert "global" in scores
        assert 0.0 <= scores["global"] <= 1.0

    def test_all_sections_scored(self, sample_ocr_text, sample_extraction):
        """Toutes les sections doivent avoir un score."""
        from ai_engine import compute_confidence_scores

        scores = compute_confidence_scores(sample_ocr_text, sample_extraction)
        expected_sections = ["fournisseur", "client", "facture", "articles", "totaux", "global"]
        for section in expected_sections:
            assert section in scores, f"Section '{section}' manquante"

    def test_high_score_when_text_matches(self, sample_ocr_text, sample_extraction):
        """Score élevé quand les données correspondent au texte OCR."""
        from ai_engine import compute_confidence_scores

        scores = compute_confidence_scores(sample_ocr_text, sample_extraction)
        assert scores["fournisseur"] >= 0.5, f"Score fournisseur trop bas: {scores['fournisseur']}"

    def test_low_score_on_empty_extraction(self, sample_ocr_text):
        """Score faible pour une extraction vide."""
        from ai_engine import compute_confidence_scores

        scores = compute_confidence_scores(sample_ocr_text, {
            "fournisseur": {}, "client": {}, "facture": {}, "articles": [], "totaux": {}
        })
        assert scores["articles"] == 0.0

    def test_empty_ocr_text(self, sample_extraction):
        """Gère proprement un texte OCR vide."""
        from ai_engine import compute_confidence_scores

        scores = compute_confidence_scores("", sample_extraction)
        assert isinstance(scores, dict)
        assert 0.0 <= scores.get("global", 0) <= 1.0


# ═════════════════════════════════════════════════════════════════════
#  Tests du label de confiance
# ═════════════════════════════════════════════════════════════════════

class TestConfidenceLabel:
    """Tests de get_confidence_label."""

    def test_high_confidence(self):
        from ai_engine import get_confidence_label
        label, css = get_confidence_label(0.9)
        assert label == "Élevée"
        assert css == "confidence-high"

    def test_medium_confidence(self):
        from ai_engine import get_confidence_label
        label, css = get_confidence_label(0.6)
        assert label == "Moyenne"
        assert css == "confidence-medium"

    def test_low_confidence(self):
        from ai_engine import get_confidence_label
        label, css = get_confidence_label(0.3)
        assert label == "Faible"
        assert css == "confidence-low"

    def test_boundary_high(self):
        from ai_engine import get_confidence_label
        label, _ = get_confidence_label(0.8)
        assert label == "Élevée"

    def test_boundary_medium(self):
        from ai_engine import get_confidence_label
        label, _ = get_confidence_label(0.5)
        assert label == "Moyenne"


# ═════════════════════════════════════════════════════════════════════
#  Tests de l'enrichissement pipeline
# ═════════════════════════════════════════════════════════════════════

class TestEnrichExtraction:
    """Tests de enrich_extraction."""

    def test_enriches_successful_result(self, sample_result, mock_mistral_client):
        """L'enrichissement ajoute classification, validation et confiance."""
        from unittest.mock import patch
        from ai_engine import enrich_extraction

        with patch("ai_engine._get_client", return_value=mock_mistral_client):
            enriched = enrich_extraction(sample_result)

        assert enriched["metadata"].get("document_type") is not None
        assert enriched["metadata"].get("confidence_score") is not None
        assert "anomalies" in enriched["metadata"]

    def test_skips_failed_result(self):
        """N'enrichit pas un résultat en échec."""
        from ai_engine import enrich_extraction

        result = {"success": False, "error": "Test error"}
        enriched = enrich_extraction(result)
        assert enriched == result
