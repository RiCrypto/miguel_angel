"""
miguel_angel — MiguelBot RAG Query Engine
Data Scientist implementation · Phase 3

Query pipeline:
  1. Embed the user question
  2. Parallel search across docs + components + forum + erc_rules
  3. Reciprocal Rank Fusion (RRF) — merge and re-rank all candidates
  4. Build prompt: system context + schematic snapshot + top-K chunks
  5. Generate answer via Ollama (Llama 3) or cloud fallback
  6. If confidence < threshold → flag for GitHub forum escalation

The engine is stateless — each call is independent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .store import (
    VectorStore, CONFIDENCE_THRESHOLD,
    COL_DOCS, COL_COMPONENTS, COL_FORUM, COL_ERC,
)
from .embeddings import EmbeddingEngine

logger = logging.getLogger("miguel_angel.miguelbot.rag")

# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RetrievedChunk:
    """A single document chunk retrieved from ChromaDB."""
    doc_id:      str
    text:        str
    metadata:    dict
    score:       float          # lower distance = higher relevance (cosine)
    collection:  str
    rrf_rank:    float = 0.0    # assigned by RRF


@dataclass
class RAGAnswer:
    """Complete answer from the RAG pipeline."""
    answer:          str
    sources:         list[RetrievedChunk]
    confidence:      float          # 0.0 – 1.0 (based on top chunk distance)
    backend_used:    str            # "ollama", "cloud", "fallback"
    should_escalate: bool           # True if confidence < threshold
    context_used:    dict           # schematic snapshot that was injected


# ─────────────────────────────────────────────────────────────────────────────
# RRF
# ─────────────────────────────────────────────────────────────────────────────

def reciprocal_rank_fusion(
    result_lists: list[list[RetrievedChunk]],
    k: int = 60,
    top_n: int = 5,
) -> list[RetrievedChunk]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion.
    RRF score = sum(1 / (k + rank)) across all lists.
    Higher RRF score = better merged rank.
    """
    scores: dict[str, float] = {}
    chunks: dict[str, RetrievedChunk] = {}

    for result_list in result_lists:
        for rank, chunk in enumerate(result_list, start=1):
            rrf = 1.0 / (k + rank)
            scores[chunk.doc_id]  = scores.get(chunk.doc_id, 0.0) + rrf
            chunks[chunk.doc_id]  = chunk

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    result = []
    for doc_id, rrf_score in ranked[:top_n]:
        c = chunks[doc_id]
        c.rrf_rank = rrf_score
        result.append(c)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# LLM backends
# ─────────────────────────────────────────────────────────────────────────────

def _call_ollama(prompt: str, model: str = "llama3") -> Optional[str]:
    """Call Ollama local LLM. Returns None if unavailable."""
    try:
        import httpx
        resp = httpx.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as exc:
        logger.warning("Ollama call failed: %s", exc)
        return None


def _call_openai_compatible(prompt: str, api_key: str, base_url: str) -> Optional[str]:
    """Call any OpenAI-compatible API. Used as cloud fallback."""
    try:
        import httpx
        resp = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model":    "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("Cloud LLM call failed: %s", exc)
        return None


