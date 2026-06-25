<div align="center">

# miguel\_angel

**Open-source desktop application for electrical and electronic schematics**

*Inspired by Eplan · SolidWorks Electrical · SkiCAD — built for engineers who believe professional tools should be free*

[![License: MIT](https://img.shields.io/badge/License-MIT-7F77DD.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-1D9E75.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Tests](https://img.shields.io/badge/Tests-268%20passing-27500A.svg)](tests/)
[![Progress](https://img.shields.io/badge/Progress-96%25-7F77DD.svg)]()
[![Release](https://img.shields.io/badge/Release-v0.1.0--dev-EF9F27.svg)]()
[![GitHub](https://img.shields.io/badge/GitHub-RiCrypto%2Fmiguel__angel-181825.svg)](https://github.com/RiCrypto/miguel_angel)

</div>

---

## What is miguel\_angel?

**miguel\_angel** is a cross-platform, open-source schematic editor for electrical and electronic engineering. It supports the full range of international instrumentation and electrical standards — giving engineers a free, professional-grade alternative to tools that cost thousands of dollars per seat.

> **Status:** 96% complete — all implementation done. MkDocs site and public launch are the only remaining items. Ready to download and run.

---

## Download

> **Note:** The repository is being prepared for public release. Downloads will appear here once the first tag (`v1.0.0`) is pushed.

| Platform | File | Notes |
|----------|------|-------|
| Windows 10/11 | `miguel_angel_*_windows_x64.zip` | Unzip and run `miguel_angel.exe` |
| macOS 12+ | `miguel_angel_*_macos.dmg` | Open DMG, drag to Applications |
| Ubuntu 22.04+ | `miguel-angel_*_amd64.deb` | `sudo dpkg -i miguel-angel_*.deb` |

### Optional: MiguelBot AI assistant
```bash
# Install Ollama then pull the two models used by MiguelBot
brew install ollama       # macOS — or https://ollama.ai for Windows/Linux
ollama pull llama3
ollama pull nomic-embed-text
```

---

## Run from source

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
| **ISA 5.2** | Binary logic diagrams for process operations | 4 |
| **ISA 5.4** | Instrument loop diagrams | 3 |
| **ISA 95** | Enterprise-control integration (PLC/HMI/SCADA) | 3 |
| **IEC 60617** | Graphical symbols for electrical diagrams | 6 |
| **ANSI / NEMA** | North American electrical standard | 5 |
| **IEEE 315** | Electronic component symbols | 7 |
| **Custom** | User-defined symbols | ∞ |

**40 symbols · 11 line types · 8 ADRs · 268/268 tests · 0 known bugs**

---

## What's inside

### ✅ Security — local, dual-factor auth
Argon2id password hashing · AES-256 encryption · TOTP (offline, RFC 6238) · FIDO2/YubiKey · 15-min lockout

### ✅ Schematic engine
```python
from miguel_angel.core import Project, Component, NetlistEngine, MAprojIO, Point, Standard

project = MAprojIO.new_project("Motor Starter")
project.sheets[0].components.append(
    Component(symbol_id="ISA51:TIC", reference="TIC-101",
              position=Point(x=10, y=5), standard=Standard.ISA_5_1)
)
MAprojIO().save(project, Path("motor_starter.maproj"))

engine = NetlistEngine(); engine.build(project)
violations   = engine.run_erc()          # ERC-001 unconnected pin, ...
netlist_dict = engine.to_netlist_dict()  # KiCad-compatible
```

### ✅ Component library (40 symbols, all 7 standards)
```python
from miguel_angel.db import LibraryDB
db = LibraryDB(); db.connect()
db.search("temperature controller")  # full-text: name · tag · keywords · aliases
db.get_symbol("ISA51:TIC")           # eager-loaded with pins, keywords, aliases
```

### ✅ Main window (PyQt6 desktop application)
- 8-menu bar with all ISA/IEC/ANSI/IEEE sub-menus and line type selections
- 9-tool vertical toolbar: Select · Pan · Wire · Junction · Symbol · Power · Ground · Label · Text
- Infinite canvas: zoom 5–2000% · orthogonal wire routing · dot-grid snap
- Symbol placement: double-click library browser → click canvas to place, auto-increments K1/K2/K3...
- 4 dock panels: Project navigator · Library browser · Properties · MiguelBot AI

### ✅ MiguelBot AI assistant (F1 to open)
Context-aware AI panel that reads your selected components in real time:
```python
from miguel_angel.miguelbot import MiguelBotService

bot = MiguelBotService(docs_path=Path("docs/"), library_db=db)
bot.start()   # ingests docs + components + ERC rules (idempotent)

answer = bot.ask("How do I wire a motor starter?",
                 schematic_context=canvas.get_context_snapshot())
# → grounded in docs, component library, and your active schematic
bot.explain_erc("ERC-001", "Pin K1.PE is unconnected")
bot.suggest_component("measure temperature in a process pipe")
```
Runs **fully offline** with Ollama Llama 3. Falls back to TF-IDF when Ollama is absent.

### ✅ Export engine (4 formats)
```python
from miguel_angel.export import DXFExporter, PDFExporter, SVGExporter, KiCadExporter

DXFExporter().export_all_sheets(project, Path("output/"))    # AutoCAD/SolidWorks compatible
PDFExporter().export_project(project, Path("project.pdf"))   # multi-page A4/A3
SVGExporter().export_sheet(sheet, Path("sheet.svg"))         # CSS-classed vector SVG
KiCadExporter().export_from_project(project, Path("out.net"))# PCB handoff .net XML
```

### ✅ Cross-platform packaging
```bash
# Build for your platform:
pip install pyinstaller==6.10.0
MA_VERSION=1.0.0 pyinstaller packaging/miguel_angel.spec --clean

# Release (triggers GitHub Actions — builds all 3 platforms):
git tag v1.0.0 && git push origin v1.0.0
```
See [packaging/BUILD.md](packaging/BUILD.md) for detailed build instructions.

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
| AI (store) | ChromaDB | ✅ |
| AI (embed) | Ollama / sentence-transformers / TF-IDF | ✅ |
| AI (gen) | Ollama Llama 3 / OpenAI-compatible / fallback | ✅ |
| Export | ezdxf · reportlab · svgwrite | ✅ |
| Packaging | PyInstaller 6.10.0 | ✅ |
| CI/CD | GitHub Actions | ✅ |
| Releases | GitHub Releases + DMG + ZIP + .deb | ✅ |

---

## Project progress

| Phase | Description | Status | Progress |
|-------|-------------|--------|:--------:|
| **1** | Requirements & architecture | ✅ Complete | 100% |
| **2** | Core engine | ✅ Complete | 100% |
| **3** | UI & AI assistant | ✅ Complete | 100% |
| **4** | Export, packaging & integration | ✅ Complete | 100% |
| **5** | Documentation & public launch | 🔄 In progress | 35% |

**Overall: 96% · 268/268 tests · 7,999 lines · 73 files · 8 ADRs · 0 bugs**

---

## Releasing a new version

```bash
# 1. Update version in pyproject.toml and CHANGELOG.md
# 2. Commit and tag
git add .
git commit -m "chore: release v1.0.0"
git tag v1.0.0
git push origin main --tags

# 3. GitHub Actions automatically:
#    ✓ Builds Windows .exe (windows-latest)
#    ✓ Builds macOS .dmg  (macos-latest)
#    ✓ Builds Linux .deb  (ubuntu-22.04)
#    ✓ Creates GitHub Release with all 3 attached
```

---

## GitHub automation

| Workflow | Trigger | Action |
|----------|---------|--------|
| `ci.yml` | Push / PR | Python 3.11+3.12 × Win+Mac+Linux |
| `release.yml` | `git tag v*.*.*` | Build .exe + .dmg + .deb → GitHub Release |
| `forumbot_respond.yml` | New Discussion | RAG → auto-reply → label |
| `forumbot_sync.yml` | Nightly 02:00 UTC | Resolved Q&A → ChromaDB |

Add `FORUMBOT_LLM_API_KEY` in **Settings → Secrets → Actions** to enable ForumBot LLM responses.

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
| [ADR-008](docs/adr/ADR-008-packaging-review.md) | Packaging + release workflow — 0 bugs | ✅ |

---

## Contributing

```bash
git checkout -b feat/your-feature
git commit -m "feat: add revision history undo/redo"
git push origin feat/your-feature
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Questions? Open a [GitHub Discussion](https://github.com/RiCrypto/miguel_angel/discussions).

---

## Development team

| # | Role | Responsibility |
|---|------|----------------|
| 10 | **Director** (Ricardo Almeida) | Final approval · change authority |
| 1 | Agent Scientist Computer | Technical lead · 8 reviews · 9 status reports |
| 7 | Project Manager | Roadmap · task delegation |
| 3 | Backend Developer | Security · data model · netlist · file I/O · export |
| 5 | Database Specialist | Component library · ISA/IEC/ANSI/IEEE schemas |
| 4 | Frontend Developer | PyQt6 UI · canvas · symbol placement · MiguelBot wiring |
| 2 | Data Scientist | RAG pipeline · MiguelBot · ChromaDB |
| 6 | Cloud Specialist | CI/CD · GitHub Actions · ForumBot · packaging |
| 8 | Marketing Specialist | Community · open-source outreach |
| 9 | Documentation Specialist | User guide · API reference · ADRs |

---

## License

MIT — see [LICENSE](LICENSE).
Built with Python, PyQt6, ezdxf, reportlab, svgwrite, and ChromaDB.
AI assistant powered by [Ollama](https://ollama.ai).
Developed with assistance from [Anthropic Claude](https://anthropic.com).

---

<div align="center">
<sub>⚡ miguel_angel — professional electrical schematics, open source, free forever</sub>
</div>
