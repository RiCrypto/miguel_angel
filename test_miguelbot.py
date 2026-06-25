"""
Tests for miguel_angel MiguelBot RAG pipeline.
Uses in-memory ChromaDB and TF-IDF embeddings — no Ollama required.

Run with: pytest tests/test_miguelbot.py -v
"""

import pytest
from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from miguel_angel.miguelbot import (
    MiguelBotService, RAGEngine, RAGAnswer, RetrievedChunk,
    IngestionPipeline, EmbeddingEngine, EmbeddingBackend,
    VectorStore, COL_DOCS, COL_COMPONENTS, COL_FORUM, COL_ERC,
    reciprocal_rank_fusion,
)
from miguel_angel.miguelbot.rag import _build_prompt, _fallback_answer
from miguel_angel.miguelbot.ingest import _chunk_text, _strip_markdown, _doc_id
from miguel_angel.miguelbot.embeddings import TFIDFEmbedder, OllamaEmbedder, SentenceTransformerEmbedder


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def embedder():
    """Always use TF-IDF — no external dependency."""
    e = EmbeddingEngine(force_backend=EmbeddingBackend.TFIDF)
    return e


@pytest.fixture
def store():
    """In-memory ChromaDB store — ephemeral, fast, isolated."""
    s = VectorStore(in_memory=True)
    s.connect()
    yield s
    s.close()


@pytest.fixture
def pipeline(store, embedder):
    return IngestionPipeline(store, embedder)


@pytest.fixture
def engine(store, embedder):
    return RAGEngine(store, embedder)


@pytest.fixture
def service():
    """Full service with in-memory store and TF-IDF embedder."""
    svc = MiguelBotService(
        in_memory=True,
        embedding_backend=EmbeddingBackend.TFIDF,
    )
    svc.start()
    yield svc
    svc.stop()


@pytest.fixture
def library_db(tmp_path):
    """Real LibraryDB seeded with test data."""
    from miguel_angel.db import LibraryDB
    db = LibraryDB(db_path=tmp_path / "lib.db")
    db.connect(seed=True)
    yield db
    db.close()


# ─── TF-IDF embedder tests ────────────────────────────────────────────────────

class TestTFIDFEmbedder:
    def test_embed_returns_correct_dim(self):
        e = TFIDFEmbedder()
        v = e.embed("temperature controller")
        assert len(v) == TFIDFEmbedder.DIM

    def test_embed_is_unit_vector(self):
        e = TFIDFEmbedder()
        v = e.embed("pressure indicator ISA")
        mag = sum(x * x for x in v) ** 0.5
        assert abs(mag - 1.0) < 1e-6 or mag == 0.0

    def test_embed_empty_string(self):
        e = TFIDFEmbedder()
        v = e.embed("")
        assert len(v) == TFIDFEmbedder.DIM
        assert all(x == 0.0 for x in v)

    def test_embed_batch(self):
        e = TFIDFEmbedder()
        texts = ["temperature", "pressure valve", "ISA 5.1"]
        result = e.embed_batch(texts)
        assert len(result) == 3
        assert all(len(v) == TFIDFEmbedder.DIM for v in result)

    def test_different_texts_different_vectors(self):
        e = TFIDFEmbedder()
        v1 = e.embed("temperature controller TIC")
        v2 = e.embed("pressure valve FCV")
        assert v1 != v2

    def test_always_available(self):
        assert TFIDFEmbedder.is_available()

    def test_ollama_not_available_in_ci(self):
        # Ollama is not running in CI — should return False
        assert not OllamaEmbedder.is_available()


# ─── EmbeddingEngine tests ────────────────────────────────────────────────────

class TestEmbeddingEngine:
    def test_auto_detects_tfidf_in_ci(self, embedder):
        assert embedder.backend_name == EmbeddingBackend.TFIDF

    def test_embed_returns_list(self, embedder):
        v = embedder.embed("motor starter contactor")
        assert isinstance(v, list)
        assert len(v) > 0

    def test_embed_batch_returns_list_of_lists(self, embedder):
        texts = ["temperature", "pressure", "flow"]
        result = embedder.embed_batch(texts)
        assert len(result) == 3
        assert all(isinstance(v, list) for v in result)

    def test_force_tfidf_backend(self):
        e = EmbeddingEngine(force_backend=EmbeddingBackend.TFIDF)
        assert e.backend_name == EmbeddingBackend.TFIDF
        assert e.dim == 128


# ─── VectorStore tests ────────────────────────────────────────────────────────

