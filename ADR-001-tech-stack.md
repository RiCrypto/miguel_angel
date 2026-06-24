# ADR-001 — Technology stack selection

**Date**: 2025-06-01
**Status**: Accepted
**Author**: Agent Scientist Computer
**Approved by**: Director (Ricardo Almeida)

---

## Context

The miguel_angel project requires a cross-platform desktop application for electrical and electronic schematics. The technology stack must support a zoomable canvas editor, an embedded AI assistant, complex file I/O, and a standards-compliant component library — while remaining accessible to open-source contributors.

## Decision

The following stack was selected and approved by the Director:

| Layer | Decision | Rationale |
|-------|----------|-----------|
| Language | Python 3.11 | Anaconda-native, rich ecosystem, large contributor base |
| GUI | PyQt6 | `QGraphicsScene` provides professional-grade zoomable canvas; same Qt foundation as Eplan |
| File format | `.maproj` (JSON) | Human-readable, git-diffable, no proprietary lock-in |
| Database | SQLite 3 + SQLAlchemy | Embedded, no server, Anaconda-bundled |
| Netlist | networkx | Graph-native model for components (nodes) and wires (edges) |
| Geometry | shapely | Hit-testing and selection on canvas |
| AI | langchain + chromadb + Ollama | Fully offline RAG, no API key required |
| Export | ezdxf + reportlab + svgwrite | DXF (AutoCAD/SolidWorks compat.), PDF, SVG |
| Security | argon2-cffi + cryptography + pyotp + fido2 | Argon2id hashing, AES-256 encryption, TOTP, FIDO2 |
| CI/CD | GitHub Actions | Free for open-source, cross-platform matrix builds |
| Packaging | PyInstaller | Single-file executables for Windows, macOS, Linux |

## Alternatives considered

- **C++ / Qt6 directly**: higher performance, but dramatically narrows contributor pool and slows development.
- **Electron + TypeScript**: cross-platform, modern, but not Python-native (breaks Anaconda workflow) and significantly heavier.
- **wxPython**: Python-native but older canvas primitives; `QGraphicsScene` is superior for CAD-style interaction.
- **PySide6**: nearly identical to PyQt6 but less community documentation at the time of decision.

## Consequences

- All agents must use Python 3.11+ and follow type annotations (`mypy` enforced in CI).
- The `.maproj` JSON schema is the single source of truth for the data model.
- SQLite means no server infrastructure — simplifies installation and air-gapped deployments.
- Ollama must be installed separately by users who want MiguelBot offline; cloud API fallback is available.
