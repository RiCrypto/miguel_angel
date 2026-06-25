"""
miguel_angel — MiguelBot Ingestion Pipeline
Data Scientist implementation · Phase 3

Ingests four knowledge sources into ChromaDB:

  1. docs/       — Markdown documentation files (MkDocs)
  2. components  — Component library from SQLite (via LibraryDB)
  3. forum       — Resolved GitHub Discussion Q&A (via PyGithub)
  4. erc_rules   — Built-in ERC rule explanations

Ingestion is idempotent — each document has a deterministic ID.
Delta ingestion: only new or changed documents are re-embedded.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from .store import VectorStore, COL_DOCS, COL_COMPONENTS, COL_FORUM, COL_ERC
from .embeddings import EmbeddingEngine

logger = logging.getLogger("miguel_angel.miguelbot.ingest")

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _doc_id(source: str, chunk_index: int) -> str:
    """Deterministic document ID — same content always gets same ID."""
    raw = f"{source}::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 60) -> list[str]:
    """
    Split text into overlapping word-level chunks.
    Tries to break at sentence boundaries first.
    """
    # Split at sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        words = sentence.split()
        if current_len + len(words) > chunk_size and current:
            chunks.append(" ".join(current))
            # Overlap: keep last <overlap> words
            current = current[-overlap:] if len(current) > overlap else current
            current_len = len(current)
        current.extend(words)
        current_len += len(words)

    if current:
        chunks.append(" ".join(current))

    return chunks if chunks else [text]


def _strip_markdown(text: str) -> str:
    """Remove markdown syntax for cleaner embedding."""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", lambda m: m.group(0)[1:-1], text)
    text = re.sub(r"#{1,6}\s+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion pipeline
# ─────────────────────────────────────────────────────────────────────────────

class IngestionPipeline:
    """
    Ingests all knowledge sources into ChromaDB.

    Usage:
        pipeline = IngestionPipeline(store, embedder)
        pipeline.ingest_docs(Path("docs/"))
        pipeline.ingest_components(library_db)
        pipeline.ingest_erc_rules()
        pipeline.ingest_forum(repo_name="RiCrypto/miguel_angel", token="ghp_...")
    """

    def __init__(self, store: VectorStore, embedder: EmbeddingEngine):
        self.store   = store
        self.embedder = embedder

    # ── Docs ──────────────────────────────────────────────────────────────────

    def ingest_docs(
        self,
        docs_path: Path,
        force_reindex: bool = False,
    ) -> int:
        """
        Walk docs/ directory and ingest all .md files.
        Returns total chunks added.
        """
        col   = self.store.collection(COL_DOCS)
        total = 0

        md_files = sorted(docs_path.rglob("*.md"))
        if not md_files:
            logger.warning("No markdown files found in %s", docs_path)
            return 0

        for md_file in md_files:
            raw_text = md_file.read_text(encoding="utf-8", errors="ignore")
            clean    = _strip_markdown(raw_text)
            chunks   = _chunk_text(clean)
            source   = str(md_file.relative_to(docs_path))

            # Extract heading context from original markdown
            heading = ""
            for line in raw_text.split("\n"):
                if line.startswith("#"):
                    heading = line.lstrip("#").strip()
                    break

            ids        = [_doc_id(source, i) for i in range(len(chunks))]
            embeddings = self.embedder.embed_batch(chunks)
            metadatas  = [
                {"source_file": source, "heading": heading,
                 "chunk_index": i, "source_type": "docs"}
                for i in range(len(chunks))
            ]

            # Delta: skip IDs already in collection
            if not force_reindex:
                existing = set(col.get(ids=ids)["ids"])
                new_mask = [i for i, id_ in enumerate(ids) if id_ not in existing]
                if not new_mask:
                    continue
                ids        = [ids[i] for i in new_mask]
                embeddings = [embeddings[i] for i in new_mask]
                metadatas  = [metadatas[i] for i in new_mask]
                chunks     = [chunks[i] for i in new_mask]

            if ids:
                col.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=chunks,
                    metadatas=metadatas,
                )
                total += len(ids)
                logger.debug("Ingested %d chunks from %s", len(ids), source)

        logger.info("Docs ingestion complete: %d new chunks", total)
        return total

    # ── Component library ─────────────────────────────────────────────────────

    def ingest_components(self, library_db, force_reindex: bool = False) -> int:
        """
        Ingest all active symbols from the component library SQLite DB.
        Each symbol becomes one document with its description, keywords, and pins.
        """
        col   = self.store.collection(COL_COMPONENTS)
        total = 0

        standards = [
            "ISA 5.1", "ISA 5.2", "ISA 5.4", "ISA 95",
            "IEC 60617", "ANSI/NEMA", "IEEE 315",
        ]

        for std in standards:
            symbols = library_db.get_symbols_by_standard(std)
            for sym in symbols:
                # Build rich descriptive text for embedding
                full_sym = library_db.get_symbol(sym.symbol_id)
                if not full_sym:
                    continue

                keywords = [k.keyword for k in full_sym.keywords]
                aliases  = [a.alias  for a in full_sym.aliases]
                pin_names = [f"{p.pin_number}:{p.name}({p.pin_type})" for p in full_sym.pins]

                doc_text = (
                    f"{full_sym.name}. "
                    f"Symbol ID: {full_sym.symbol_id}. "
                    f"Standard: {std}. "
                    f"Reference prefix: {full_sym.reference_prefix}. "
                    + (f"ISA tag: {full_sym.isa_tag}. " if full_sym.isa_tag else "")
                    + (f"IEC code: {full_sym.iec_code}. " if full_sym.iec_code else "")
                    + (f"Description: {full_sym.description}. " if full_sym.description else "")
                    + (f"Keywords: {', '.join(keywords)}. " if keywords else "")
                    + (f"Also known as: {', '.join(aliases)}. " if aliases else "")
                    + (f"Pins: {', '.join(pin_names)}. " if pin_names else "")
                )

                doc_id = _doc_id(f"component::{full_sym.symbol_id}", 0)

                if not force_reindex:
                    existing = col.get(ids=[doc_id])["ids"]
                    if existing:
                        continue

                embedding = self.embedder.embed(doc_text)
                col.add(
                    ids        = [doc_id],
                    embeddings = [embedding],
                    documents  = [doc_text],
                    metadatas  = [{
                        "symbol_id":        full_sym.symbol_id,
                        "standard":         std,
                        "reference_prefix": full_sym.reference_prefix,
                        "isa_tag":          full_sym.isa_tag or "",
                        "source_type":      "component",
                    }],
                )
                total += 1

        logger.info("Component ingestion complete: %d symbols", total)
        return total

    # ── ERC rules ─────────────────────────────────────────────────────────────

    def ingest_erc_rules(self, force_reindex: bool = False) -> int:
        """
        Ingest built-in ERC rule explanations with fix guidance.
        These are static — no external dependency required.
        """
        col = self.store.collection(COL_ERC)

        rules = [
            {
                "code": "ERC-001",
                "title": "Unconnected pin",
                "text": (
                    "ERC-001: An unconnected pin was found on a component. "
                    "Every pin that is not intentionally left unconnected should "
                    "be wired to a net. To fix this, draw a wire from the pin to "
                    "the appropriate net, or place a 'No Connect' marker (X) on "
                    "the pin to indicate it is intentionally unused. "
                    "Common cause: forgetting to connect power or ground pins."
                ),
            },
            {
                "code": "ERC-002",
                "title": "Dead-end wire — single-pin net",
                "text": (
                    "ERC-002: A net has only one connected pin. This usually means "
                    "a wire was drawn but not connected at one end, or a net label "
                    "references a net name that does not exist elsewhere. "
                    "To fix: check both ends of all wires in the area and ensure "
                    "each connects to a pin or joins another wire."
                ),
            },
            {
                "code": "ERC-003",
                "title": "Power-to-power short circuit",
                "text": (
                    "ERC-003: Two power pins are directly connected on the same net. "
                    "This can cause a short circuit if the voltages differ. "
                    "To fix: verify that both power pins carry the same voltage, "
                    "or insert a protection element (fuse, diode, or resistor) "
                    "between them. Common cause: accidentally connecting 24VDC to PE."
                ),
            },
            {
                "code": "ERC-004",
                "title": "Output conflict — multiple outputs on one net",
                "text": (
                    "ERC-004: Multiple output pins are connected to the same net. "
                    "This causes a bus conflict where two drivers fight over the "
                    "same signal line. To fix: insert a pull-up/pull-down resistor, "
                    "use open-collector outputs, or check whether the signals should "
                    "be on separate nets. Common in PLC digital output wiring."
                ),
            },
            {
                "code": "ERC-GENERAL",
                "title": "About the Electrical Rules Check (ERC)",
                "text": (
                    "The ERC (Electrical Rules Check) validates the schematic for "
                    "common wiring errors. Run it from Tools → Run ERC check (F5). "
                    "Each violation shows a code (ERC-001 to ERC-004), a description, "
                    "and the affected component or net. "
                    "MiguelBot can explain any ERC error — click 'Explain this error' "
                    "in the ERC panel, or ask a question here."
                ),
            },
        ]

        total = 0
        for rule in rules:
            doc_id = _doc_id(f"erc::{rule['code']}", 0)
            if not force_reindex:
                existing = col.get(ids=[doc_id])["ids"]
                if existing:
                    continue
            embedding = self.embedder.embed(rule["text"])
            col.add(
                ids        = [doc_id],
                embeddings = [embedding],
                documents  = [rule["text"]],
                metadatas  = [{"code": rule["code"], "title": rule["title"], "source_type": "erc"}],
            )
            total += 1

        logger.info("ERC rules ingestion complete: %d rules", total)
        return total

    # ── GitHub forum ──────────────────────────────────────────────────────────

    def ingest_forum(
        self,
        repo_name: str,
        github_token: str,
        max_discussions: int = 200,
        force_reindex: bool = False,
    ) -> int:
        """
        Fetch resolved GitHub Discussions and ingest Q&A pairs.
        Only discussions labelled 'answered' are ingested.
        Requires PyGithub and a valid token.
        """
        try:
            from github import Github
        except ImportError:
            logger.warning("PyGithub not installed — forum ingestion skipped")
            return 0

        col   = self.store.collection(COL_FORUM)
        total = 0

        try:
            gh   = Github(github_token)
            repo = gh.get_repo(repo_name)
        except Exception as exc:
            logger.error("GitHub connection failed: %s", exc)
            return 0

        try:
            discussions = list(repo.get_discussions())[:max_discussions]
        except Exception:
            # Discussions not available via REST API — skip gracefully
            logger.info("GitHub Discussions not accessible (may need GraphQL) — skipping")
            return 0

        for disc in discussions:
            # Only ingest answered discussions
            labels = [lb.name for lb in disc.labels] if hasattr(disc, "labels") else []
            if "answered" not in labels:
                continue

            body    = disc.body or ""
            answer  = ""
            try:
                comments = list(disc.get_comments())
                for comment in comments:
                    if getattr(comment, "is_answer", False):
                        answer = comment.body or ""
                        break
                if not answer and comments:
                    answer = comments[0].body or ""
            except Exception:
                pass

            qa_text = (
                f"Question: {disc.title}. {body[:500]}. "
                f"Answer: {answer[:800]}"
            )

            doc_id = _doc_id(f"forum::{disc.number}", 0)
            if not force_reindex:
                existing = col.get(ids=[doc_id])["ids"]
                if existing:
                    continue

            embedding = self.embedder.embed(qa_text)
            col.add(
                ids        = [doc_id],
                embeddings = [embedding],
                documents  = [qa_text],
                metadatas  = [{
                    "discussion_number": str(disc.number),
                    "title":             disc.title,
                    "url":               disc.html_url,
                    "source_type":       "forum",
                }],
            )
            total += 1

        logger.info("Forum ingestion complete: %d Q&A pairs", total)
        return total
