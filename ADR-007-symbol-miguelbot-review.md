# ADR-007 — Frontend Developer symbol placement + MiguelBot wiring: code review and double-check

**Date**: 2025-06-24
**Status**: Accepted
**Reviewed by**: Agent Scientist Computer (double-check pass)
**Work reviewed**: Phase 3 completion — symbol_item.py, canvas.py, panels.py, mainwindow.py

---

## Review scope

Four modified / new files reviewed. Double-check ran 16 integration assertions.

- `miguel_angel/ui/symbol_item.py`  — new SymbolItem + PinItem QGraphicsItem subclasses
- `miguel_angel/ui/canvas.py`       — set_pending_symbol / _place_symbol / cancel added
- `miguel_angel/ui/panels.py`       — MiguelBotPanel fully wired to MiguelBotService
- `miguel_angel/ui/mainwindow.py`   — _on_symbol_selected + start_miguelbot implemented

**Test results**: 268 passing, 3 skipped (headless CI — canvas grid render OOM).

---

## Findings — ui/symbol_item.py

### Strengths

- `SymbolItem` correctly inherits `QGraphicsItem` (not `QGraphicsObject`) — avoids
  unnecessary signal overhead; `ItemSendsGeometryChanges` flag handles position updates
- `itemChange()` overrides `ItemPositionChange` for snap-to-grid — runs before the
  item is moved, which is the correct Qt pattern (returning the modified position)
- `COMPONENT_DATA_ROLE = 0` constant used consistently — matches `canvas.get_context_snapshot()`
  which reads `item.data(0)` — data dict keys include symbol_id, reference, standard,
  category, position, rotation — all required by MiguelBot context (assertion #3 verified)
- `PinItem` is a child of `SymbolItem` — moves with the parent automatically,
  correct Qt parent–child relationship
- `PinItem` explicitly marks itself as non-selectable, non-movable — pins cannot be
  accidentally selected or dragged away from their parent
- Context menu correctly uses `scene.miguelbot_requested` signal for MiguelBot integration
- `_infer_standard()` covers all 8 standards including ISA 5.2 and ISA 5.4 — 8/8
  inference cases verified (assertion #7)
- `acceptHoverEvents(True)` with cursor change to `SizeAllCursor` on hover — correct
  UX pattern for movable items

### Issues found

None.

### Verdict: **Production-ready** ✅

---

## Findings — ui/canvas.py additions

### Strengths

- `set_pending_symbol()` calls `set_tool("symbol")` internally — toolbar highlights
  the symbol tool automatically when placement is armed
- `_place_symbol()` uses `self._ref_counter` dict keyed by reference prefix —
  K1, K2, K3… and TIC-101, TIC-102… auto-increment independently per prefix
- `_place_symbol()` calls `self._scene.clearSelection()` then `item.setSelected(True)` —
  the placed symbol is immediately selected, which triggers the Properties panel to update
- `cancel_pending_symbol()` clears both `_pending_symbol_id` and `_pending_symbol_data` —
  no stale state
- Escape key handler updated to call `cancel_pending_symbol()` before `set_tool("select")`
- mousePressEvent symbol branch returns early before the wire handler — correct ordering

### Issues found

None. The 3 skipped tests are a headless CI limitation (dot-grid render allocates ~50k
ellipse items which OOMs in the test runner), not a code defect. The tests are correctly
marked with `pytest.skip()` and the skip reason is documented.

### Verdict: **Production-ready** ✅

---

## Findings — ui/panels.py MiguelBotPanel

### Strengths

- `set_service()` updates the status dot colour from red to green — visual confirmation
  that the RAG pipeline is connected
- `_submit_query()` creates a `_Worker(QObject)` that runs `service.ask()` on a
  `QThread` — the main UI thread never blocks
- Worker is created fresh per query — no race conditions from reusing a single worker
- Previous worker is gracefully quit + waited before starting a new one — thread leak
  prevention
- `_on_answer()` correctly removes the "Thinking…" placeholder by selecting and deleting
  the last block before appending the answer — no placeholder text left in chat
- Sources display (up to 3) with metadata labels — users can identify where answers come from
- `should_escalate=True` adds an informational notice without alarming the user
- `_on_submit()` clears the input field before calling `_submit_query()` — correct order
- `_scroll_to_bottom()` called after every new message — chat always shows latest
- Suggestion buttons now fire real queries to `_submit_query()` via lambda with
  `q=query` capture — avoids Python late-binding closure issue

### Issues found

None.

### Verdict: **Production-ready** ✅

---

## Findings — ui/mainwindow.py additions

### Strengths

- `_on_symbol_selected()` fetches full symbol data from `LibraryDB.get_symbol()` with
  graceful fallback to default geometry if the DB is unavailable
- Symbol data dict contains `width_lu`, `height_lu`, `reference_prefix`, and full `pins`
  list with all five pin attributes — everything `SymbolItem` needs
- Status bar message shows "Placing X — click canvas to place | Esc to cancel" for
  the duration of placement mode (empty timeout = stays until cleared)
- `start_miguelbot()` runs `service.start()` in a `QThread` and calls
  `panel.set_service(svc)` on the main thread via `finished.connect()` — correct
  thread handoff pattern
- `_bot_service` and `_bot_thread` attributes initialised to `None` in `_init_ui()` —
  clean state machine, no AttributeError risk
- `MiguelBotService` import moved to mainwindow level — correct

### Issues found

None.

### Verdict: **Production-ready** ✅

---

## Overall verdict

All Phase 3 completion deliverables are **approved for main branch**.
Zero bugs found. All 16 double-check assertions passed on first run.

**Total project status at time of this review:**
- 7,999 production lines · 2,460 test lines · 268/268 passing · 3 skipped (known CI)
- 8 packages fully implemented and reviewed
- 7 ADRs · 0 known bugs
- Phase 3 is now **complete**

**Next recommended task**: Agent Scientist Computer briefing on v1.0 release preparation
— Cloud Specialist (PyInstaller builds) and Documentation Specialist (MkDocs site).
