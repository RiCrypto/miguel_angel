<div align="center">

# miguel\_angel

**Open-source desktop application for electrical and electronic schematics**

*Inspired by Eplan · SolidWorks Electrical · SkiCAD — built for engineers who believe professional tools should be free*

[![License: MIT](https://img.shields.io/badge/License-MIT-7F77DD.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-1D9E75.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Tests](https://img.shields.io/badge/Tests-122%20passing-27500A.svg)](tests/)
[![Phase](https://img.shields.io/badge/Phase-2%20of%205%20%E2%80%94%2062%25-EF9F27.svg)]()
[![GitHub](https://img.shields.io/badge/GitHub-RiCrypto%2Fmiguel__angel-181825.svg)](https://github.com/RiCrypto/miguel_angel)

</div>

---

## What is miguel\_angel?

**miguel\_angel** is a cross-platform, open-source schematic editor for electrical and electronic engineering. It supports the full range of international instrumentation and electrical standards — giving engineers a free, professional-grade alternative to tools that cost thousands of dollars per seat.

> **Current status:** Phase 2 of 5 — 62% complete. Core engine fully implemented and reviewed. UI and canvas editor are next.

---

## Standards supported

| Standard | Scope | Symbols |
|----------|-------|:-------:|
| **ISA 5.1** | Instrumentation symbols & identification — indicators, controllers, transmitters, valves, switches | 12 |
| **ISA 5.2** | Binary logic diagrams — AND/OR/NOT gates, timers, interlocks | 4 |
| **ISA 5.4** | Instrument loop diagrams — I/P converters, positioners, annunciators | 3 |
| **ISA 95** | Enterprise-control integration — PLC, HMI, DCS, SCADA (levels 0–4) | 3 |
| **IEC 60617** | Graphical symbols — contactors, motors, breakers, transformers, terminals | 6 |
| **ANSI / NEMA** | North American electrical — push buttons, relays, fuses | 5 |
| **IEEE 315** | Electronic symbols — R, C, L, diodes, transistors, op-amps, logic gates | 7 |
| **Custom** | User-defined symbols — SVG import, symbol editor, team-shareable | ∞ |

**40 production-ready symbols · 11 line types (6 ISA 5.1 signal + 5 IEC 60617 power)**

---

## Architecture

```
miguel_angel/
├── auth/                    ← Security module ✅ COMPLETE
│   └── profile.py               Argon2id · AES-256 · TOTP · FIDO2
│                                34 tests passing
│
├── core/                    ← Schematic engine ✅ COMPLETE
│   ├── models.py                Pydantic v2 data model
│   │                            Project → Sheet → Component → Pin
│   │                            WireSegment · Net · NetLabel · LibrarySymbol
│   ├── netlist.py               NetworkX connectivity graph
│   │                            Spatial pin matching · Net labels · ERC rules
│   └── fileio.py                .maproj JSON save/load
│                                Msgpack sidecar · .bak backup
│                                45 tests passing
│
├── db/                      ← Component library ✅ COMPLETE
│   ├── library_models.py        SQLAlchemy 2.0 ORM — 9 tables
│   │                            standards · categories · symbols · pins
│   │                            keywords · aliases · line_types · manufacturers
│   ├── library_db.py            Library engine + 40 seed symbols + search
│   └── migrations/
│       └── 0001_initial_schema.py   Alembic migration
│                                43 tests passing
│
├── ui/                      ← PyQt6 editor — Phase 3 (pending)
│   ├── mainwindow.py            Main window · 8-menu bar · toolbar
│   ├── canvas.py                QGraphicsScene infinite canvas
│   ├── wire_tool.py             Click-to-route wire drawing
│   └── miguelbot_panel.py       AI assistant dock (F1)
│
├── miguelbot/               ← AI assistant RAG — Phase 3 (pending)
│   ├── rag.py                   LangChain + ChromaDB + Ollama
│   └── context.py               Live schematic state reader
│
└── export/                  ← Export engines — Phase 4 (pending)
    ├── dxf.py                   AutoCAD / SolidWorks Electrical (ezdxf)
    ├── pdf.py                   PDF print sheets (reportlab)
    ├── svg.py                   Vector export (svgwrite)
    └── kicad.py                 PCB handoff netlist
```

---

## Tech stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.11+ | Primary language — Anaconda-native |
| GUI | PyQt6 + QGraphicsScene | Desktop UI + infinite canvas |
| Data model | Pydantic v2 | Schema validation + JSON serialisation |
| File format | `.maproj` (JSON) | Human-readable, git-diffable project files |
| Netlist | networkx | Graph model: components = nodes, wires = edges |
| Component DB | SQLite 3 + SQLAlchemy 2.0 | Embedded library, no server needed |
| Geometry | shapely | Hit-testing, selection, collision on canvas |
| AI assistant | LangChain + ChromaDB + Ollama | Offline RAG, no API key required |
| Export | ezdxf · reportlab · svgwrite | DXF, PDF, SVG output |
| Security | argon2-cffi · cryptography · pyotp · fido2 | Dual-factor local auth |
| Migrations | Alembic | DB schema versioning |
| CI/CD | GitHub Actions | Cross-platform test matrix |
| Packaging | PyInstaller | .exe · .app · .deb single-file bundles |

---

## Project progress

| Phase | Description | Status | Progress |
|-------|-------------|--------|:--------:|
| **1** | Requirements & architecture | ✅ Complete | 100% |
| **2** | Core engine development | ✅ Complete | 95% |
| **3** | UI & schematic editor | 🔄 Designed | 40% |
| **4** | Data, export & integration | 🔄 Designed | 30% |
| **5** | Release & documentation | 📝 In progress | 20% |

**Overall: 62% complete · 122 tests passing · 4,242 lines of production code**

---

## What's been built

### ✅ Security module — `miguel_angel/auth/`

Full dual-factor local authentication. Nothing is ever sent off-device.

| Feature | Implementation |
|---------|---------------|
| Password hashing | Argon2id — 64 MB memory-hard, GPU-resistant |
| Storage encryption | AES-256 (Fernet) · key from PBKDF2-HMAC-SHA256 (480k iterations) |
| Validation 1 | TOTP RFC 6238 — Google Authenticator / Authy / any TOTP app |
| Validation 2 | FIDO2/WebAuthn (YubiKey) · Windows Hello · email OTP fallback |
| Recovery | 10 single-use SHA-256 backup codes, consumed on use |
| Lockout | 3 attempts → 15 min lockout → recovery email OTP |
| Tests | **34 passing** |

### ✅ Schematic data model — `miguel_angel/core/models.py`

18 Pydantic v2 models covering every concept in the schematic domain.

```python
from miguel_angel.core import (
    Project, Sheet, Component, Pin, WireSegment, Net, NetLabel,
    Point, Standard, ComponentCategory, LineType, MAprojIO
)

# Create a project
io      = MAprojIO()
project = MAprojIO.new_project("Motor Starter", author="R. Almeida")

# Place a temperature controller
tic = Component(
    symbol_id="ISA51:TIC",
    reference="TIC-101",
    position=Point(x=10, y=5),
    standard=Standard.ISA_5_1,
    category=ComponentCategory.CONTROLLER,
)
project.sheets[0].components.append(tic)

# Save
io.save(project, Path("motor_starter.maproj"))
```

### ✅ Netlist engine — `miguel_angel/core/netlist.py`

NetworkX graph with spatial pin matching, net label cross-sheet connectivity, and ERC.

```python
from miguel_angel.core import NetlistEngine

engine = NetlistEngine()
engine.build(project)

engine.is_connected(pin_a.id, pin_b.id)    # → True / False
engine.get_net_for_pin(pin_id)              # → "L1"
violations = engine.run_erc()              # → [ERC-001, ERC-004...]
netlist = engine.to_netlist_dict()         # → KiCad-compatible dict
```

ERC rules: `ERC-001` unconnected pin · `ERC-002` dead-end wire · `ERC-003` power short · `ERC-004` output conflict.

### ✅ File I/O — `miguel_angel/core/fileio.py`

`.maproj` is UTF-8 JSON, human-readable, git-diffable. Msgpack binary sidecar for large projects. Automatic `.bak` backup on every save.

### ✅ Component library — `miguel_angel/db/`

SQLite database with SQLAlchemy 2.0 ORM. 9 tables. 40 seed symbols. 11 line types.

```python
from miguel_angel.db import LibraryDB

db = LibraryDB()
db.connect()

# Search
results = db.search("temperature controller")
# → [<Symbol ISA51:TIC: Temperature indicator controller>, ...]

# Browse by standard
symbols = db.get_symbols_by_standard("IEC 60617")

# Get one symbol with all pins and keywords
tic = db.get_symbol("ISA51:TIC")
print(tic.isa_tag)          # → "TIC"
print(tic.measured_variable) # → "T"
for pin in tic.pins:
    print(pin.name, pin.pin_type, pin.orientation)

# Line types
lts = db.get_line_types("ISA 5.1")
# → Process connection (solid) · Pneumatic (dashed) · Electric (dotted) ...

# Stats
db.stats()
# → {"ISA 5.1": 12, "IEC 60617": 6, "IEEE 315": 7, ...}
```

---

## Getting started

### Prerequisites

- Python 3.11 or higher
- [Anaconda](https://www.anaconda.com/) (recommended)
- Windows 10+, macOS 12+, or Ubuntu 22.04+
- [Ollama](https://ollama.ai) (optional — for MiguelBot AI assistant)

### Installation

```bash
# Clone
git clone https://github.com/RiCrypto/miguel_angel.git
cd miguel_angel

# Create conda environment
conda create -n miguel_angel python=3.11
conda activate miguel_angel

# Install
pip install -r requirements.txt
pip install -r requirements-auth.txt

# Run all tests
pytest tests/ -v
# Expected: 122 passed
```

### Windows path note

Working from the default project root:

```
C:\Users\ralmeida\Documents\Documentos\Minha Bibliteca\Scripts de Programas\Python\miguel_angel
```

Wrap in quotes in any terminal:

```bash
cd "C:\Users\ralmeida\...\miguel_angel"
```

---

## Security

All data stored locally in the OS app data directory:

| OS | Path |
|----|------|
| Windows | `%LOCALAPPDATA%\miguel_angel\` |
| macOS | `~/Library/Application Support/miguel_angel/` |
| Linux | `~/.local/share/miguel_angel/` |

Two files are created on first launch: `profile.db` (encrypted user profile) and `library.db` (component library). Both are in `.gitignore` — never committed.

See [docs/guides/security.md](docs/guides/security.md) for the full dual-factor setup guide.

---

## .maproj file format

```json
{
  "version": "1",
  "metadata": {
    "name": "Motor Starter Circuit",
    "author": "R. Almeida",
    "organisation": "Acme Engineering",
    "standard": "IEC 60617",
    "revision": "A",
    "created_at": "2025-06-01T10:00:00Z",
    "modified_at": "2025-06-24T15:30:00Z",
    "miguel_angel_version": "0.1.0-dev"
  },
  "sheets": [
    {
      "id": "uuid",
      "name": "Sheet 1 — Power circuit",
      "size": "A4",
      "components": [
        {
          "id": "uuid",
          "symbol_id": "ISA51:TIC",
          "reference": "TIC-101",
          "position": {"x": 10, "y": 5},
          "rotation": 0.0,
          "standard": "ISA 5.1",
          "category": "Controller"
        }
      ],
      "wires": [
        {"start": {"x": 14, "y": 5}, "end": {"x": 20, "y": 5}, "line_type": "Generic"}
      ],
      "net_labels": [
        {"net_name": "L1", "position": {"x": 14, "y": 5}}
      ]
    }
  ],
  "nets": [
    {"id": "uuid", "name": "L1", "pin_ids": ["pin-uuid-1", "pin-uuid-2"]}
  ]
}
```

---

## AI assistant — MiguelBot

MiguelBot is embedded in the application as a dockable panel (press `F1`).

- **Context-aware** — reads selected components and active nets from the canvas
- **Offline-capable** — runs Llama 3 locally via Ollama, no API key required
- **Standards-aware** — knows ISA 5.1 tags, IEC codes, ANSI designations
- **ERC advisor** — explains electrical rule violations in plain language
- **Forum bridge** — auto-posts to GitHub Discussions when it cannot answer

The same RAG knowledge base (ChromaDB + nomic-embed-text) also powers **ForumBot**, which watches GitHub Discussions and responds within minutes.

---

## GitHub automation

| Workflow | Trigger | Action |
|----------|---------|--------|
| `ci.yml` | Push / PR | Test matrix: Python 3.11+3.12 × Win+Mac+Linux |
| `forumbot_respond.yml` | New Discussion | RAG query → reply → label |
| `forumbot_sync.yml` | Nightly 02:00 UTC | Sync resolved Q&A → ChromaDB |

ForumBot labels: `answered` · `needs-triage` · `confirmed-bug` · `upgrade-candidate` · `erc-issue` · `escalated` · `duplicate`

Add `FORUMBOT_LLM_API_KEY` in **Settings → Secrets → Actions** to enable LLM-powered responses.

---

## Architecture decisions

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-001](docs/adr/ADR-001-tech-stack.md) | Technology stack — Python 3.11, PyQt6, SQLite, `.maproj` | ✅ Accepted |
| [ADR-002](docs/adr/ADR-002-backend-review.md) | Backend Developer code review — all work approved | ✅ Accepted |
| [ADR-003](docs/adr/ADR-003-db-review.md) | Database Specialist code review — all work approved | ✅ Accepted |

---

## Contributing

```bash
git checkout -b feat/your-feature
git commit -m "feat: add ISA 5.1 temperature transmitter symbol"
git push origin feat/your-feature
# → open pull request
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide and commit convention.

**Questions?** Open a [GitHub Discussion](https://github.com/RiCrypto/miguel_angel/discussions) — ForumBot responds within minutes.

---

## Development team

| # | Role | Responsibility |
|---|------|----------------|
| 10 | **Director** (Ricardo Almeida) | Final approval, change authority, version decisions |
| 1 | Agent Scientist Computer | Technical lead · architecture · code review (ADR-001/002/003) |
| 7 | Project Manager | Roadmap · sprint management · status reports |
| 3 | Backend Developer | Core engine · data model · security · file I/O |
| 4 | Frontend Developer | PyQt6 UI · canvas · menus · MiguelBot panel |
| 5 | Database Specialist | SQLite schemas · component library (ISA/IEC/ANSI/IEEE) |
| 2 | Data Scientist | RAG pipeline · auto-router (A\*) · BOM intelligence |
| 6 | Cloud Specialist | CI/CD · GitHub Actions · ForumBot · packaging |
| 8 | Marketing Specialist | Community · open-source outreach · launch |
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
