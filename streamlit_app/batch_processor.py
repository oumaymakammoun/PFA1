"""
DocuFlow AI — Processeur Batch avec Retry
Traitement de plusieurs documents en file d'attente avec retry automatique.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Callable
from collections import deque

logger = logging.getLogger(__name__)


# ── Configuration ────────────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # Backoff exponentiel : 2s, 4s, 8s


@dataclass
class BatchItem:
    """Représente un document dans la file d'attente."""
    file_name: str
    file_bytes: bytes
    mime_type: str
    index: int = 0
    status: str = "pending"  # pending, processing, success, failed
    result: dict = field(default_factory=dict)
    attempts: int = 0
    error: str = ""
    processing_time: float = 0.0


@dataclass
class BatchResult:
    """Résultat global d'un traitement batch."""
    total: int = 0
    success: int = 0
    failed: int = 0
    retried: int = 0
    total_time: float = 0.0
    items: list = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return (self.success / self.total * 100) if self.total > 0 else 0


class BatchProcessor:
    """
    Processeur batch avec file d'attente et retry automatique.

    Utilise une deque (file d'attente FIFO) pour traiter les documents
    séquentiellement avec retry en cas d'échec (backoff exponentiel).

    Usage:
        processor = BatchProcessor()
        result = processor.process_batch(files, extract_fn, progress_callback)
    """

    def __init__(self, max_retries: int = MAX_RETRIES):
        self.max_retries = max_retries
        self.queue: deque[BatchItem] = deque()

    def process_batch(
        self,
        files: list[dict],
        extract_fn: Callable,
        enrich_fn: Callable = None,
        progress_callback: Callable = None,
        status_callback: Callable = None,
    ) -> BatchResult:
        """
        Traite une liste de fichiers en batch.

        Args:
            files: Liste de dicts {"file_name", "file_bytes", "mime_type"}
            extract_fn: Fonction d'extraction OCR (file_bytes, file_name, mime_type) -> dict
            enrich_fn: Fonction d'enrichissement IA (result) -> result (optionnel)
            progress_callback: Callback(progress: float) pour barre de progression
            status_callback: Callback(index: int, status: str, message: str)

        Returns:
            BatchResult avec les résultats détaillés
        """
        batch_start = time.time()

        # Initialiser la file d'attente
        self.queue.clear()
        for i, f in enumerate(files):
            item = BatchItem(
                file_name=f["file_name"],
                file_bytes=f["file_bytes"],
                mime_type=f["mime_type"],
                index=i,
            )
            self.queue.append(item)

        result = BatchResult(total=len(files))
        processed = 0

        # Traiter chaque élément de la file
        while self.queue:
            item = self.queue.popleft()
            item.status = "processing"
            item.attempts += 1

            if status_callback:
                status_callback(
                    item.index,
                    "processing",
                    f"📄 Traitement de {item.file_name} (tentative {item.attempts}/{self.max_retries})..."
                )

            item_start = time.time()

            try:
                # Extraction OCR
                extraction_result = extract_fn(
                    file_bytes=item.file_bytes,
                    file_name=item.file_name,
                    mime_type=item.mime_type,
                )

                if not extraction_result.get("success"):
                    raise Exception(extraction_result.get("error", "Extraction échouée"))

                # Enrichissement IA (si disponible)
                if enrich_fn:
                    extraction_result = enrich_fn(extraction_result)

                # Succès
                item.status = "success"
                item.result = extraction_result
                item.processing_time = time.time() - item_start
                result.success += 1

                if item.attempts > 1:
                    result.retried += 1

                if status_callback:
                    status_callback(
                        item.index, "success",
                        f"✅ {item.file_name} — extrait en {item.processing_time:.1f}s"
                    )

                logger.info(
                    f"Batch: {item.file_name} traité en {item.processing_time:.1f}s "
                    f"(tentative {item.attempts})"
                )

            except Exception as e:
                item.error = str(e)
                item.processing_time = time.time() - item_start

                if item.attempts < self.max_retries:
                    # Retry avec backoff exponentiel
                    wait_time = RETRY_BACKOFF_BASE ** item.attempts
                    if status_callback:
                        status_callback(
                            item.index, "retrying",
                            f"⏳ {item.file_name} échoué, retry dans {wait_time}s... ({e})"
                        )
                    time.sleep(wait_time)
                    self.queue.append(item)  # Remettre en file d'attente
                    logger.warning(
                        f"Batch: retry {item.file_name} (tentative {item.attempts}, "
                        f"erreur: {e})"
                    )
                else:
                    # Échec définitif après max retries
                    item.status = "failed"
                    result.failed += 1

                    if status_callback:
                        status_callback(
                            item.index, "failed",
                            f"❌ {item.file_name} — échec après {self.max_retries} tentatives : {e}"
                        )

                    logger.error(
                        f"Batch: {item.file_name} échoué définitivement après "
                        f"{self.max_retries} tentatives : {e}"
                    )

            processed += 1
            if progress_callback:
                progress_callback(processed / len(files))

            result.items.append(item)

        result.total_time = time.time() - batch_start
        return result
