# miguel_angel

> Open-source desktop application for electrical and electronic schematics.
> Inspired by Eplan, SolidWorks Electrical, and SkiCAD — built for engineers who believe professional tools should be free.

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Tests](https://img.shields.io/badge/Tests-34%20passing-brightgreen.svg)](tests/)
[![Status](https://img.shields.io/badge/Status-Phase%201%20%E2%80%94%20Active%20Development-orange.svg)]()

---

## What is miguel_angel?

**miguel_angel** is a cross-platform, open-source schematic editor for electrical and electronic engineering. It supports international standards including ISA 5.1, ISA 5.2, ISA 5.4, ISA 95, IEC 60617, ANSI/NEMA, and IEEE 315 — giving engineers a free, standards-compliant alternative to expensive proprietary tools.

### Key features (planned — v1.0)

- Canvas-based schematic editor with infinite zoom and pan
- Full ISA 5.1 / IEC 60617 / ANSI / IEEE 315 component symbol libraries
- ISA 5.1 signal line types (process, pneumatic, electric, hydraulic)
- Export to PDF, DXF, SVG, and KiCad netlist
- Electrical Rules Check (ERC) engine
- Auto-wire routing with A* pathfinding
- **MiguelBot** — embedded AI assistant (context-aware, offline-capable via Ollama)
- **ForumBot** — autonomous GitHub Discussions support system
- Dual-factor local security (TOTP + FIDO2/biometric)
- Bill of Materials (BOM) generator
- Multi-sheet project workspace
- Cross-platform: Windows, macOS, Linux

---

## Project status

| Phase | Description | Status | Progress |
|-------|-------------|--------|----------|
| 1 | Requirements & architecture | ✅ Complete | 95% |
| 2 | Core engine development | 🔄 In progress | 42% |
| 3 | UI & schematic editor | 🔄 In progress | 35% |
| 4 | Data, export & integration | 🔄 In progress | 18% |
| 5 | Release & documentation | ⏳ Pending | 0% |

**Overall: 38% complete** — targeting v1.0 release in 12 months.

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| GUI framework | PyQt6 + QGraphicsScene |
| Native file format | `.maproj` (JSON / msgpack) |
| Component library | SQLite 3 + SQLAlchemy |
| Netlist graph | networkx |
| AI assistant | langchain + chromadb + Ollama (Llama 3) |
| Export | ezdxf, reportlab, svgwrite, cairosvg |
| Security | Argon2id, AES-256, pyotp (TOTP), python-fido2 |
| Testing | pytest + pytest-qt |
| CI/CD | GitHub Actions |
| Packaging | PyInstaller (.exe / .app / .deb) |

---

## Getting started

### Prerequisites

- Python 3.11 or higher
- [Anaconda](https://www.anaconda.com/) (recommended) or pip
- Windows 10+, macOS 12+, or Ubuntu 22.04+

### Installation (development)

```bash
# Clone the repository
git clone https://github.com/RiCrypto/miguel_angel.git
cd miguel_angel

# Create conda environment
conda create -n miguel_angel python=3.11
conda activate miguel_angel

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m miguel_angel
```

### Run tests

```bash
pytest tests/ -v
```

---

## Security

miguel_angel runs entirely locally. No data is ever transmitted to external servers.

On first launch, you will be prompted to:

1. Create a personal profile (name, email, organisation, role, country)
2. Set a strong password (Argon2id hashing, AES-256 encrypted storage)
3. Set up TOTP authentication — **Validation 1** (Google Authenticator, Authy, any RFC 6238 app)
4. Register a hardware key or biometric — **Validation 2** (YubiKey / Windows Hello / email OTP fallback)

All profile data is encrypted at rest using a key derived from your password via PBKDF2 (480,000 iterations). See [docs/guides/security.md](docs/guides/security.md) for full details.

---

## Standards supported

| Standard | Description |
|----------|-------------|
| ISA 5.1 | Instrumentation symbols and identification |
| ISA 5.2 | Binary logic diagrams for process operations |
| ISA 5.4 | Instrument loop diagrams |
| ISA 95 | Enterprise-control system integration |
| IEC 60617 | Graphical symbols for diagrams |
| ANSI / NEMA | North American electrical standard |
| IEEE 315 | Graphic symbols for electrical and electronics |

---

## AI assistant — MiguelBot

MiguelBot is embedded directly in the application as a dockable panel (press `F1`). It is context-aware — it knows which components and nets you have selected on the canvas — and answers questions, explains ERC errors in plain language, and suggests components.

MiguelBot runs fully offline using [Ollama](https://ollama.ai) with Llama 3. No API key required.

When MiguelBot cannot answer a question, it automatically posts to the GitHub Discussions forum on your behalf, where **ForumBot** responds within minutes.

---

## Contributing

We welcome contributions from electrical engineers, software developers, and open-source enthusiasts.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'feat: add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

Please read [CONTRIBUTING.md](CONTRIBUTING.md) and follow the [Code of Conduct](CODE_OF_CONDUCT.md).

### Issue categories (GitHub Discussions)

- 🐛 **Bug** — something is not working
- ❓ **How-to** — usage questions (ForumBot will answer automatically)
- 💡 **Feature request** — ideas for new features
- ⚡ **ERC help** — electrical rules check questions
- 📦 **Component library** — missing or incorrect symbols

---

## Project team — agent structure

This project is developed using a structured 10-agent team:

| # | Agent | Responsibility |
|---|-------|----------------|
| 10 | Director (Ricardo Almeida) | Final approval, change authority |
| 1 | Agent Scientist Computer | Technical lead, architecture, coordination |
| 7 | Project Manager | Roadmap, delegation, sprint management |
| 3 | Backend Developer | Core engine, data model, file I/O, security |
| 4 | Frontend Developer | PyQt6 UI, canvas editor, MiguelBot panel |
| 5 | Database Specialist | SQLite schemas, component library, migrations |
| 2 | Data Scientist | RAG pipeline, auto-router, BOM intelligence |
| 6 | Cloud Specialist | CI/CD, GitHub Actions, ForumBot, packaging |
| 8 | Marketing Specialist | Community, positioning, open-source outreach |
| 9 | Documentation Specialist | User guide, API reference, ADRs |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

Built with Python, PyQt6, and the open-source community.
AI assistant powered by [Ollama](https://ollama.ai) and [LangChain](https://langchain.com).
Developed with assistance from [Anthropic Claude](https://anthropic.com).
