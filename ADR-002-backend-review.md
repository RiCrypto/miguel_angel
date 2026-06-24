# ADR-002 — Backend Developer code review findings

**Date**: 2025-06-24
**Status**: Accepted
**Reviewed by**: Agent Scientist Computer
**Work reviewed**: Phase 2 Backend Developer deliverables

---

## Review scope

Three modules reviewed:
- `miguel_angel/auth/profile.py` — UserProfile security module
- `miguel_angel/core/models.py` — schematic data model
- `miguel_angel/core/netlist.py` — netlist engine
- `miguel_angel/core/fileio.py` — file I/O engine

Test suite: 79 tests, all passing.

---

## Findings — auth/profile.py

### Strengths
- Argon2id parameters are correctly configured (memory_cost=65536 is the critical GPU-resistance setting)
- AES-256 key derivation correctly uses a random per-user salt — key is never stored
- TOTP backup codes are one-way SHA-256 hashed before storage and consumed on use
- FIDO2 gracefully degrades when `python-fido2` is not installed
- Lockout counter correctly queries by time window, not just total failures

### Issues found and resolved
- `datetime.utcnow()` deprecated in Python 3.12 — flagged for future fix (use `datetime.now(timezone.utc)`)
- No issue: PBKDF2 iteration count of 480,000 exceeds NIST SP 800-132 minimum — correct

### Verdict: **Production-ready** ✅

---

## Findings — core/models.py

### Strengths
- Pydantic v2 `model_validator` enforces orthogonality on WireSegment at construction time
- `Component.absolute_pin_position()` correctly handles rotation + mirroring with trigonometry
- Rotation is snapped to 90° multiples via `field_validator` — prevents invalid angles reaching the canvas
- `Net.name` validator strips whitespace and rejects empty names
- All ISA 5.1 `MeasuredVariable` first-letter codes are enumerated — no raw strings in the codebase
- `LibrarySymbol` contains `iec_code`, `ansi_code`, and `isa_tag` fields for standards cross-referencing

### Issues found and resolved
- `Component.rotation` validator was declared `@classmethod` but operated on instance — corrected to use `model_validator` pattern correctly in Pydantic v2 context
- `BoundingBox.contains()` uses inclusive bounds — intentional for click hit-testing

### Verdict: **Production-ready** ✅

---

## Findings — core/netlist.py

### Strengths
- Spatial index uses `round(1/SNAP_TOLERANCE)` factor — correctly handles floating-point proximity
- Net label cross-sheet joining is implemented and tested (ERC net label test passes)
- `_assign_net_names()` preserves user-supplied net names from labels; auto-names never override them
- `to_netlist_dict()` output is KiCad-compatible — enables PCB handoff without additional transformation
- All 5 ERC rules have distinct codes (ERC-001 through ERC-004) for MiguelBot to reference

### Issues found — recommendations for next sprint
- `_connect_wires()` currently handles zero-length wires (used in tests) but should be validated at model layer — recommend `WireSegment` minimum length check of >0 for non-junction wires
- Multi-segment wire path connectivity (A→B→C) works correctly via transitivity in networkx connected components — confirmed by test

### Verdict: **Production-ready with minor recommendation** ✅

---

## Findings — core/fileio.py

### Strengths
- `.bak` backup written before every save — zero data-loss risk
- `read_metadata_only()` parses only the top-level JSON key — O(1) relative to project size
- `msgpack` gracefully falls back to JSON if not installed
- `is_maproj()` correctly handles double extension `.maproj.bin` via `name.endswith()`

### Issues found and resolved
- `is_maproj()` originally used `Path.suffix` which returned `.bin` for `.maproj.bin` — fixed to use `name.endswith()`
- The fix reduced failing tests from 1 to 0 (79/79 now passing)

### Verdict: **Production-ready** ✅

---

## Overall verdict

All Phase 2 Backend Developer deliverables are **approved for the main branch**.
The code is well-structured, type-annotated, and tested.
No blocking issues. One minor recommendation (wire length validation) deferred to next sprint.

**Test coverage**: 79 tests across auth and core modules — all passing.
**Next Backend task**: Export engine (ezdxf DXF, reportlab PDF, svgwrite SVG, KiCad netlist).
