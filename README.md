<div align="center">

# miguel\_angel

**Open-source electrical and electronic schematic editor**

*ISA · IEC · ANSI · IEEE · Built for engineers who believe professional tools should be free*

[![License: MIT](https://img.shields.io/badge/License-MIT-7F77DD.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-1D9E75.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Tests](https://img.shields.io/badge/Tests-268%20passing-27500A.svg)](tests/)
[![Docs](https://img.shields.io/badge/Docs-MkDocs%20Material-7F77DD.svg)](https://ricrypto.github.io/miguel_angel/)
[![Progress](https://img.shields.io/badge/Progress-98%25-27500A.svg)]()
[![GitHub](https://img.shields.io/badge/GitHub-RiCrypto%2Fmiguel__angel-181825.svg)](https://github.com/RiCrypto/miguel_angel)

**[📖 Documentation](https://ricrypto.github.io/miguel_angel/)** · **[💬 Discussions](https://github.com/RiCrypto/miguel_angel/discussions)** · **[📋 CHANGELOG](CHANGELOG.md)**

</div>

---

## Download

| Platform | File | Notes |
|----------|------|-------|
| Windows 10/11 | `miguel_angel_*_windows_x64.zip` | Unzip → run `miguel_angel.exe` |
| macOS 12+ | `miguel_angel_*_macos.dmg` | Open DMG → drag to Applications |
| Ubuntu 22.04+ | `miguel-angel_*_amd64.deb` | `sudo dpkg -i miguel-angel_*.deb` |

> Downloads appear automatically when a release tag is pushed: `git tag v1.0.0 && git push origin v1.0.0`

---

## Run from source

```bash
git clone https://github.com/RiCrypto/miguel_angel.git
cd miguel_angel
conda create -n miguel_angel python=3.11 && conda activate miguel_angel
pip install -r requirements.txt -r requirements-auth.txt
python -m miguel_angel       # launch
pytest tests/                # 268 tests
```

---

## Standards supported

| Standard | Scope | Symbols |
|----------|-------|:-------:|
| **ISA 5.1** | Instrumentation — indicators, controllers, transmitters, valves, switches | 12 |
| **ISA 5.2** | Binary logic diagrams — AND/OR/NOT, timers, interlocks | 4 |
| **ISA 5.4** | Instrument loop diagrams — I/P converters, positioners, annunciators | 3 |
| **ISA 95** | Enterprise-control integration — PLC, HMI, DCS, SCADA | 3 |
| **IEC 60617** | Electrical symbols — contactors, motors, breakers, transformers | 6 |
| **ANSI / NEMA** | North American electrical — push buttons, relays, fuses | 5 |
| **IEEE 315** | Electronic symbols — R, C, L, diodes, transistors, op-amps | 7 |
| **Custom** | User-defined symbols | ∞ |

---

## Feature overview

### ✅ Security
Argon2id · AES-256 · TOTP (RFC 6238, offline) · FIDO2/YubiKey · 15-min lockout

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
engine.run_erc()            # [ERC-001 unconnected, ...]
engine.to_netlist_dict()    # KiCad-compatible
```

### ✅ Component library (40 symbols)
```python
from miguel_angel.db import LibraryDB
db = LibraryDB(); db.connect()
db.search("temperature controller")   # name · ISA tag · keywords · aliases
db.get_symbol("ISA51:TIC")            # eager-loaded: pins, keywords, aliases
db.stats()   # → {"ISA 5.1": 12, "IEC 60617": 6, ...}
```

### ✅ PyQt6 desktop application
- 8-menu bar (File · Edit · Workspace · Component library · Line types · View · Tools · Help)
- 9-tool vertical toolbar + infinite canvas (zoom 5–2000%)
- Symbol placement: double-click library → click canvas → K1, K2, K3... auto-numbered
- 4 dock panels: Navigator · Library browser · Properties · MiguelBot AI
- Press **F1** to open the AI assistant

### ✅ MiguelBot AI (RAG, offline)
```python
from miguel_angel.miguelbot import MiguelBotService
bot = MiguelBotService(docs_path=Path("docs/"), library_db=db)
bot.start()
answer = bot.ask("How do I wire a motor starter?",
                 schematic_context=canvas.get_context_snapshot())
bot.explain_erc("ERC-001", "Pin K1.PE is unconnected")
bot.suggest_component("measure temperature in a process pipe")
```
Runs on Ollama Llama 3 locally. Falls back to TF-IDF when Ollama is absent.

### ✅ Export (4 formats)
```python
from miguel_angel.export import DXFExporter, PDFExporter, SVGExporter, KiCadExporter
DXFExporter().export_all_sheets(project, Path("output/"))       # AutoCAD/SolidWorks
PDFExporter().export_project(project, Path("project.pdf"))      # A4/A3 multi-page
SVGExporter(scale=2.0).export_sheet(sheet, Path("hires.svg"))   # CSS-classed
KiCadExporter().export_from_project(project, Path("out.net"))   # PCB handoff
```

### ✅ Cross-platform packaging
```bash
pip install pyinstaller==6.10.0
MA_VERSION=1.0.0 pyinstaller packaging/miguel_angel.spec --clean
# Windows → .exe  |  macOS → .app + DMG  |  Linux → binary + .deb
# Or just: git tag v1.0.0 && git push origin v1.0.0 (GitHub Actions does the rest)
```

---

## Documentation

**Full docs:** https://ricrypto.github.io/miguel_angel/

| Section | Contents |
|---------|---------|
| [Getting started](https://ricrypto.github.io/miguel_angel/guides/installation/) | Installation (Win/Mac/Linux) · Quick start · First schematic |
| [User guide](https://ricrypto.github.io/miguel_angel/guides/canvas/) | Canvas · Standards · Wires · MiguelBot · Export · Shortcuts |
| [API reference](https://ricrypto.github.io/miguel_angel/api/) | core · db · miguelbot · export · auth · ui |
| [Architecture decisions](https://ricrypto.github.io/miguel_angel/adr/) | ADR-001 through ADR-009 |

Build locally:
```bash
pip install mkdocs mkdocs-material mkdocstrings mkdocstrings-python
mkdocs serve   # → http://127.0.0.1:8000
```

---

## GitHub automation (5 workflows)

| Workflow | Trigger | Action |
|----------|---------|--------|
| `ci.yml` | Push / PR | Tests on Python 3.11+3.12 × Win+Mac+Linux |
| `release.yml` | `git tag v*.*.*` | Build .exe + .dmg + .deb → GitHub Release |
| `docs.yml` | Push to `docs/**` or `mkdocs.yml` | Deploy to GitHub Pages |
| `forumbot_respond.yml` | New Discussion | RAG → auto-reply → label |
| `forumbot_sync.yml` | Nightly 02:00 UTC | Resolved Q&A → ChromaDB |

---

## Architecture decisions (9 ADRs, 8 bugs found across all reviews)

| ADR | Decision | Bugs |
|-----|----------|------|
| [ADR-001](docs/adr/ADR-001-tech-stack.md) | Technology stack | — |
| [ADR-002](docs/adr/ADR-002-backend-review.md) | Backend Developer review | 0 |
| [ADR-003](docs/adr/ADR-003-db-review.md) | DB Specialist review | 3 |
| [ADR-004](docs/adr/ADR-004-frontend-review.md) | Frontend Developer review | 2 |
| [ADR-005](docs/adr/ADR-005-rag-review.md) | Data Scientist review | 1 |
| [ADR-006](docs/adr/ADR-006-export-review.md) | Export engine review | 1 |
| [ADR-007](docs/adr/ADR-007-symbol-miguelbot-review.md) | Symbol + MiguelBot wiring | 0 |
| [ADR-008](docs/adr/ADR-008-packaging-review.md) | Packaging review | 0 |
| [ADR-009](docs/adr/ADR-009-docs-review.md) | Documentation review | 1 |

---

## Contributing

```bash
git checkout -b feat/your-feature
git commit -m "feat: add revision history undo/redo"
git push origin feat/your-feature
```

See [docs/contributing.md](docs/contributing.md). Questions? Open a [GitHub Discussion](https://github.com/RiCrypto/miguel_angel/discussions) — ForumBot responds within minutes.

---

## Development team

| # | Role | Responsibility |
|---|------|----------------|
| 10 | **Director** (Ricardo Almeida) | Final approval · change authority |
| 1 | Agent Scientist Computer | Technical lead · 9 reviews · 10 status reports |
| 7 | Project Manager | Roadmap · sprint management |
| 3 | Backend Developer | Security · core engine · export |
| 5 | Database Specialist | Component library · standards schemas |
| 4 | Frontend Developer | PyQt6 UI · canvas · symbol placement |
| 2 | Data Scientist | MiguelBot RAG · ChromaDB |
| 6 | Cloud Specialist | CI/CD · packaging · release |
| 9 | Documentation Specialist | MkDocs site · API reference · ADRs |
| 8 | Marketing Specialist | Community · launch strategy |

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
