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
