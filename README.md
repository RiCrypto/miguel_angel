<div align="center">

# miguel\_angel

**Open-source desktop application for electrical and electronic schematics**

*Inspired by Eplan · SolidWorks Electrical · SkiCAD — built for engineers who believe professional tools should be free*

[![License: MIT](https://img.shields.io/badge/License-MIT-7F77DD.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-1D9E75.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Tests](https://img.shields.io/badge/Tests-203%20passing-27500A.svg)](tests/)
[![Progress](https://img.shields.io/badge/Progress-80%25-7F77DD.svg)]()
[![Phase](https://img.shields.io/badge/Phase-3%20of%205-EF9F27.svg)]()
[![GitHub](https://img.shields.io/badge/GitHub-RiCrypto%2Fmiguel__angel-181825.svg)](https://github.com/RiCrypto/miguel_angel)

</div>

---

## What is miguel\_angel?

**miguel\_angel** is a cross-platform, open-source schematic editor for electrical and electronic engineering. It supports the full range of international instrumentation and electrical standards — giving engineers a free, professional-grade alternative to tools that cost thousands of dollars per seat.

> **Current status:** Phase 3 of 5 — 80% complete. Core engine, component library, main window, and AI assistant are all implemented and code-reviewed. Export engine and canvas symbol placement are next.

---

## Quick start

```bash
git clone https://github.com/RiCrypto/miguel_angel.git
cd miguel_angel

conda create -n miguel_angel python=3.11
conda activate miguel_angel
pip install -r requirements.txt -r requirements-auth.txt

# Launch
python -m miguel_angel

# Run tests (203 passing)
pytest tests/ -v
```

**CLI options:**
```bash
python -m miguel_angel                    # standard launch
python -m miguel_angel --no-auth          # skip login (dev mode)
python -m miguel_angel --debug            # verbose logging
python -m miguel_angel project.maproj     # open file on start
```

---

## Standards supported

| Standard | Scope | Symbols |
|----------|-------|:-------:|
| **ISA 5.1** | Instrumentation symbols — indicators, controllers, transmitters, valves, switches | 12 |
| **ISA 5.2** | Binary logic diagrams — AND/OR/NOT gates, timers, interlocks | 4 |
| **ISA 5.4** | Instrument loop diagrams — I/P converters, positioners, annunciators | 3 |
| **ISA 95** | Enterprise-control integration — PLC, HMI, DCS, SCADA (levels 0–4) | 3 |
| **IEC 60617** | Graphical symbols — contactors, motors, breakers, transformers, terminals | 6 |
| **ANSI / NEMA** | North American electrical — push buttons, relays, fuses | 5 |
| **IEEE 315** | Electronic symbols — R, C, L, diodes, transistors, op-amps, logic gates | 7 |
| **Custom** | User-defined — SVG import, symbol editor, team-shareable | ∞ |

**40 symbols · 11 line types (6 ISA 5.1 signal + 5 IEC 60617 power)**

---

## Architecture

```
miguel_angel/
│
├── auth/                        ✅ COMPLETE — Phase 2 · ADR-002
│   └── profile.py               Argon2id · AES-256 · TOTP · FIDO2
│                                34 tests
│
├── core/                        ✅ COMPLETE — Phase 2 · ADR-002
│   ├── models.py                Pydantic v2 — Project/Sheet/Component/Pin/Wire/Net
│   ├── netlist.py               NetworkX — spatial matching · ERC · KiCad export
│   └── fileio.py                .maproj JSON · msgpack sidecar · .bak backup
│                                45 tests
│
├── db/                          ✅ COMPLETE — Phase 2 · ADR-003
│   ├── library_models.py        SQLAlchemy 2.0 ORM — 9 tables
│   ├── library_db.py            40 symbols · 11 line types · full-text search
│   └── migrations/
│       └── 0001_initial_schema.py   Alembic migration
│                                43 tests
│
├── ui/                          ✅ COMPLETE — Phase 3 · ADR-004
│   ├── constants.py             Theme (21 tokens) · stylesheet · app metadata
│   ├── menubar.py               8 menus · 7 standard libraries · 11 line types
│   ├── toolbar.py               9-tool vertical palette · exclusive group
│   ├── canvas.py                QGraphicsView · zoom 5–2000% · wire routing · ERC signals
│   ├── panels.py                4 dock panels — navigator · library · properties · MiguelBot
│   └── mainwindow.py            Orchestrator · QSettings · unsaved-changes guard
│                                29 tests (headless)
│
├── miguelbot/                   ✅ COMPLETE — Phase 3 · ADR-005
│   ├── store.py                 ChromaDB — 4 collections (docs/components/forum/erc_rules)
│   ├── embeddings.py            Ollama nomic-embed-text → sentence-transformers → TF-IDF
│   ├── ingest.py                Docs · component library · forum · ERC rules
│   ├── rag.py                   RRF retrieval · prompt builder · Ollama/cloud/fallback LLM
│   └── service.py               MiguelBotService public API
│                                52 tests
│
├── __main__.py                  ✅ Entry point — python -m miguel_angel
│
└── export/                      🔄 Phase 4 — Backend Developer (pending)
    ├── dxf.py                   ezdxf — AutoCAD / SolidWorks Electrical
    ├── pdf.py                   reportlab — print sheets
    ├── svg.py                   svgwrite — vector export
    └── kicad.py                 KiCad netlist — PCB handoff
```

---

## What's been built

### ✅ Security — `miguel_angel/auth/`

Full dual-factor local authentication. Nothing is ever sent off-device.

| Feature | Implementation |
|---------|---------------|
| Password hashing | Argon2id — 64 MB memory-hard, GPU-resistant |
| Storage | AES-256 (Fernet) · PBKDF2-HMAC-SHA256 (480k iterations) · timezone-aware timestamps |
| Validation 1 | TOTP RFC 6238 — any authenticator app, works offline |
| Validation 2 | FIDO2 (YubiKey) · Windows Hello · email OTP fallback |
| Recovery | 10 single-use SHA-256 backup codes |
| Lockout | 3 attempts → 15 min · recovery email OTP |

### ✅ Schematic engine — `miguel_angel/core/`

```python
from miguel_angel.core import Project, Sheet, Component, NetlistEngine, MAprojIO, Point, Standard

# Create, edit and save a schematic
project = MAprojIO.new_project("Motor Starter", author="R. Almeida")
tic = Component(symbol_id="ISA51:TIC", reference="TIC-101",
                position=Point(x=10, y=5), standard=Standard.ISA_5_1)
project.sheets[0].components.append(tic)
MAprojIO().save(project, Path("motor_starter.maproj"))

# Build netlist and run ERC
engine = NetlistEngine()
engine.build(project)
violations = engine.run_erc()              # [ERC-001 unconnected pin, ...]
netlist    = engine.to_netlist_dict()      # KiCad-compatible export dict
```

ERC rules: `ERC-001` unconnected pin · `ERC-002` dead-end wire · `ERC-003` power short · `ERC-004` output conflict.

### ✅ Component library — `miguel_angel/db/`

```python
from miguel_angel.db import LibraryDB

db = LibraryDB()
db.connect()

db.search("temperature controller")            # full-text: name + tag + keywords + aliases
db.get_symbol("ISA51:TIC")                     # eager-loaded with pins, keywords, aliases
db.get_symbols_by_standard("IEC 60617")
db.get_line_types("ISA 5.1")                   # 6 signal line types
db.stats()   # → {"ISA 5.1": 12, "IEC 60617": 6, "IEEE 315": 7, ...}
```

### ✅ Main window — `miguel_angel/ui/`

- **8-menu bar**: File · Edit · Workspace · Component library · Line types · View · Tools · Help
- **9-tool vertical toolbar**: Select · Pan · Wire · Junction · Symbol · Power · Ground · Label · Text
- **Infinite canvas**: QGraphicsView · zoom 5–2000% · orthogonal wire routing · dot-grid snap
- **4 dock panels**: Project navigator · Component library browser · Properties · MiguelBot AI
- **Status bar**: active tool · cursor coordinates · zoom % · ERC status · filename
- **QSettings**: window geometry and dock layout persist across restarts

### ✅ MiguelBot AI assistant — `miguel_angel/miguelbot/`

Context-aware AI assistant embedded as a dockable panel (`F1`).

```python
from miguel_angel.miguelbot import MiguelBotService, EmbeddingBackend
from pathlib import Path

bot = MiguelBotService(
    docs_path    = Path("docs/"),
    library_db   = db,                          # LibraryDB instance
    ollama_model = "llama3",                    # offline, no API key
)
bot.start()   # connect + ingest (idempotent)

answer = bot.ask(
    "How do I wire a motor starter circuit?",
    schematic_context = canvas.get_context_snapshot(),
)
print(answer.answer)          # LLM-generated answer grounded in docs
print(answer.confidence)      # 0.0 – 1.0 (based on vector similarity)
print(answer.should_escalate) # True → auto-post to GitHub Discussions

bot.explain_erc("ERC-001", "Pin K1.PE is unconnected")
bot.suggest_component("measure temperature in a process pipe")
bot.stop()
```

**RAG pipeline:**
1. Embed question with `nomic-embed-text` (Ollama, 768-dim) or fallback
2. Parallel search across `docs`, `components`, `erc_rules`, `forum`
3. Reciprocal Rank Fusion (RRF) — re-ranks 20 candidates to top-5
4. Inject schematic context (selected components, active nets, ERC errors)
5. Generate answer via Ollama Llama 3 → cloud API → deterministic fallback
6. If confidence < 0.72 → `should_escalate=True` → MiguelBot panel auto-posts to GitHub Discussions

**Embedding backends** (auto-detected at startup):
- `nomic-embed-text` via Ollama — 768-dim, CPU-only, no GPU, offline
- `all-MiniLM-L6-v2` via sentence-transformers — 384-dim, pip-installable
- TF-IDF bag-of-words — 128-dim, always available (used in CI)

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
| AI vector store | ChromaDB (persistent, 4 collections) | ✅ |
| AI embeddings | Ollama nomic-embed-text / sentence-transformers / TF-IDF | ✅ |
| AI generation | Ollama Llama 3 / OpenAI-compatible / fallback | ✅ |
| Export | ezdxf · reportlab · svgwrite | 🔄 Phase 4 |
| CI/CD | GitHub Actions | ✅ |
| Packaging | PyInstaller | 🔄 Phase 4 |

---

## Project progress

| Phase | Description | Status | Progress |
|-------|-------------|--------|:--------:|
| **1** | Requirements & architecture | ✅ Complete | 100% |
| **2** | Core engine | ✅ Complete | 95% |
| **3** | UI & AI assistant | ✅ Complete | 90% |
| **4** | Export & integration | 🔄 Designed | 30% |
| **5** | Release & documentation | 📝 In progress | 22% |

**Overall: 80% · 203 tests passing · 6,361 lines of production code · 5 ADRs · 49 files**

---

## .maproj file format

Human-readable JSON, git-diffable, version-controlled alongside your schematic:

```json
{
  "version": "1",
  "metadata": {
    "name": "Motor Starter",
    "author": "R. Almeida",
    "standard": "IEC 60617",
    "revision": "A"
  },
  "sheets": [{
    "name": "Sheet 1",
    "size": "A4",
    "components": [{ "reference": "TIC-101", "symbol_id": "ISA51:TIC" }],
    "wires": [{ "start": {"x": 14, "y": 5}, "end": {"x": 20, "y": 5} }],
    "net_labels": [{ "net_name": "L1", "position": {"x": 14, "y": 5} }]
  }],
  "nets": [{ "name": "L1", "pin_ids": ["uuid-1", "uuid-2"] }]
}
```

---

## Security

All data stored locally — nothing leaves your machine:

| OS | Profile DB | Library DB | Vector Store |
|----|-----------|-----------|-------------|
| Windows | `%LOCALAPPDATA%\miguel_angel\` | same | `\miguel_angel\miguelbot_store\` |
| macOS | `~/Library/Application Support/miguel_angel/` | same | same |
| Linux | `~/.local/share/miguel_angel/` | same | same |

See [docs/guides/security.md](docs/guides/security.md) for the full dual-factor setup guide.

---

## GitHub automation

| Workflow | Trigger | Action |
|----------|---------|--------|
| `ci.yml` | Push / PR | Python 3.11+3.12 × Win+Mac+Linux |
| `forumbot_respond.yml` | New Discussion | RAG → auto-reply → label |
| `forumbot_sync.yml` | Nightly 02:00 UTC | Resolved Q&A → ChromaDB sync |

Add `FORUMBOT_LLM_API_KEY` in **Settings → Secrets → Actions** to enable LLM responses.

---

## Architecture decisions

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-001](docs/adr/ADR-001-tech-stack.md) | Technology stack | ✅ |
| [ADR-002](docs/adr/ADR-002-backend-review.md) | Backend Developer review | ✅ |
| [ADR-003](docs/adr/ADR-003-db-review.md) | Database Specialist review — 3 bugs fixed | ✅ |
| [ADR-004](docs/adr/ADR-004-frontend-review.md) | Frontend Developer review — 2 bugs fixed | ✅ |
| [ADR-005](docs/adr/ADR-005-rag-review.md) | Data Scientist review + double-check — 1 bug fixed | ✅ |

---

## Contributing

```bash
git checkout -b feat/your-feature
git commit -m "feat: add ISA 5.1 flow control valve symbol"
git push origin feat/your-feature
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Questions? Open a [GitHub Discussion](https://github.com/RiCrypto/miguel_angel/discussions) — ForumBot responds within minutes.

---

## Development team

| # | Role | Responsibility |
|---|------|----------------|
| 10 | **Director** (Ricardo Almeida) | Final approval · change authority |
| 1 | Agent Scientist Computer | Technical lead · architecture · 5 code reviews |
| 7 | Project Manager | Roadmap · 6 status reports |
| 3 | Backend Developer | Security · data model · netlist · file I/O |
| 5 | Database Specialist | Component library · ISA/IEC/ANSI/IEEE schemas |
| 4 | Frontend Developer | PyQt6 UI · canvas · menus · panels |
| 2 | Data Scientist | RAG pipeline · MiguelBot · ChromaDB |
| 6 | Cloud Specialist | CI/CD · GitHub Actions · ForumBot |
| 8 | Marketing Specialist | Community · open-source outreach |
| 9 | Documentation Specialist | User guide · API reference · ADRs |

---

## License

MIT — see [LICENSE](LICENSE).
Built with Python and PyQt6.
AI assistant powered by [Ollama](https://ollama.ai) + [LangChain](https://langchain.com).
Developed with assistance from [Anthropic Claude](https://anthropic.com).

---

<div align="center">
<sub>⚡ miguel_angel — professional electrical schematics, open source, free forever</sub>
</div>
