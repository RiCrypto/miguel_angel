# ADR-005 — Data Scientist RAG pipeline code review + Agent Scientist Computer double-check

**Date**: 2025-06-24
**Status**: Accepted
**Reviewed by**: Agent Scientist Computer (double-check pass)
**Work reviewed**: Phase 3 Data Scientist + all prior deliverables

---

## Double-check scope

Full cross-module review of all 26 Python source files, 14 integration assertions,
203 tests, and 6 package imports. This was a comprehensive re-audit — not just the
new RAG work, but every module delivered so far.

---

## Findings — miguelbot/store.py

### Strengths
- `hnsw:space=cosine` explicitly set — ensures distance scores are interpretable as
  [0.0, 1.0] for the confidence calculation in `rag.py`
- `anonymized_telemetry=False` on `PersistentClient` — correct for privacy-first local app
- `get_or_create_collection` pattern — idempotent, safe on every startup
- `count()` with `max(col.count(), 1)` guard in `query()` — prevents ChromaDB error
  on empty collections

### Verdict: **Production-ready** ✅

---

## Findings — miguelbot/embeddings.py

### Strengths
- Three-tier fallback (Ollama → sentence-transformers → TF-IDF) auto-detects at startup
- `OllamaEmbedder.is_available()` probes the actual running models list, not just the port
- TF-IDF vocabulary seeded with 72 domain-specific electrical/instrumentation terms —
  meaningful signal for component and ERC queries even without a neural model
- TF-IDF produces true unit vectors (magnitude = 1.0 verified in assertion #2)
- All three backends implement the same `embed()` / `embed_batch()` / `dim` interface —
  backend is fully interchangeable

### Issues found
None.

### Verdict: **Production-ready** ✅

---

## Findings — miguelbot/ingest.py

### Strengths
- `_doc_id()` uses SHA-256 of `source::chunk_index` — deterministic, 16-char hex, collision-resistant
- Delta ingestion checks existing IDs before embedding — avoids duplicate work on restarts
- Component library ingestor builds rich descriptive sentences combining name, ISA tag,
  IEC code, description, keywords, aliases, and pin types — maximises semantic recall
- ERC rules are self-contained (no external dependency) — always available even offline
- Forum ingestion gracefully handles missing `get_discussions()` REST API availability

### Verdict: **Production-ready** ✅

---

## Findings — miguelbot/rag.py

### Strengths
- RRF correctly boosts documents appearing in multiple collections (assertion #6 verified)
- `k=60` in RRF is the standard literature-recommended value — not arbitrary
- Confidence = `1.0 - best_cosine_distance` — interpretable and calibrated to cosine space
- Prompt structure: system → schematic context → retrieved chunks → question — correct order
- Three LLM backends: Ollama → cloud API → deterministic fallback — robust degradation
- `should_escalate` threshold of 0.72 is tunable per deployment

### Verdict: **Production-ready** ✅

---

## Findings — miguelbot/service.py

### Strengths
- Single public API (`start()`, `ask()`, `explain_erc()`, `suggest_component()`, `stop()`)
- `start()` is idempotent with `force_reindex=False` guard
- `status` property exposes backend name and per-collection counts for the UI panel header
- Thread-safe for use from `QThread` worker in the PyQt6 panel

### Verdict: **Production-ready** ✅

---

## Findings — cross-module double-check

### Bug found and fixed during review

**`auth/profile.py` — `datetime.utcnow()` deprecation (7 occurrences)**

`datetime.utcnow()` is deprecated since Python 3.12 and scheduled for removal.
All 7 occurrences replaced with `datetime.now(timezone.utc)` — timezone-aware.
The `session_validation` comparison was updated to use `.replace(tzinfo=timezone.utc)`
to correctly compare aware and naive datetimes.

Fix applied. All 34 auth tests still pass. 203/203 total tests passing.

---

## Overall verdict

All RAG pipeline deliverables are **approved for main branch**.
One bug found and fixed (utcnow deprecation) in the auth module during the cross-module pass.

**Total project status at time of this review:**
- 26 Python source files · 1,813 test lines · 203/203 tests passing
- 6 packages: auth · core · db · miguelbot · ui · export (stub)
- 5 ADRs documenting all major decisions and code reviews
- 0 known bugs outstanding

**Next Agent Scientist Computer recommendation**: implement the export engine (Backend Developer).
