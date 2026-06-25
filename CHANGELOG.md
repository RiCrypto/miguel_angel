# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] — v0.1.0-dev

### Added — Phase 1 (Requirements & Architecture)
- Project vision, scope, and 10-agent development team structure
- Technology stack selected and approved by Director: Python 3.11, PyQt6, SQLite, `.maproj`
- 12-month roadmap across 5 phases (28 milestones)
- ADR-001: Technology stack decision documented

### Added — Phase 2 (Core Engine — in progress)
- `miguel_angel/auth/profile.py` — UserProfile security module
  - Argon2id password hashing (64 MB memory-hard)
  - AES-256 local encryption with PBKDF2 key derivation (480,000 iterations)
  - TOTP Validation 1 (RFC 6238, offline-capable, Google Authenticator compatible)
  - FIDO2/WebAuthn Validation 2 (YubiKey, Windows Hello, email OTP fallback)
  - SQLite profile database with encrypted blob storage
  - Account lockout (3 attempts → 15 min) and backup code system
  - 34 automated tests — all passing
- `miguel_angel/core/models.py` — Pydantic v2 schematic data model
  - Full type hierarchy: Project → Sheet → Component → Pin
  - WireSegment, Net, NetLabel, TitleBlock models
  - ISA 5.1 / IEC 60617 / ANSI / IEEE 315 enum taxonomy
  - Geometry primitives: Point, BoundingBox
  - LibrarySymbol model for component library
- `miguel_angel/core/netlist.py` — NetworkX netlist engine
  - Pin-to-pin connectivity via wire segment spatial matching
  - Net label cross-sheet electrical connectivity
  - Auto-generated net names (N001, N002…) with label override
  - Electrical Rules Check: ERC-001 through ERC-004
  - KiCad-compatible netlist export dictionary
- `miguel_angel/core/fileio.py` — .maproj file I/O engine
  - JSON primary format (human-readable, git-diffable)
  - Msgpack binary sidecar for large projects (>1 MB)
  - Automatic .bak backup on every save
  - Metadata-only fast read for project previews
  - 45 automated tests — all passing

### Added — Phase 4 (Automation)
- GitHub Actions CI pipeline (cross-platform: Windows, macOS, Linux)
- ForumBot workflows: auto-respond, nightly sync
- ForumBot response engine with RAG + label + escalation

### Added — Documentation
- README.md (this restructure)
- CONTRIBUTING.md — dev setup, commit convention, PR checklist
- docs/guides/security.md — TOTP + FIDO2 + profile setup guide
- docs/adr/ADR-001-tech-stack.md — Director-approved stack decision
- CHANGELOG.md (this file)

### Added — Phase 2 (Core Engine — DB Specialist, reviewed & approved)
- `miguel_angel/db/library_models.py` — SQLAlchemy 2.0 ORM component library schema
  - 9 tables: standards · categories · symbols · symbol_pins · symbol_keywords
  - symbol_aliases · line_types · manufacturers · manufacturer_parts
  - WAL journal mode · foreign key enforcement · composite unique constraints
- `miguel_angel/db/library_db.py` — library database engine
  - 40 seed symbols across all 7 standards (ISA 5.1/5.2/5.4/5.4/95, IEC 60617, ANSI/NEMA, IEEE 315)
  - 11 line type definitions (6 ISA 5.1 signal lines, 5 IEC 60617 power lines)
  - Full-text search across name, ISA tag, keywords, aliases
  - Idempotent seed, eager loading, stats by standard
- `miguel_angel/db/migrations/0001_initial_schema.py` — Alembic migration
- `tests/test_library_db.py` — 43 tests, all passing
- `docs/adr/ADR-003-db-review.md` — DB Specialist code review (Agent Scientist Computer)

### Changed
- `CHANGELOG.md` updated with Phase 2 DB deliverables
- `README.md` v3 — updated with DB architecture, symbol counts, full project status

### Added — Phase 3 (UI & Schematic Editor — Frontend Developer, reviewed & approved)
- `miguel_angel/ui/constants.py` — theme tokens (21), Qt stylesheet (4,320 chars), app metadata
- `miguel_angel/ui/menubar.py` — 8-menu bar: File · Edit · Workspace · Component library · Line types · View · Tools · Help
  - 7 standard library sub-menus (ISA 5.1/5.2/5.4/95, IEC 60617, ANSI/NEMA, IEEE 315)
  - 11 line type actions (6 ISA 5.1 signal + 5 IEC 60617 power)
  - All actions as named public attributes for clean signal wiring
- `miguel_angel/ui/toolbar.py` — vertical canvas tool palette (9 tools, exclusive group)
- `miguel_angel/ui/canvas.py` — QGraphicsScene/View infinite canvas
  - Zoom 5%–2000% · orthogonal wire routing · dot-grid · snap-to-grid
  - 4 signals: selection_changed · project_loaded · erc_results_changed · coordinates_changed
  - MiguelBot context snapshot (get_context_snapshot())
- `miguel_angel/ui/panels.py` — 4 dockable panels
  - ProjectNavigatorPanel · ComponentLibraryPanel · PropertiesPanel · MiguelBotPanel