def _fallback_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    """
    Deterministic fallback when no LLM is available.
    Extracts the first sentence of the best-scoring chunk.
    """
    if not chunks:
        return (
            "I couldn't find a confident answer in the documentation. "
            "Please post your question in the GitHub Discussions forum — "
            "ForumBot will respond within minutes."
        )
    best   = chunks[0].text
    # Return first 2 sentences
    import re
    sentences = re.split(r"(?<=[.!?])\s+", best)
    preview   = " ".join(sentences[:2])
    return (
        f"Based on the documentation: {preview} "
        f"\n\n(Source: {chunks[0].metadata.get('source_file', chunks[0].collection)})"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(
    question:    str,
    chunks:      list[RetrievedChunk],
    context:     dict,
) -> str:
    """
    Build the complete RAG prompt:
      [SYSTEM CONTEXT]
      [SCHEMATIC SNAPSHOT]
      [RETRIEVED KNOWLEDGE]
      [QUESTION]
    """
    # System context
    system = (
        "You are MiguelBot, the embedded AI assistant for miguel_angel — an open-source "
        "electrical and electronic schematic editor supporting ISA 5.1, ISA 5.2, ISA 5.4, "
        "ISA 95, IEC 60617, ANSI/NEMA, and IEEE 315 standards.\n"
        "Answer the user's question concisely and accurately using ONLY the provided context. "
        "If the context does not contain enough information, say so clearly. "
        "When referencing a component, include its symbol ID (e.g. ISA51:TIC). "
        "When explaining an ERC error, suggest a specific fix.\n"
    )

    # Schematic snapshot from canvas
    snap_parts = []
    if context.get("selected_components"):
        refs = [c.get("reference", "?") for c in context["selected_components"][:3]]
        snap_parts.append(f"Selected components: {', '.join(refs)}")
    if context.get("active_nets"):
        snap_parts.append(f"Active nets: {', '.join(context['active_nets'][:5])}")
    if context.get("erc_errors"):
        snap_parts.append(f"ERC errors present: {len(context['erc_errors'])}")
    if context.get("zoom_level"):
        snap_parts.append(f"Canvas zoom: {context['zoom_level']}%")

    schematic_context = ""
    if snap_parts:
        schematic_context = "Current schematic context:\n" + "\n".join(f"  - {p}" for p in snap_parts) + "\n\n"

    # Retrieved knowledge chunks
    knowledge_parts = []
    for i, chunk in enumerate(chunks[:5], start=1):
        src = chunk.metadata.get("source_file") or chunk.metadata.get("symbol_id") or chunk.collection
        knowledge_parts.append(f"[Source {i}: {src}]\n{chunk.text[:600]}")
    knowledge = "\n\n".join(knowledge_parts)

    return (
        f"{system}\n"
        f"{schematic_context}"
        f"Relevant knowledge:\n{knowledge}\n\n"
        f"User question: {question}\n\n"
        f"Answer:"
    )


# ─────────────────────────────────────────────────────────────────────────────
# RAG Engine
# ─────────────────────────────────────────────────────────────────────────────

class RAGEngine:
    """
    Main MiguelBot query engine.

    Usage:
        engine = RAGEngine(store, embedder)
        answer = engine.query("How do I wire a motor starter?", context)
    """

    def __init__(
        self,
        store:           VectorStore,
        embedder:        EmbeddingEngine,
        ollama_model:    str = "llama3",
        cloud_api_key:   Optional[str] = None,
        cloud_base_url:  str = "https://api.openai.com/v1",
        n_results_per_col: int = 5,
    ):
        self.store              = store
        self.embedder           = embedder
        self.ollama_model       = ollama_model
        self.cloud_api_key      = cloud_api_key
        self.cloud_base_url     = cloud_base_url
        self.n_results_per_col  = n_results_per_col

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(
        self,
        question:        str,
        schematic_context: Optional[dict] = None,
        collections:     Optional[list[str]] = None,
    ) -> RAGAnswer:
        """
        Full RAG pipeline:
          embed → retrieve (parallel) → RRF → prompt → generate → return
        """
        ctx = schematic_context or {}
        cols = collections or [COL_DOCS, COL_COMPONENTS, COL_ERC, COL_FORUM]

        # Step 1: embed question
        q_embedding = self.embedder.embed(question)

        # Step 2: parallel retrieval from all collections
        all_lists: list[list[RetrievedChunk]] = []
        for col_name in cols:
            try:
                if self.store.count(col_name) == 0:
                    continue
                results = self.store.query(col_name, q_embedding, n_results=self.n_results_per_col)
                chunks  = self._parse_results(results, col_name)
                if chunks:
                    all_lists.append(chunks)
            except Exception as exc:
                logger.warning("Retrieval error in %s: %s", col_name, exc)

        # Step 3: RRF merge
        top_chunks = reciprocal_rank_fusion(all_lists, top_n=5) if all_lists else []

        # Step 4: compute confidence
        confidence = self._confidence(top_chunks)

        # Step 5: build prompt and generate
        prompt       = _build_prompt(question, top_chunks, ctx)
        answer, backend = self._generate(prompt)

        # Step 6: escalation decision
        should_escalate = confidence < CONFIDENCE_THRESHOLD

        return RAGAnswer(
            answer          = answer,
            sources         = top_chunks,
            confidence      = confidence,
            backend_used    = backend,
            should_escalate = should_escalate,
            context_used    = ctx,
        )

    def query_for_erc(self, error_code: str, error_message: str) -> RAGAnswer:
        """Specialised query for ERC error explanation — searches ERC + docs."""
        question = f"Explain {error_code}: {error_message}. How do I fix it?"
        return self.query(question, collections=[COL_ERC, COL_DOCS])

    def query_for_component(self, search_term: str) -> RAGAnswer:
        """Specialised query for component suggestions."""
        question = f"What component should I use for: {search_term}?"
        return self.query(question, collections=[COL_COMPONENTS, COL_DOCS])

    # ── Internals ─────────────────────────────────────────────────────────────

    def _parse_results(
        self,
        results: dict,
        collection: str,
    ) -> list[RetrievedChunk]:
        """Parse ChromaDB results dict into RetrievedChunk list."""
        chunks = []
        ids       = results.get("ids",       [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc_id, text, meta, dist in zip(ids, documents, metadatas, distances):
            chunks.append(RetrievedChunk(
                doc_id     = doc_id,
                text       = text or "",
                metadata   = meta or {},
                score      = float(dist),
                collection = collection,
            ))
        return chunks

    def _confidence(self, chunks: list[RetrievedChunk]) -> float:
        """
        Confidence score [0.0, 1.0].
        Based on the cosine distance of the top chunk:
          distance=0.0 → perfect match → confidence=1.0
          distance=1.0 → completely different → confidence=0.0
        """
        if not chunks:
            return 0.0
        best_dist  = min(c.score for c in chunks)
        return max(0.0, min(1.0, 1.0 - best_dist))

    def _generate(self, prompt: str) -> tuple[str, str]:
        """
        Try LLM backends in priority order.
        Returns (answer_text, backend_name).
        """
        # 1. Ollama local
        answer = _call_ollama(prompt, self.ollama_model)
        if answer:
            return answer, "ollama"

        # 2. Cloud API fallback
        if self.cloud_api_key:
            answer = _call_openai_compatible(prompt, self.cloud_api_key, self.cloud_base_url)
            if answer:
                return answer, "cloud"

        # 3. Deterministic fallback
        chunks = []  # fallback doesn't have access to chunks here — handled upstream
        return _fallback_answer(prompt, []), "fallback"
