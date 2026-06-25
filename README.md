<div align="center">

# miguel\_angel

**Open-source desktop application for electrical and electronic schematics**

*Inspired by Eplan · SolidWorks Electrical · SkiCAD — built for engineers who believe professional tools should be free*

[![License: MIT](https://img.shields.io/badge/License-MIT-7F77DD.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-1D9E75.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Tests](https://img.shields.io/badge/Tests-268%20passing-27500A.svg)](tests/)
[![Progress](https://img.shields.io/badge/Progress-93%25-7F77DD.svg)]()
[![Phase](https://img.shields.io/badge/Phase-4%2F5%20complete-EF9F27.svg)]()
[![GitHub](https://img.shields.io/badge/GitHub-RiCrypto%2Fmiguel__angel-181825.svg)](https://github.com/RiCrypto/miguel_angel)

</div>

---

## What is miguel\_angel?

**miguel\_angel** is a cross-platform, open-source schematic editor for electrical and electronic engineering. It supports the full range of international instrumentation and electrical standards — giving engineers a free, professional-grade alternative to tools that cost thousands of dollars per seat.

> **Status:** 93% complete — Phases 1–4 done. PyInstaller packaging, MkDocs documentation, and public launch are all that remain.

---

## Quick start

```bash
git clone https://github.com/RiCrypto/miguel_angel.git
cd miguel_angel
conda create -n miguel_angel python=3.11
conda activate miguel_angel
pip install -r requirements.txt -r requirements-auth.txt
python -m miguel_angel          # launch
pytest tests/                   # 268 tests
```

---

## Standards supported

| Standard | Scope | Symbols |
|----------|-------|:-------:|
| **ISA 5.1** | Instrumentation symbols & identification | 12 |
| **ISA 5.2** | Binary logic diagrams | 4 |
| **ISA 5.4** | Instrument loop diagrams | 3 |
| **ISA 95** | Enterprise-control integration | 3 |
| **IEC 60617** | Graphical symbols for electrical diagrams | 6 |
| **ANSI / NEMA** | North American electrical standard | 5 |
| **IEEE 315** | Electronic component symbols | 7 |
| **Custom** | User-defined | ∞ |

**40 symbols · 11 line types · 7 ADRs · 268/268 tests**

---

## Architecture — all packages complete

```
miguel_angel/
│
├── auth/                        ✅ Phase 2 · ADR-002
│   └── profile.py               Argon2id · AES-256 · TOTP · FIDO2
│                                34 tests
│
├── core/                        ✅ Phase 2 · ADR-002
│   ├── models.py                Pydantic v2 — Project/Sheet/Component/Pin/Wire/Net
│   ├── netlist.py               NetworkX — spatial matching · ERC-001–004 · KiCad export
│   └── fileio.py                .maproj JSON · msgpack sidecar · .bak backup
│                                45 tests
│
├── db/                          ✅ Phase 2 · ADR-003
│   ├── library_models.py        SQLAlchemy 2.0 ORM — 9 tables
│   ├── library_db.py            40 symbols · 11 line types · full-text search
│   └── migrations/0001_initial_schema.py
│                                43 tests
│
├── ui/                          ✅ Phase 3 · ADR-004 · ADR-007
│   ├── constants.py             Theme tokens · Qt stylesheet
│   ├── menubar.py               8 menus · 7 standard libraries · 11 line types
│   ├── toolbar.py               9-tool vertical palette
│   ├── canvas.py                Infinite QGraphicsView · zoom 5–2000% · wire routing
│   │                            Symbol placement: set_pending_symbol / _place_symbol
│   ├── symbol_item.py           SymbolItem + PinItem — placed components on canvas
│   │                            Snap-to-grid · COMPONENT_DATA_ROLE · context menu
│   ├── panels.py                4 dock panels — navigator · library · properties
│   │                            MiguelBotPanel: QThread RAG wiring · sources · escalation
│   └── mainwindow.py            Orchestrator · symbol placement · start_miguelbot()
│                                58 tests (268 total across project)
│
├── miguelbot/                   ✅ Phase 3 · ADR-005
│   ├── store.py                 ChromaDB — docs/components/forum/erc_rules
│   ├── embeddings.py            Ollama nomic-embed-text → sentence-transformers → TF-IDF
│   ├── ingest.py                Docs · library · GitHub forum · ERC rules
│   ├── rag.py                   RRF retrieval · prompt builder · Ollama/cloud/fallback
│   └── service.py               MiguelBotService — start/ask/explain_erc/stop
│                                52 tests
│
├── export/                      ✅ Phase 4 · ADR-006
│   ├── base.py                  ExportResult · PageSize · lu_to_mm/pt/px
│   ├── dxf.py                   DXF R2010 — AutoCAD · SolidWorks Electrical (ezdxf)
│   ├── pdf.py                   Multi-page PDF — A4/A3/A2 (reportlab)
│   ├── svg.py                   SVG — CSS classes · mm units (svgwrite)
│   └── kicad.py                 KiCad legacy .net XML — PCB handoff
│                                46 tests
│
└── __main__.py                  ✅ CLI entry point
```

**7,999 production lines · 2,460 test lines · 63 files · 7 ADRs**

---

## What's been built

### ✅ Security — `auth/`
Dual-factor local auth. Argon2id · AES-256 · TOTP (RFC 6238) · FIDO2/YubiKey · 15-min lockout.

### ✅ Schematic engine — `core/`

```python
from miguel_angel.core import Project, Component, NetlistEngine, MAprojIO, Point, Standard

project = MAprojIO.new_project("Motor Starter")
project.sheets[0].components.append(
    Component(symbol_id="ISA51:TIC", reference="TIC-101",
              position=Point(x=10, y=5), standard=Standard.ISA_5_1)
)
MAprojIO().save(project, Path("motor_starter.maproj"))

engine = NetlistEngine(); engine.build(project)
violations   = engine.run_erc()          # [ERC-001 unconnected, ...]
netlist_dict = engine.to_netlist_dict()  # KiCad-compatible
```

### ✅ Component library — `db/`

```python
from miguel_angel.db import LibraryDB
db = LibraryDB(); db.connect()
db.search("temperature controller")   # name · tag · keywords · aliases
db.get_symbol("ISA51:TIC")            # eager: pins, keywords, aliases
db.stats()   # → {"ISA 5.1": 12, "IEC 60617": 6, ...}
```

### ✅ Main window + symbol placement — `ui/`

```python
from miguel_angel.ui import MiguelAngelMainWindow, SymbolItem

# Canvas placement API
canvas.set_pending_symbol("IEC:CONTACTOR_3P", {
    "width_lu": 6.0, "height_lu": 8.0,
    "reference_prefix": "K",
    "pins": [{"pin_number":"A1","name":"A1","pin_type":"Power",
              "x_offset":0,"y_offset":4,"orientation":"N"}, ...]
})
# → cursor becomes crosshair; next click places K1 at snapped position
# → Escape cancels; each subsequent click increments K2, K3...

# SymbolItem carries full component data for MiguelBot
item = canvas.scene().items()[0]
data = item.data(SymbolItem.COMPONENT_DATA_ROLE)
# → {"symbol_id":"IEC:CONTACTOR_3P","reference":"K1","standard":"IEC 60617",...}
```

**UI features:**
- 8-menu bar with full ISA/IEC/ANSI/IEEE submenus
- 9-tool vertical toolbar (Select, Pan, Wire, Junction, Symbol, Power, Ground, Label, Text)
- Infinite canvas with zoom 5–2000%, orthogonal wire routing, dot-grid snap
- 4 dock panels: Navigator · Library browser · Properties · MiguelBot AI

### ✅ MiguelBot AI assistant — `miguelbot/`

```python
from miguel_angel.miguelbot import MiguelBotService

bot = MiguelBotService(docs_path=Path("docs/"), library_db=db)
bot.start()   # idempotent; ingests docs + components + ERC rules

answer = bot.ask("How do I wire a motor starter?",
                 schematic_context=canvas.get_context_snapshot())
# answer.answer          — grounded, context-aware LLM response
# answer.confidence      — 0.0–1.0 (cosine similarity)
# answer.should_escalate — True → auto-post to GitHub Discussions
# answer.sources         — retrieved chunk metadata

bot.explain_erc("ERC-001", "Pin K1.PE is unconnected")
bot.suggest_component("measure temperature in a process pipe")
```

**From the UI:** press `F1` to open MiguelBot panel. Select a component and ask a question —
the panel automatically injects the selected component context into every query.
Answers appear without blocking the UI (QThread worker). Sources are shown beneath each answer.

### ✅ Export engine — `export/`

```python
from miguel_angel.export import DXFExporter, PDFExporter, SVGExporter, KiCadExporter

DXFExporter().export_all_sheets(project, Path("output/"))     # DXF R2010, metric
PDFExporter().export_project(project, Path("project.pdf"))    # multi-page A4/A3
SVGExporter(scale=2.0).export_sheet(sheet, Path("hires.svg")) # CSS-classed SVG
KiCadExporter().export_from_project(project, Path("out.net")) # KiCad legacy .net
```

---

## Tech stack

| Layer | Technology | Status |
|-------|-----------|--------|
| Language | Python 3.11+ | ✅ |
| GUI | PyQt6 + QGraphicsScene | ✅ |
| Data model | Pydantic v2 | ✅ |
| File format | `.maproj` JSON | ✅ |
| Netlist | networkx | ✅ |
| Component DB | SQLite + SQLAlchemy 2.0 | ✅ |
| Security | argon2-cffi · cryptography · pyotp · fido2 | ✅ |
| Migrations | Alembic | ✅ |
| AI (store) | ChromaDB | ✅ |
| AI (embed) | Ollama nomic-embed-text / sentence-transformers / TF-IDF | ✅ |
| AI (gen) | Ollama Llama 3 / OpenAI-compatible / fallback | ✅ |
| Export DXF | ezdxf R2010 | ✅ |
| Export PDF | reportlab | ✅ |
| Export SVG | svgwrite | ✅ |
| CI/CD | GitHub Actions | ✅ |
| Packaging | PyInstaller | 🔄 Pending |

---

## Project progress

| Phase | Description | Status | Progress |
|-------|-------------|--------|:--------:|
| **1** | Requirements & architecture | ✅ Complete | 100% |
| **2** | Core engine | ✅ Complete | 100% |
| **3** | UI & AI assistant | ✅ Complete | 100% |
| **4** | Export & integration | ✅ Complete | 90% |
| **5** | Release & documentation | 📝 In progress | 22% |

**Overall: 93% · 268/268 tests · 7,999 lines · 7 ADRs · 0 known bugs**

---

## Security

All data stored locally:

| OS | Path |
|----|------|
| Windows | `%LOCALAPPDATA%\miguel_angel\` |
| macOS | `~/Library/Application Support/miguel_angel/` |
| Linux | `~/.local/share/miguel_angel/` |

See [docs/guides/security.md](docs/guides/security.md).

---

## GitHub automation

| Workflow | Trigger | Action |
|----------|---------|--------|
| `ci.yml` | Push / PR | Python 3.11+3.12 × Win+Mac+Linux |
| `forumbot_respond.yml` | New Discussion | RAG → auto-reply → label |
| `forumbot_sync.yml` | Nightly 02:00 UTC | Resolved Q&A → ChromaDB |

Add `FORUMBOT_LLM_API_KEY` in **Settings → Secrets → Actions**.

---

## Architecture decisions

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-001](docs/adr/ADR-001-tech-stack.md) | Technology stack | ✅ |
| [ADR-002](docs/adr/ADR-002-backend-review.md) | Backend Developer review | ✅ |
| [ADR-003](docs/adr/ADR-003-db-review.md) | DB Specialist review — 3 bugs fixed | ✅ |
| [ADR-004](docs/adr/ADR-004-frontend-review.md) | Frontend Developer review — 2 bugs fixed | ✅ |
| [ADR-005](docs/adr/ADR-005-rag-review.md) | Data Scientist review — 1 bug fixed | ✅ |
| [ADR-006](docs/adr/ADR-006-export-review.md) | Export engine review — 1 bug fixed | ✅ |
| [ADR-007](docs/adr/ADR-007-symbol-miguelbot-review.md) | Symbol + MiguelBot wiring — 0 bugs | ✅ |

---

## Contributing

```bash
git checkout -b feat/your-feature
git commit -m "feat: add revision history undo/redo"
git push origin feat/your-feature
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Questions? Open a [GitHub Discussion](https://github.com/RiCrypto/miguel_angel/discussions) — ForumBot responds within minutes.

---

## Development team

| # | Role | Responsibility |
|---|------|----------------|
| 10 | **Director** (Ricardo Almeida) | Final approval · change authority |
| 1 | Agent Scientist Computer | Technical lead · 7 reviews + double-checks |
| 7 | Project Manager | Roadmap · 8 status reports |
| 3 | Backend Developer | Security · data model · netlist · file I/O · export |
| 5 | Database Specialist | Component library · ISA/IEC/ANSI/IEEE schemas |
| 4 | Frontend Developer | PyQt6 UI · canvas · symbol placement · MiguelBot wiring |
| 2 | Data Scientist | RAG pipeline · MiguelBot · ChromaDB |
| 6 | Cloud Specialist | CI/CD · GitHub Actions · ForumBot |
| 8 | Marketing Specialist | Community · open-source outreach |
| 9 | Documentation Specialist | User guide · API reference · ADRs |

---

## License

MIT — see [LICENSE](LICENSE).
Built with Python, PyQt6, ezdxf, reportlab, svgwrite, and ChromaDB.
AI assistant powered by [Ollama](https://ollama.ai) + [LangChain](https://langchain.com).
Developed with assistance from [Anthropic Claude](https://anthropic.com).

---

<div align="center">
<sub>⚡ miguel_angel — professional electrical schematics, open source, free forever</sub>
</div>
