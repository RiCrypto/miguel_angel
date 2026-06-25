"""
miguel_angel — MiguelBot Embedding Engine
Data Scientist implementation · Phase 3

Embedding backends (in priority order):

  1. Ollama — nomic-embed-text (768-dim, CPU-only, offline, best quality)
  2. sentence-transformers — all-MiniLM-L6-v2 (384-dim, CPU-only, pip-installable)
  3. Simple TF-IDF bag-of-words (128-dim, always available, for CI/testing)

The active backend is auto-detected at startup and exposed via embed().
Users can override in Preferences (MiguelBot → Embedding backend).
"""

from __future__ import annotations

import logging
import hashlib
import json
import math
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("miguel_angel.miguelbot.embeddings")


class EmbeddingBackend(str, Enum):
    OLLAMA     = "ollama"
    SENTENCE_T = "sentence_transformers"
    TFIDF      = "tfidf"


# ─────────────────────────────────────────────────────────────────────────────
# Backend implementations
# ─────────────────────────────────────────────────────────────────────────────

class OllamaEmbedder:
    """
    nomic-embed-text via Ollama local server.
    Install: ollama pull nomic-embed-text
    Runs on CPU, 768-dimensional output.
    """
    MODEL = "nomic-embed-text"
    DIM   = 768

    def __init__(self):
        import httpx
        self._client = httpx.Client(base_url="http://localhost:11434", timeout=30.0)

    def embed(self, text: str) -> list[float]:
        resp = self._client.post(
            "/api/embeddings",
            json={"model": self.MODEL, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    @property
    def dim(self) -> int:
        return self.DIM

    @classmethod
    def is_available(cls) -> bool:
        try:
            import httpx
            resp = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
            models = [m["name"] for m in resp.json().get("models", [])]
            return any(cls.MODEL in m for m in models)
        except Exception:
            return False


class SentenceTransformerEmbedder:
    """
    sentence-transformers/all-MiniLM-L6-v2 — local pip package.
    Install: pip install sentence-transformers
    384-dimensional output, CPU-only.
    """
    MODEL = "all-MiniLM-L6-v2"
    DIM   = 384

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self.MODEL)

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, convert_to_numpy=True).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, convert_to_numpy=True).tolist()

    @property
    def dim(self) -> int:
        return self.DIM

    @classmethod
    def is_available(cls) -> bool:
        try:
            import sentence_transformers  # noqa: F401
            return True
        except ImportError:
            return False


class TFIDFEmbedder:
    """
    Simple TF-IDF bag-of-words embedding.
    No external dependencies — always available.
    Used in CI/testing and as last-resort fallback.
    128-dimensional output.
    """
    DIM = 128

    # Vocabulary seeded with domain-specific electrical/instrumentation terms
    _VOCAB = [
        "temperature", "pressure", "flow", "level", "indicator", "controller",
        "transmitter", "valve", "switch", "relay", "contactor", "motor",
        "breaker", "fuse", "overload", "transformer", "terminal", "ground",
        "power", "signal", "ISA", "IEC", "ANSI", "IEEE", "PLC", "SCADA",
        "HMI", "DCS", "ERC", "netlist", "schematic", "wire", "net", "pin",
        "component", "symbol", "library", "drawing", "diagram", "loop",
        "instrument", "process", "pneumatic", "electric", "hydraulic",
        "sensor", "actuator", "converter", "positioner", "annunciator",
        "AND", "OR", "NOT", "gate", "logic", "interlock", "timer", "alarm",
        "miguel", "angel", "project", "sheet", "export", "DXF", "PDF",
        "save", "open", "file", "window", "canvas", "zoom", "grid", "snap",
        "install", "setup", "profile", "password", "authentication", "TOTP",
        "error", "warning", "connection", "disconnect", "unconnected", "short",
        "resistor", "capacitor", "inductor", "diode", "transistor", "opamp",
        "voltage", "current", "frequency", "analog", "digital", "BOM", "cost",
        "manufacturer", "datasheet", "part", "number", "revision", "version",
        "4-20mA", "24VDC", "RTD", "thermocouple", "modbus", "ethernet",
        "calibration", "range", "setpoint", "output", "input", "bidirectional",
        "MiguelBot", "RAG", "search", "question", "answer", "help", "guide",
        "documentation", "tutorial", "example", "how", "what", "why", "when",
    ] + [f"term_{i}" for i in range(128 - 72)]  # pad to 128 terms

    def __init__(self):
        self._vocab = {w.lower(): i for i, w in enumerate(self._VOCAB[:self.DIM])}

    def embed(self, text: str) -> list[float]:
        words = text.lower().split()
        tf: dict[int, float] = {}
        for word in words:
            # try exact and stemmed (first 5 chars)
            for key in (word, word[:5]):
                if key in self._vocab:
                    idx = self._vocab[key]
                    tf[idx] = tf.get(idx, 0.0) + 1.0
                    break

        # Normalise to unit vector
        vec = [0.0] * self.DIM
        for idx, count in tf.items():
            vec[idx] = count / max(len(words), 1)

        mag = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / mag for v in vec]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    @property
    def dim(self) -> int:
        return self.DIM

    @classmethod
    def is_available(cls) -> bool:
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Auto-detecting embedder
# ─────────────────────────────────────────────────────────────────────────────

class EmbeddingEngine:
    """
    Auto-detecting embedding engine.
    Probes Ollama → sentence-transformers → TF-IDF in order.
    Active backend is cached after first probe.
    """

    def __init__(self, force_backend: Optional[EmbeddingBackend] = None):
        self._force    = force_backend
        self._backend: Optional[object] = None
        self._backend_name: Optional[str] = None

    def _init_backend(self):
        if self._force == EmbeddingBackend.OLLAMA or self._force is None:
            if OllamaEmbedder.is_available():
                try:
                    self._backend      = OllamaEmbedder()
                    self._backend_name = EmbeddingBackend.OLLAMA
                    logger.info("Embedding backend: Ollama nomic-embed-text (768-dim)")
                    return
                except Exception as exc:
                    logger.warning("Ollama init failed: %s", exc)

        if self._force == EmbeddingBackend.SENTENCE_T or self._force is None:
            if SentenceTransformerEmbedder.is_available():
                try:
                    self._backend      = SentenceTransformerEmbedder()
                    self._backend_name = EmbeddingBackend.SENTENCE_T
                    logger.info("Embedding backend: sentence-transformers all-MiniLM-L6-v2 (384-dim)")
                    return
                except Exception as exc:
                    logger.warning("sentence-transformers init failed: %s", exc)

        self._backend      = TFIDFEmbedder()
        self._backend_name = EmbeddingBackend.TFIDF
        logger.info("Embedding backend: TF-IDF (128-dim, fallback)")

    @property
    def backend(self) -> object:
        if self._backend is None:
            self._init_backend()
        return self._backend

    @property
    def backend_name(self) -> str:
        if self._backend_name is None:
            self._init_backend()
        return self._backend_name

    @property
    def dim(self) -> int:
        return self.backend.dim

    def embed(self, text: str) -> list[float]:
        """Embed a single text string. Returns a list of floats."""
        return self.backend.embed(text.strip())

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts. Returns list of embedding vectors."""
        return self.backend.embed_batch([t.strip() for t in texts])