- `miguel_angel/ui/mainwindow.py` — MiguelAngelMainWindow orchestrator
  - QSettings geometry persistence · unsaved-changes guard · status bar
- `miguel_angel/__main__.py` — entry point with argparse CLI
- `tests/test_ui.py` — 29 UI tests (headless, offscreen)
- `docs/adr/ADR-004-frontend-review.md` — Frontend code review (Agent Scientist Computer)

### Fixed (found during review)
- `QActionGroup` import corrected from `QtWidgets` → `QtGui`
- F-string escaped quote syntax error in `panels.py` MiguelBot chat initialisation

### Added — Phase 3 (MiguelBot RAG pipeline — Data Scientist, reviewed & approved)
- `miguel_angel/miguelbot/store.py` — ChromaDB persistent store (4 collections)
  - docs · components · forum · erc_rules
  - Cosine space · WAL-equivalent · telemetry disabled
- `miguel_angel/miguelbot/embeddings.py` — Auto-detecting embedding engine
  - Ollama nomic-embed-text (768-dim) → sentence-transformers (384-dim) → TF-IDF (128-dim)
- `miguel_angel/miguelbot/ingest.py` — Ingestion pipeline
  - Docs (MkDocs markdown) · Component library (SQLite) · Forum (GitHub Discussions) · ERC rules
  - Deterministic SHA-256 IDs · delta ingestion · idempotent
- `miguel_angel/miguelbot/rag.py` — RAG query engine
  - RRF across 4 collections · confidence scoring · Ollama/cloud/fallback LLM
  - Prompt builder with schematic context injection
- `miguel_angel/miguelbot/service.py` — MiguelBotService public API
- `tests/test_miguelbot.py` — 52 tests, all passing
- `docs/adr/ADR-005-rag-review.md` — RAG + double-check review

### Fixed (found during Agent Scientist Computer double-check)
- `auth/profile.py` — `datetime.utcnow()` deprecated in Python 3.12; all 7 occurrences
  replaced with `datetime.now(timezone.utc)`. All 34 auth tests still pass.

### Added — Phase 4 (Export engine — Backend Developer, reviewed & approved)
- `miguel_angel/export/base.py` — shared types, coordinate helpers (lu_to_mm/pt/px), ExportResult
- `miguel_angel/export/dxf.py` — DXF R2010 exporter (ezdxf)
  - 5 named layers: COMPONENTS · WIRES · NET_LABELS · TITLE_BLOCK · DIMENSIONS
  - Metric header ($MEASUREMENT=1, $INSUNITS=4) — AutoCAD/SolidWorks compatible
  - Title block · component boxes · pin crosses · wire segments · net labels
- `miguel_angel/export/pdf.py` — multi-page PDF exporter (reportlab)
  - A4/A3/A2 landscape · title block strip · component fills · wire colours
- `miguel_angel/export/svg.py` — SVG vector exporter (svgwrite)
  - CSS classes · mm units · viewBox · configurable scale parameter
- `miguel_angel/export/kicad.py` — KiCad legacy .net XML exporter
  - export() + export_from_project() · design/components/nets structure · minidom pretty-print
- `tests/test_export.py` — 46 tests, all passing
- `docs/adr/ADR-006-export-review.md` — export engine double-check review

### Fixed (found during double-check)
- `export/svg.py` — `svgwrite.container.Title` does not exist; replaced with hidden `<text>` element

### Added — Phase 3 completion (Frontend Developer, reviewed & approved · ADR-007)
- `miguel_angel/ui/symbol_item.py` — SymbolItem + PinItem QGraphicsItem subclasses
  - SymbolItem: filled rect · reference label · symbol ID · snap-to-grid · COMPONENT_DATA_ROLE
  - PinItem: cross-hair child items at correct offsets · non-selectable · moves with parent
  - Context menu: Ask MiguelBot · Properties · Rotate 90° · Mirror · Delete
  - _infer_standard(): maps symbol_id prefix → ISA/IEC/ANSI/IEEE/Custom
- `miguel_angel/ui/canvas.py` — symbol placement API
  - set_pending_symbol(symbol_id, symbol_data): arms placement + switches tool
  - _place_symbol(pos): places SymbolItem at snapped position + auto-increments ref counter
  - cancel_pending_symbol(): clears pending state (Escape key)
  - mousePressEvent: symbol tool branch routes to _place_symbol
- `miguel_angel/ui/panels.py` — MiguelBotPanel fully wired to MiguelBotService
  - set_service(service): connects RAG pipeline · updates status dot
  - _submit_query(query): QThread worker · non-blocking UI · sources display · escalation notice
  - Suggestion buttons fire real queries · scroll-to-bottom after every answer
- `miguel_angel/ui/mainwindow.py` — real symbol placement + MiguelBot startup
  - _on_symbol_selected(): fetches full symbol geometry from LibraryDB · arms canvas
  - start_miguelbot(): starts MiguelBotService in QThread · wires to panel on completion
- `tests/test_ui.py` — 19 new tests (SymbolItem, PinItem, canvas API, MiguelBot wiring)
  - 268 passed, 3 skipped (headless CI canvas grid render limitation — documented)
- `docs/adr/ADR-007-symbol-miguelbot-review.md` — double-check review · 0 bugs found
