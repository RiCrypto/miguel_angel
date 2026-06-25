"""
miguel_angel — MiguelBot ChromaDB Store
Data Scientist implementation · Phase 3

Manages four ChromaDB persistent collections:
  docs        — MkDocs markdown documentation
  components  — Component library symbol descriptions
  forum       — Resolved GitHub Discussion Q&A pairs
  erc_rules   — ERC rule explanations and fix guidance

Each collection uses the same embedding function.
The store is local-only — nothing is sent off-device.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
import os

import chromadb
from chromadb.config import Settings

logger = logging.getLogger("miguel_angel.miguelbot.store")

# Collection names
COL_DOCS       = "docs"
COL_COMPONENTS = "components"
COL_FORUM      = "forum"
COL_ERC        = "erc_rules"

ALL_COLLECTIONS = [COL_DOCS, COL_COMPONENTS, COL_FORUM, COL_ERC]

# Default similarity threshold for confident retrieval
CONFIDENCE_THRESHOLD = 0.72


def _get_store_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    elif hasattr(os, "uname") and os.uname().sysname == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "miguel_angel" / "miguelbot_store"
    path.mkdir(parents=True, exist_ok=True)
    return path


class VectorStore:
    """
    Persistent ChromaDB client with four named collections.

    Usage:
        store = VectorStore()
        store.connect()
        col = store.collection(COL_COMPONENTS)
        col.add(documents=["..."], metadatas=[{...}], ids=["id1"])
        results = store.query(COL_COMPONENTS, "temperature controller", n_results=5)
    """

    def __init__(self, path: Optional[Path] = None, in_memory: bool = False):
        self._path      = path or _get_store_path()
        self._in_memory = in_memory
        self._client: Optional[chromadb.ClientAPI] = None
        self._collections: dict[str, chromadb.Collection] = {}

    def connect(self) -> None:
        """Open (or create) the persistent ChromaDB store."""
        if self._in_memory:
            self._client = chromadb.EphemeralClient()
        else:
            self._client = chromadb.PersistentClient(
                path=str(self._path),
                settings=Settings(anonymized_telemetry=False),
            )
        for name in ALL_COLLECTIONS:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        logger.info(
            "VectorStore connected: %s (%s)",
            "in-memory" if self._in_memory else self._path,
            ", ".join(f"{n}:{self._collections[n].count()}" for n in ALL_COLLECTIONS),
        )

    def collection(self, name: str) -> chromadb.Collection:
        if self._client is None:
            raise RuntimeError("Call connect() first.")
        return self._collections[name]

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> dict:
        """
        Query a single collection by pre-computed embedding vector.
        Returns ChromaDB results dict with keys: ids, documents, metadatas, distances.
        """
        col = self.collection(collection_name)
        kwargs: dict = {"query_embeddings": [query_embedding], "n_results": min(n_results, max(col.count(), 1))}
        if where:
            kwargs["where"] = where
        return col.query(**kwargs)

    def count(self, collection_name: str) -> int:
        return self.collection(collection_name).count()

    def total_count(self) -> dict[str, int]:
        return {name: self.collection(name).count() for name in ALL_COLLECTIONS}

    def clear_collection(self, name: str) -> None:
        """Delete and recreate a collection (full re-index)."""
        if self._client:
            self._client.delete_collection(name)
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )

    def close(self) -> None:
        self._client = None
        self._collections.clear()