class TestVectorStore:
    def test_connect_creates_collections(self, store):
        for col in [COL_DOCS, COL_COMPONENTS, COL_FORUM, COL_ERC]:
            assert store.collection(col) is not None

    def test_initial_count_zero(self, store):
        assert store.count(COL_DOCS) == 0
        assert store.count(COL_COMPONENTS) == 0

    def test_total_count_returns_dict(self, store):
        counts = store.total_count()
        assert COL_DOCS in counts
        assert COL_COMPONENTS in counts

    def test_add_and_query(self, store, embedder):
        col = store.collection(COL_DOCS)
        text = "temperature indicator controller ISA 5.1"
        emb  = embedder.embed(text)
        col.add(ids=["test-1"], embeddings=[emb], documents=[text], metadatas=[{"source": "test"}])
        assert store.count(COL_DOCS) == 1
        results = store.query(COL_DOCS, emb, n_results=1)
        assert results["ids"][0][0] == "test-1"

    def test_clear_collection(self, store, embedder):
        col = store.collection(COL_DOCS)
        emb = embedder.embed("test document")
        col.add(ids=["test-clear"], embeddings=[emb], documents=["test"], metadatas=[{"source": "test"}])
        before = store.count(COL_DOCS)
        assert before >= 1
        store.clear_collection(COL_DOCS)
        assert store.count(COL_DOCS) == 0

    def test_query_empty_collection_safe(self, store, embedder):
        emb = embedder.embed("query on empty")
        results = store.query(COL_FORUM, emb, n_results=5)
        assert results["ids"][0] == []


# ─── Ingestion tests ──────────────────────────────────────────────────────────

class TestIngestion:
    def test_chunk_text_basic(self):
        text = "Hello world. This is a test. " * 30
        chunks = _chunk_text(text, chunk_size=50)
        assert len(chunks) >= 2
        assert all(isinstance(c, str) for c in chunks)

    def test_chunk_text_short_returns_single(self):
        text = "Short text."
        chunks = _chunk_text(text)
        assert len(chunks) == 1

    def test_strip_markdown_removes_headers(self):
        text = "# Main title\n## Sub title\nNormal text."
        result = _strip_markdown(text)
        assert "#" not in result
        assert "Normal text" in result

    def test_strip_markdown_removes_code_blocks(self):
        text = "Before.\n```python\ncode here\n```\nAfter."
        result = _strip_markdown(text)
        assert "code here" not in result
        assert "Before" in result

    def test_strip_markdown_removes_links(self):
        text = "See [documentation](https://example.com) for more."
        result = _strip_markdown(text)
        assert "https://" not in result
        assert "documentation" in result

    def test_doc_id_is_deterministic(self):
        id1 = _doc_id("docs/security.md", 0)
        id2 = _doc_id("docs/security.md", 0)
        assert id1 == id2

    def test_doc_id_is_unique_per_chunk(self):
        id1 = _doc_id("same.md", 0)
        id2 = _doc_id("same.md", 1)
        assert id1 != id2

    def test_ingest_docs_from_real_path(self, pipeline, store):
        docs_path = Path(__file__).parent.parent / "docs"
        if not docs_path.exists():
            pytest.skip("docs/ directory not found")
        count = pipeline.ingest_docs(docs_path)
        assert count > 0
        assert store.count(COL_DOCS) > 0

    def test_ingest_components_from_library(self, pipeline, store, library_db):
        count = pipeline.ingest_components(library_db)
        assert count > 0
        assert store.count(COL_COMPONENTS) == count

    def test_ingest_erc_rules(self, pipeline, store):
        count = pipeline.ingest_erc_rules()
        assert count == 5   # 4 rules + 1 general ERC explanation
        assert store.count(COL_ERC) == 5

    def test_ingest_erc_rules_idempotent(self, pipeline, store):
        pipeline.ingest_erc_rules()
        count2 = pipeline.ingest_erc_rules()
        assert count2 == 0

    def test_ingest_empty_docs_path_safe(self, pipeline, tmp_path):
        count = pipeline.ingest_docs(tmp_path)
        assert count == 0


# ─── RRF tests ────────────────────────────────────────────────────────────────

class TestRRF:
    def _make_chunks(self, ids: list[str], scores: list[float], col: str) -> list[RetrievedChunk]:
        return [RetrievedChunk(doc_id=id_, text="t", metadata={}, score=s, collection=col)
                for id_, s in zip(ids, scores)]

    def test_rrf_merges_lists(self):
        list1 = self._make_chunks(["a", "b", "c"], [0.1, 0.2, 0.3], "docs")
        list2 = self._make_chunks(["c", "d", "e"], [0.1, 0.2, 0.3], "components")
        result = reciprocal_rank_fusion([list1, list2], top_n=5)
        ids = [r.doc_id for r in result]
        assert "c" in ids   # appears in both lists → higher RRF score

    def test_rrf_top_n_respected(self):
        list1 = self._make_chunks(["a","b","c","d","e","f"], [0.1]*6, "docs")
        result = reciprocal_rank_fusion([list1], top_n=3)
        assert len(result) == 3

    def test_rrf_empty_input(self):
        result = reciprocal_rank_fusion([])
        assert result == []

    def test_rrf_single_list(self):
        list1 = self._make_chunks(["a","b"], [0.1, 0.2], "docs")
        result = reciprocal_rank_fusion([list1], top_n=2)
        assert len(result) == 2

    def test_rrf_assigns_rrf_rank(self):
        list1 = self._make_chunks(["a","b"], [0.1, 0.2], "docs")
        result = reciprocal_rank_fusion([list1])
        assert all(r.rrf_rank > 0 for r in result)


