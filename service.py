"""
miguel_angel — MiguelBot Service
Data Scientist implementation · Phase 3

Single entry point that the PyQt6 UI calls:
  bot = MiguelBotService()
  bot.start()
  answer = bot.ask("How do I wire a motor starter?", context)
  bot.stop()

Also provides the background thread wrapper for PyQt6 integration.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from .store      import VectorStore
from .embeddings import EmbeddingEngine, EmbeddingBackend
from .ingest     import IngestionPipeline
from .rag        import RAGEngine, RAGAnswer

logger = logging.getLogger("miguel_angel.miguelbot")

# ─────────────────────────────────────────────────────────────────────────────
# MiguelBot service
# ─────────────────────────────────────────────────────────────────────────────

class MiguelBotService:
    """
    High-level service that manages the full RAG lifecycle.

    Usage from PyQt6 panel:
        self.bot = MiguelBotService(docs_path=Path("docs/"), library_db=db)
        self.bot.start()                    # connect + ingest (idempotent)
        answer = self.bot.ask(question, ctx) # sync query
        self.bot.stop()                     # cleanup
    """

    def __init__(
        self,
        docs_path:       Optional[Path]   = None,
        library_db=None,
        store_path:      Optional[Path]   = None,
        embedding_backend: Optional[EmbeddingBackend] = None,
        ollama_model:    str              = "llama3",
        cloud_api_key:   Optional[str]   = None,
        cloud_base_url:  str              = "https://api.openai.com/v1",
        github_token:    Optional[str]   = None,
        in_memory:       bool             = False,
    ):
        self.docs_path        = docs_path
        self.library_db       = library_db
        self.github_token     = github_token
        self.in_memory        = in_memory

        self._store    = VectorStore(path=store_path, in_memory=in_memory)
        self._embedder = EmbeddingEngine(force_backend=embedding_backend)
        self._pipeline = IngestionPipeline(self._store, self._embedder)
        self._engine   = RAGEngine(
            store          = self._store,
            embedder       = self._embedder,
            ollama_model   = ollama_model,
            cloud_api_key  = cloud_api_key,
            cloud_base_url = cloud_base_url,
        )
        self._started  = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self, force_reindex: bool = False) -> None:
        """Connect to ChromaDB and ingest all knowledge sources (idempotent)."""
        if self._started and not force_reindex:
            return
        self._store.connect()
        self._ingest_all(force_reindex=force_reindex)
        self._started = True
        counts = self._store.total_count()
        logger.info(
            "MiguelBot started | backend: %s | docs: %d | components: %d | forum: %d | erc: %d",
            self._embedder.backend_name,
            counts.get("docs", 0),
            counts.get("components", 0),
            counts.get("forum", 0),
            counts.get("erc_rules", 0),
        )

    def _ingest_all(self, force_reindex: bool = False) -> None:
        # ERC rules — always available
        self._pipeline.ingest_erc_rules(force_reindex=force_reindex)

        # Documentation
        if self.docs_path and self.docs_path.exists():
            self._pipeline.ingest_docs(self.docs_path, force_reindex=force_reindex)
        else:
            logger.info("No docs_path provided — skipping docs ingestion")

        # Component library
        if self.library_db:
            self._pipeline.ingest_components(self.library_db, force_reindex=force_reindex)
        else:
            logger.info("No library_db provided — skipping component ingestion")

        # GitHub forum (optional — requires token)
        if self.github_token:
            self._pipeline.ingest_forum(
                repo_name   = "RiCrypto/miguel_angel",
                github_token = self.github_token,
                force_reindex = force_reindex,
            )

    def stop(self) -> None:
        self._store.close()
        self._started = False

    # ── Query API ─────────────────────────────────────────────────────────────

    def ask(
        self,
        question: str,
        schematic_context: Optional[dict] = None,
    ) -> RAGAnswer:
        """
        Answer a user question using the RAG pipeline.
        Thread-safe — can be called from a QThread worker.
        """
        if not self._started:
            self.start()
        return self._engine.query(question, schematic_context)

    def explain_erc(self, error_code: str, error_message: str) -> RAGAnswer:
        """Explain an ERC error and suggest a fix."""
        if not self._started:
            self.start()
        return self._engine.query_for_erc(error_code, error_message)

    def suggest_component(self, description: str) -> RAGAnswer:
        """Suggest a component from the library for a given use case."""
        if not self._started:
            self.start()
        return self._engine.query_for_component(description)

    def reindex(self) -> None:
        """Force a full re-index of all knowledge sources."""
        self._ingest_all(force_reindex=True)

    # ── Status ────────────────────────────────────────────────────────────────

    @property
    def status(self) -> dict:
        """Return status info for the MiguelBot UI panel header."""
        if not self._started:
            return {"online": False, "backend": "not started", "counts": {}}
        return {
            "online":  True,
            "backend": self._embedder.backend_name,
            "counts":  self._store.total_count(),
        }

    @property
    def is_ready(self) -> bool:
        return self._started
