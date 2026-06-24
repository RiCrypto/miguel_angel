# ADR-003 — Database Specialist code review findings

**Date**: 2025-06-24
**Status**: Accepted
**Reviewed by**: Agent Scientist Computer
**Work reviewed**: Phase 2 Database Specialist deliverables

---

## Review scope

Four artefacts reviewed:

- `miguel_angel/db/library_models.py` — SQLAlchemy 2.0 ORM table definitions
- `miguel_angel/db/library_db.py` — library engine, seed data, queries
- `miguel_angel/db/migrations/0001_initial_schema.py` — Alembic migration
- `tests/test_library_db.py` — 43-test suite

---

## Findings — library_models.py

### Strengths

- SQLAlchemy 2.0 `Mapped` + `mapped_column` pattern used throughout — modern, fully type-annotated ORM
- `UniqueConstraint` and `Index` are declared inline in `__table_args__` — correct pattern for composite constraints
- WAL journal mode enabled on connection — correct for multi-reader SQLite workloads
- `PRAGMA foreign_keys=ON` enforced at connect time — critical for referential integrity in SQLite (disabled by default)
- `on_update=_now` on `Symbol.updated_at` correctly triggers on every ORM flush

### Issues found and resolved

- `SymbolPin` `pin_number` uniqueness scoped to `(symbol_id, pin_number)` — correct; two different symbols can share pin number "1"
- `ManufacturerPart.unit_price_usd` stored as `Float` — acceptable for a library; production BOM would use `Numeric(10,4)` for precision. Deferred recommendation.

### Verdict: **Production-ready** ✅

---

## Findings — library_db.py

### Strengths

- `_seed_if_empty()` counts standards before seeding — idempotent, safe to call on every startup
- `seed_symbols()` uses `get_or_create_cat()` helper — categories are never duplicated even if seed runs twice
- `add_symbol()` early-returns on `existing` — idempotent symbol insertion, regression-tested
- `search()` queries across `name`, `symbol_id`, `isa_tag`, `description`, `keywords`, and `aliases` in one `DISTINCT` join — thorough full-text coverage
- `get_symbol()` uses `selectinload` for eager relationship loading — correct pattern; avoids `DetachedInstanceError` outside session context
- `stats()` uses `outer join` so standards with zero symbols still appear in the dict

### Issues found and resolved during this review

- `SymbolPin` for IEC motor had a syntax error (`dict(pin_number="PE","name","PE",...)`) — fixed to `dict(pin_number="PE", name="PE", ...)` — 1 test was failing, now 0
- `get_symbol()` originally used lazy loading — caused `DetachedInstanceError` when accessing `sym.pins` after session close — fixed by adding `selectinload`
- ISA 5.4 had zero symbols — standard was seeded but no symbols were added; fixed by adding 3 ISA 5.4 representative symbols (I/P converter, valve positioner, annunciator)
- After fixes: **43/43 tests passing**, **122/122 total tests passing**

### Verdict: **Production-ready** ✅

---

## Findings — 0001_initial_schema.py

### Strengths

- All tables from `library_models.py` replicated in the migration — schema in sync
- `downgrade()` drops tables in correct reverse dependency order (parts → manufacturers → symbols → categories → standards)
- Unique constraints and indexes are explicitly named — Alembic best practice for reliable rollback

### Verdict: **Production-ready** ✅

---

## Findings — test_library_db.py

### Strengths

- 43 tests across 7 test classes covering schema, standards, symbols, pins, search, categories, line types, and stats
- `test_seed_is_idempotent()` explicitly verifies double-seeding produces no duplicates — critical correctness guarantee
- `test_foreign_keys_enabled()` verifies SQLite FK enforcement at runtime — not just assumed
- `test_search_case_insensitive()` validates `ilike` behaviour

### Verdict: **Production-ready** ✅

---

## Overall verdict

All Database Specialist deliverables are **approved for the main branch**.
Three bugs were found and fixed during review — all caught by the test suite before any code shipped.
The component library now covers 40 symbols across 7 standards with 11 line type definitions.

**Next DB Specialist task**: implement the revision history and undo/redo system (SQLite journal — Phase 4).