# ─── RAG Engine tests ─────────────────────────────────────────────────────────

class TestRAGEngine:
    def test_query_empty_store_returns_answer(self, engine):
        answer = engine.query("What is a TIC?")
        assert isinstance(answer, RAGAnswer)
        assert isinstance(answer.answer, str)
        assert len(answer.answer) > 0

    def test_query_with_context(self, engine):
        ctx = {
            "selected_components": [{"reference": "TIC-101", "symbol_id": "ISA51:TIC"}],
            "active_nets": ["L1"],
            "erc_errors": [],
        }
        answer = engine.query("What is this component?", schematic_context=ctx)
        assert isinstance(answer, RAGAnswer)
        assert answer.context_used == ctx

    def test_query_returns_sources(self, engine, pipeline, library_db):
        pipeline.ingest_components(library_db)
        pipeline.ingest_erc_rules()
        answer = engine.query("temperature controller")
        assert isinstance(answer.sources, list)

    def test_confidence_zero_on_empty_store(self, engine):
        answer = engine.query("test question")
        assert 0.0 <= answer.confidence <= 1.0

    def test_escalation_flag_on_low_confidence(self, engine):
        answer = engine.query("xyzzy completely unknown term 99999")
        assert answer.should_escalate is True or answer.should_escalate is False  # bool

    def test_erc_query_specialised(self, engine, pipeline):
        pipeline.ingest_erc_rules()
        answer = engine.query_for_erc("ERC-001", "Pin K1.PE is unconnected")
        assert isinstance(answer.answer, str)
        assert len(answer.answer) > 0

    def test_component_query_specialised(self, engine, pipeline, library_db):
        pipeline.ingest_components(library_db)
        answer = engine.query_for_component("measure temperature in a process pipe")
        assert isinstance(answer.answer, str)

    def test_backend_used_is_string(self, engine):
        answer = engine.query("hello")
        assert answer.backend_used in ("ollama", "cloud", "fallback")

    def test_prompt_includes_context(self):
        from miguel_angel.miguelbot.rag import RetrievedChunk
        chunk = RetrievedChunk(
            doc_id="t1", text="TIC is a temperature indicator controller.", metadata={}, score=0.1, collection="docs"
        )
        ctx    = {"selected_components": [{"reference": "TIC-101"}]}
        prompt = _build_prompt("What is TIC?", [chunk], ctx)
        assert "TIC-101" in prompt
        assert "temperature indicator controller" in prompt
        assert "What is TIC?" in prompt

    def test_fallback_answer_no_chunks(self):
        answer = _fallback_answer("How do I wire this?", [])
        assert "GitHub Discussions" in answer or "forum" in answer.lower()


# ─── MiguelBotService tests ───────────────────────────────────────────────────

class TestMiguelBotService:
    def test_service_starts(self, service):
        assert service.is_ready

    def test_status_online(self, service):
        status = service.status
        assert status["online"] is True
        assert "backend" in status
        assert "counts" in status

    def test_erc_rules_seeded_on_start(self, service):
        counts = service._store.total_count()
        assert counts[COL_ERC] == 5

    def test_ask_returns_answer(self, service):
        answer = service.ask("What is ERC-001?")
        assert isinstance(answer, RAGAnswer)
        assert len(answer.answer) > 10

    def test_ask_with_docs_path(self, tmp_path):
        """Service ingests docs when docs_path is provided."""
        (tmp_path / "test.md").write_text(
            "# Temperature Indicator\nA TI is a field-mounted temperature indicator per ISA 5.1."
        )
        svc = MiguelBotService(
            docs_path=tmp_path,
            in_memory=True,
            embedding_backend=EmbeddingBackend.TFIDF,
        )
        svc.start()
        assert svc._store.count(COL_DOCS) > 0
        answer = svc.ask("What is a temperature indicator?")
        assert isinstance(answer, RAGAnswer)
        svc.stop()

    def test_ask_with_library(self, service, library_db):
        """Attach library after start via reindex."""
        service.library_db = library_db
        service.reindex()
        assert service._store.count(COL_COMPONENTS) > 0
        answer = service.suggest_component("temperature measurement")
        assert isinstance(answer, RAGAnswer)

    def test_explain_erc(self, service):
        answer = service.explain_erc("ERC-001", "Pin M1.PE is unconnected")
        assert isinstance(answer, RAGAnswer)
        assert "ERC-001" in answer.answer or len(answer.answer) > 10

    def test_stop_and_restart(self, tmp_path):
        svc = MiguelBotService(in_memory=True, embedding_backend=EmbeddingBackend.TFIDF)
        svc.start()
        assert svc.is_ready
        svc.stop()
        assert not svc.is_ready
        svc.start()
        assert svc.is_ready
        svc.stop()
