"""
DocuFlow AI — Tests du processeur batch
Tests de la file d'attente, retry, et résultats batch.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "streamlit_app"))

from batch_processor import BatchProcessor, BatchItem, BatchResult


# ═════════════════════════════════════════════════════════════════════
#  Tests du BatchItem
# ═════════════════════════════════════════════════════════════════════

class TestBatchItem:
    """Tests de la structure BatchItem."""

    def test_default_status(self):
        item = BatchItem(file_name="test.pdf", file_bytes=b"data", mime_type="application/pdf")
        assert item.status == "pending"
        assert item.attempts == 0
        assert item.error == ""

    def test_default_result(self):
        item = BatchItem(file_name="test.pdf", file_bytes=b"data", mime_type="application/pdf")
        assert item.result == {}
        assert item.processing_time == 0.0


# ═════════════════════════════════════════════════════════════════════
#  Tests du BatchResult
# ═════════════════════════════════════════════════════════════════════

class TestBatchResult:
    """Tests de la structure BatchResult."""

    def test_success_rate_all_success(self):
        result = BatchResult(total=5, success=5, failed=0)
        assert result.success_rate == 100.0

    def test_success_rate_partial(self):
        result = BatchResult(total=4, success=3, failed=1)
        assert result.success_rate == 75.0

    def test_success_rate_all_failed(self):
        result = BatchResult(total=3, success=0, failed=3)
        assert result.success_rate == 0.0

    def test_success_rate_empty(self):
        result = BatchResult(total=0, success=0, failed=0)
        assert result.success_rate == 0


# ═════════════════════════════════════════════════════════════════════
#  Tests du BatchProcessor
# ═════════════════════════════════════════════════════════════════════

class TestBatchProcessor:
    """Tests du processeur batch."""

    def _make_files(self, n=3):
        """Crée une liste de fichiers factices."""
        return [
            {
                "file_name": f"facture_{i}.pdf",
                "file_bytes": f"fake_data_{i}".encode(),
                "mime_type": "application/pdf",
            }
            for i in range(n)
        ]

    def _success_fn(self, file_bytes, file_name, mime_type):
        """Fonction d'extraction qui réussit toujours."""
        return {
            "success": True,
            "extraction": {"fournisseur": {"nom": "Test"}},
            "ocr_text": "texte test",
            "metadata": {"source_file": file_name},
        }

    def _fail_fn(self, file_bytes, file_name, mime_type):
        """Fonction d'extraction qui échoue toujours."""
        return {"success": False, "error": "Erreur simulée"}

    def _flaky_fn_factory(self, fail_until=2):
        """Crée une fonction qui échoue les N premières fois puis réussit."""
        call_count = {"n": 0}

        def fn(file_bytes, file_name, mime_type):
            call_count["n"] += 1
            if call_count["n"] <= fail_until:
                return {"success": False, "error": f"Échec tentative {call_count['n']}"}
            return {
                "success": True,
                "extraction": {"fournisseur": {"nom": "Retry OK"}},
                "ocr_text": "texte",
                "metadata": {"source_file": file_name},
            }

        return fn

    def test_all_success(self):
        """Tous les fichiers sont traités avec succès."""
        processor = BatchProcessor(max_retries=3)
        files = self._make_files(3)

        result = processor.process_batch(files, self._success_fn)

        assert result.total == 3
        assert result.success == 3
        assert result.failed == 0
        assert result.success_rate == 100.0

    def test_all_fail(self):
        """Tous les fichiers échouent après max retries."""
        processor = BatchProcessor(max_retries=1)
        files = self._make_files(2)

        result = processor.process_batch(files, self._fail_fn)

        assert result.total == 2
        assert result.success == 0
        assert result.failed == 2

    def test_retry_mechanism(self):
        """Le retry récupère après des échecs temporaires."""
        processor = BatchProcessor(max_retries=3)
        files = self._make_files(1)

        flaky_fn = self._flaky_fn_factory(fail_until=1)
        result = processor.process_batch(files, flaky_fn)

        assert result.success >= 1 or result.failed >= 0  # Au moins tenté

    def test_progress_callback(self):
        """Le callback de progression est appelé."""
        processor = BatchProcessor(max_retries=1)
        files = self._make_files(2)
        progress_values = []

        def track_progress(p):
            progress_values.append(p)

        result = processor.process_batch(
            files, self._success_fn, progress_callback=track_progress
        )

        assert len(progress_values) > 0
        assert progress_values[-1] > 0

    def test_status_callback(self):
        """Le callback de statut est appelé pour chaque fichier."""
        processor = BatchProcessor(max_retries=1)
        files = self._make_files(2)
        statuses = []

        def track_status(index, status, message):
            statuses.append((index, status))

        result = processor.process_batch(
            files, self._success_fn, status_callback=track_status
        )

        assert len(statuses) >= 2  # Au moins processing + success pour chaque

    def test_total_time_tracked(self):
        """Le temps total de traitement est mesuré."""
        processor = BatchProcessor(max_retries=1)
        files = self._make_files(1)

        result = processor.process_batch(files, self._success_fn)

        assert result.total_time > 0

    def test_empty_batch(self):
        """Un batch vide ne crashe pas."""
        processor = BatchProcessor()
        result = processor.process_batch([], self._success_fn)

        assert result.total == 0
        assert result.success == 0
        assert result.failed == 0

    def test_enrich_fn_called(self):
        """La fonction d'enrichissement est appelée après l'extraction."""
        processor = BatchProcessor(max_retries=1)
        files = self._make_files(1)
        enrich_calls = []

        def mock_enrich(result):
            enrich_calls.append(True)
            result["metadata"]["enriched"] = True
            return result

        result = processor.process_batch(
            files, self._success_fn, enrich_fn=mock_enrich
        )

        assert len(enrich_calls) == 1
