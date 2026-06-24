<div align="center">

# miguel\_angel

**Open-source desktop application for electrical and electronic schematics**

*Inspired by Eplan · SolidWorks Electrical · SkiCAD — built for engineers who believe professional tools should be free*

[![License: MIT](https://img.shields.io/badge/License-MIT-7F77DD.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-1D9E75.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Tests](https://img.shields.io/badge/Tests-79%20passing-27500A.svg)](tests/)
[![Phase](https://img.shields.io/badge/Phase-2%20of%205-EF9F27.svg)]()
[![GitHub](https://img.shields.io/badge/GitHub-RiCrypto%2Fmiguel__angel-181825.svg)](https://github.com/RiCrypto/miguel_angel)

</div>

---

## What is miguel\_angel?

**miguel\_angel** is a cross-platform, open-source schematic editor for electrical and electronic engineering. It supports the full range of international instrumentation and electrical standards — giving engineers a free, professional-grade alternative to tools that cost thousands of dollars per seat.

> **Current status:** Active development — Phase 2 of 5. Core engine (security, data model, netlist) is complete. UI and canvas editor are next.

---

## Standards supported

| Standard | Scope | Component categories |
|----------|-------|---------------------|
| **ISA 5.1** | Instrumentation symbols & identification | Temperature, Pressure, Flow, Level, Valves, Controllers, Transmitters |
| **ISA 5.2** | Binary logic diagrams for process operations | AND/OR gates, Interlocks, Timers |
| **ISA 5.4** | Instrument loop diagrams | Loop symbols, Transmitters, Controllers |
| **ISA 95** | Enterprise-control system integration | PLC, HMI, SCADA, MES levels 0–4 |
| **IEC 60617** | Graphical symbols for diagrams | Contactors, Motors, Breakers, Transformers |
| **ANSI / NEMA** | North American electrical standard | Push buttons, Relays, Fuses, Overloads |
| **IEEE 315** | Graphic symbols for electrical & electronics | Resistors, Capacitors, Transistors, ICs |
| **Custom** | User-defined symbols | SVG import, Symbol editor, Team-shareable |

---

## Architecture

```
miguel_angel/
├── auth/           ← Security module (complete ✅)
│   └── profile.py      Argon2id · AES-256 · TOTP · FIDO2
├── core/           ← Schematic engine (complete ✅)
│   ├── models.py       Pydantic v2 data model (Project/Sheet/Component/Net)
│   ├── netlist.py      NetworkX connectivity graph + ERC engine
│   └── fileio.py       .maproj JSON save/load + msgpack sidecar
├── ui/             ← PyQt6 editor (Phase 3 — pending)
│   ├── mainwindow.py   Main window, menu bar (8 menus), toolbar
│   ├── canvas.py       QGraphicsScene infinite canvas
│   ├── wire_tool.py    Click-to-route wire drawing
│   └── miguelbot/      AI assistant dock panel (F1)
├── miguelbot/      ← AI assistant RAG pipeline (Phase 3 — pending)
│   ├── rag.py          LangChain + ChromaDB + Ollama
│   └── context.py      Live schematic state reader
└── export/         ← Export engines (Phase 4 — pending)
    ├── dxf.py          AutoCAD / SolidWorks Electrical (ezdxf)
    ├── pdf.py          PDF print sheets (reportlab)
    ├── svg.py          Vector export (svgwrite)
    └── kicad.py        PCB handoff netlist
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
| Component DB | SQLite + SQLAlchemy | Embedded library, no server needed |
| Geometry | shapely | Hit-testing, selection, collision on canvas |
| AI assistant | LangChain + ChromaDB + Ollama | Offline RAG, no API key required |
| Export | ezdxf · reportlab · svgwrite | DXF, PDF, SVG output |
| Security | argon2-cffi · cryptography · pyotp · fido2 | Dual-factor local auth |
| CI/CD | GitHub Actions | Cross-platform test matrix |
| Packaging | PyInstaller | .exe · .app · .deb single-file bundles |

---

## Project progress

| Phase | Description | Status | Progress |
|-------|-------------|--------|:--------:|
| **1** | Requirements & architecture | ✅ Complete | 100% |
| **2** | Core engine development | 🔄 In progress | 48% |
| **3** | UI & schematic editor | 🔄 Designed | 38% |
| **4** | Data, export & integration | 🔄 Designed | 28% |
| **5** | Release & documentation | ⏳ Pending | 5% |

**Overall: 43% complete** · 79 tests passing · Target: v1.0 in 12 months

---

## What's been built

### ✅ Security module — `miguel_angel/auth/profile.py`

Full local authentication system. Nothing is ever sent off-device.

- **Password**: Argon2id hashing (64 MB memory-hard, GPU-resistant)
- **Encryption**: AES-256 via Fernet; key derived with PBKDF2-HMAC-SHA256 (480,000 iterations)
- **Validation 1**: TOTP (RFC 6238) — works with Google Authenticator, Authy, any TOTP app
- **Validation 2**: FIDO2/WebAuthn (YubiKey), Windows Hello biometric, or email OTP fallback
- **Recovery**: 10 single-use backup codes (SHA-256 hashed, consumed on use)
- **Lockout**: 3 failed attempts → 15-minute lockout → recovery email OTP
- **34 automated tests** · all passing

### ✅ Schematic data model — `miguel_angel/core/models.py`

18 Pydantic v2 models covering every concept in the schematic domain.

```python
from miguel_angel.core import Project, Sheet, Component, Pin, WireSegment, Net
from miguel_angel.core import Point, Standard, ComponentCategory, LineType

# Create a project
project = Project(
    metadata=ProjectMetadata(name="Motor Starter", author="R. Almeida"),
    sheets=[Sheet(name="Power Circuit")]
)

# Place a contactor
k1 = Component(
    symbol_id="IEC:contactor-3P",
    reference="K1",
    position=Point(x=10, y=5),
    standard=Standard.IEC_60617,
    category=ComponentCategory.CONTACTOR,
)
```

Key design: `Component.absolute_pin_position()` computes exact canvas coordinates accounting for rotation (snapped to 90°) and mirroring — the netlist engine depends on this for spatial connectivity.

### ✅ Netlist engine — `miguel_angel/core/netlist.py`

NetworkX graph where every pin is a node and every connection is an edge.

```python
from miguel_angel.core import NetlistEngine

engine = NetlistEngine()
engine.build(project)

# Connectivity queries
engine.is_connected(pin_k1_b.id, pin_k2_a.id)   # → True
engine.get_net_for_pin(pin_id)                    # → "L1"
engine.unconnected_pins()                          # → [...]

# ERC
violations = engine.run_erc()
# → [ERC-001: K1.PE unconnected, ERC-004: output conflict on N003]

# Export
netlist = engine.to_netlist_dict()   # KiCad-compatible
```

Net labels with the same name on any sheet are electrically joined — no physical wire needed. ERC rules implemented: ERC-001 (unconnected pin), ERC-002 (dead-end wire), ERC-003 (power short), ERC-004 (output conflict).

### ✅ File I/O engine — `miguel_angel/core/fileio.py`

Save and load `.maproj` project files.

```python
from miguel_angel.core import MAprojIO
from pathlib import Path

io = MAprojIO()

# Create blank project
project = MAprojIO.new_project("Motor Starter", author="R. Almeida")

# Save — writes motor_starter.maproj (JSON) + .bak backup
io.save(project, Path("motor_starter.maproj"))

# Load
project = io.load(Path("motor_starter.maproj"))

# Fast metadata preview (no full parse)
meta = MAprojIO.read_metadata_only(Path("motor_starter.maproj"))
```

`.maproj` is UTF-8 JSON with 2-space indentation — human-readable and git-diffable. For projects over 1 MB, a msgpack binary sidecar is written automatically for faster loading.

---

## Getting started

### Prerequisites

- Python 3.11 or higher
- [Anaconda](https://www.anaconda.com/) (recommended) or pip
- Windows 10+, macOS 12+, or Ubuntu 22.04+
- [Ollama](https://ollama.ai) (optional — for MiguelBot AI assistant offline mode)

### Installation

```bash
# Clone
git clone https://github.com/RiCrypto/miguel_angel.git
cd miguel_angel

# Create conda environment
conda create -n miguel_angel python=3.11
conda activate miguel_angel

# Install — core + auth
pip install -r requirements.txt
pip install -r requirements-auth.txt

# Run tests
pytest tests/ -v
```

### Windows path note

If you are working from the default project root on Windows:

```
C:\Users\ralmeida\Documents\Documentos\Minha Bibliteca\Scripts de Programas\Python\miguel_angel
```

Always wrap the path in quotes in the terminal:

```bash
cd "C:\Users\ralmeida\Documents\Documentos\Minha Bibliteca\Scripts de Programas\Python\miguel_angel"
```

---

## Security

miguel\_angel runs entirely locally. No data is ever transmitted to external servers.

First launch opens a 5-step setup wizard:

1. **Profile** — name, email, organisation, role, country
2. **Password** — min 12 chars, Argon2id hashed, AES-256 encrypted at rest
3. **Validation 1** — TOTP QR code (scan with any authenticator app)
4. **Validation 2** — YubiKey / Windows Hello / email OTP
5. **Complete** — session token issued, app unlocks

See [docs/guides/security.md](docs/guides/security.md) for full details.

---

## AI assistant — MiguelBot

MiguelBot is embedded in the application as a dockable panel (press `F1`).

- **Context-aware** — knows which components and nets are selected on the canvas
- **Offline-capable** — runs Llama 3 via Ollama, no API key required
- **ERC advisor** — explains electrical rule violations in plain language
- **Forum bridge** — if MiguelBot can't answer, it posts to GitHub Discussions automatically

When a question stumps MiguelBot, **ForumBot** (a GitHub Actions bot) responds within minutes from the same RAG knowledge base, drawing on the documentation, component library, and all previously resolved discussions.

---

## Automated forum — ForumBot

Three GitHub Actions workflows power the autonomous support system:

| Workflow | Trigger | Action |
|----------|---------|--------|
| `forumbot_respond.yml` | New GitHub Discussion | RAG query → reply → label |
| `forumbot_sync.yml` | Nightly 02:00 UTC | Sync resolved Q&A → ChromaDB |
| `ci.yml` | Push / PR | Test matrix: Python 3.11+3.12 × Win+Mac+Linux |

ForumBot labels: `answered` · `needs-triage` · `confirmed-bug` · `upgrade-candidate` · `erc-issue` · `escalated` · `duplicate`

To enable LLM-powered responses, add `FORUMBOT_LLM_API_KEY` in **Settings → Secrets → Actions**.

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
      "components": [ { "id": "...", "reference": "K1", "position": {"x": 10, "y": 5}, "..." } ],
      "wires": [ { "start": {"x": 14, "y": 5}, "end": {"x": 20, "y": 5}, "line_type": "Generic" } ],
      "net_labels": [ { "net_name": "L1", "position": {"x": 14, "y": 5} } ]
    }
  ],
  "nets": [
    { "id": "uuid", "name": "L1", "pin_ids": ["pin-uuid-1", "pin-uuid-2"] }
  ]
}
```

---

## Contributing

Contributions from electrical engineers, software developers, and technical writers are welcome.

```bash
# Fork, branch, commit, push, PR
git checkout -b feat/your-feature
git commit -m "feat: add ISA 5.1 temperature transmitter symbol"
git push origin feat/your-feature
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide, commit convention, and PR checklist.

**Questions?** Open a [GitHub Discussion](https://github.com/RiCrypto/miguel_angel/discussions) — ForumBot will respond within minutes.

---

## Development team

| # | Role | Responsibility |
|---|------|----------------|
| 10 | **Director** (Ricardo Almeida) | Final approval, change authority, version decisions |
| 1 | Agent Scientist Computer | Technical lead, architecture, code review, agent coordination |
| 7 | Project Manager | Roadmap, sprint management, status reports |
| 3 | Backend Developer | Core engine, data model, security, file I/O |
| 4 | Frontend Developer | PyQt6 UI, canvas, menus, MiguelBot panel |
| 5 | Database Specialist | SQLite schemas, component library (ISA/IEC/ANSI/IEEE) |
| 2 | Data Scientist | RAG pipeline, auto-router (A\*), BOM intelligence |
| 6 | Cloud Specialist | CI/CD, GitHub Actions, ForumBot, cross-platform builds |
| 8 | Marketing Specialist | Community, open-source outreach, launch |
| 9 | Documentation Specialist | User guide, API reference, ADRs |

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
