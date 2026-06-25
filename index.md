# miguel_angel

**Open-source electrical and electronic schematic editor**

---

<div class="grid cards" markdown>

-   :material-lightning-bolt:{ .lg .middle } **Get started in 5 minutes**

    ---

    Install, launch, and draw your first schematic.

    [:octicons-arrow-right-24: Installation](guides/installation.md)

-   :material-book-open:{ .lg .middle } **Standards supported**

    ---

    ISA 5.1 · ISA 5.2 · ISA 5.4 · ISA 95 · IEC 60617 · ANSI/NEMA · IEEE 315

    [:octicons-arrow-right-24: Standards guide](guides/standards.md)

-   :material-robot:{ .lg .middle } **MiguelBot AI assistant**

    ---

    Context-aware AI assistant powered by local Ollama — no API key needed.

    [:octicons-arrow-right-24: MiguelBot guide](guides/miguelbot.md)

-   :material-export:{ .lg .middle } **Export to 4 formats**

    ---

    DXF for AutoCAD/SolidWorks · PDF for printing · SVG for the web · KiCad for PCB.

    [:octicons-arrow-right-24: Export guide](guides/export.md)

</div>

---

## What is miguel_angel?

miguel_angel is a cross-platform, open-source schematic editor for electrical and
electronic engineering. It is built on Python 3.11 and PyQt6, stores projects in
a human-readable JSON format (`.maproj`), and runs entirely locally — nothing is
ever sent to an external server.

### Key features

- **40 built-in symbols** across ISA 5.1, ISA 5.2, ISA 5.4, ISA 95, IEC 60617,
  ANSI/NEMA, and IEEE 315
- **Netlist engine** with spatial pin matching, net label cross-sheet connectivity,
  and Electrical Rules Check (ERC-001 through ERC-004)
- **MiguelBot** — embedded AI assistant using Retrieval-Augmented Generation (RAG)
  with ChromaDB and Ollama; falls back to TF-IDF when Ollama is absent
- **Export engine** — DXF (AutoCAD/SolidWorks), PDF (multi-page), SVG (CSS-classed),
  KiCad legacy .net netlist
- **Dual-factor local auth** — Argon2id password hashing, AES-256 storage,
  TOTP (RFC 6238), FIDO2/YubiKey
- **Cross-platform packages** — .exe (Windows), .app/.dmg (macOS), .deb (Linux),
  built automatically on every version tag via GitHub Actions

---

## Project status

!!! success "96% complete — Phases 1–4 done"
    All implementation is complete and code-reviewed. The documentation site you
    are reading right now is the final Phase 5 deliverable before the v1.0 release.

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Requirements & architecture | ✅ Complete |
| 2 | Core engine (auth · data model · netlist · DB · export) | ✅ Complete |
| 3 | UI & AI assistant (canvas · MiguelBot) | ✅ Complete |
| 4 | Packaging & CI/CD | ✅ Complete |
| 5 | Documentation & public launch | 🔄 In progress |

---

## Quick links

- [GitHub Repository](https://github.com/RiCrypto/miguel_angel)
- [GitHub Discussions](https://github.com/RiCrypto/miguel_angel/discussions) — ask a question (ForumBot will reply)
- [CHANGELOG](https://github.com/RiCrypto/miguel_angel/blob/main/CHANGELOG.md)
- [Architecture Decisions](adr/index.md)
