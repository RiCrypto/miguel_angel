# Quick start

This guide walks you from a blank application to a saved schematic in under 10 minutes.

---

## 1. First launch — registration wizard

On first launch, miguel_angel runs a 5-step setup wizard:

1. **Profile** — enter your name, email, and organisation
2. **Password** — choose a password (min. 12 characters; strength meter shown)
3. **TOTP** — scan the QR code with Google Authenticator, Authy, or any TOTP app
4. **Hardware key** *(optional)* — register a YubiKey or Windows Hello credential
5. **Complete** — your profile is encrypted and saved locally

!!! info "Everything stays local"
    Your profile, component library, and MiguelBot vector store are all stored in
    your OS app data directory. Nothing is ever sent to an external server.

---

## 2. The main window

After logging in, you will see:

```
┌──────────────────────────────────────────────────────────────────────┐
│  File  Edit  Workspace  Component library  Line types  View  Tools  Help │
├─────┬────────────────────────────────────────────┬───────────────────┤
│     │                                            │  Component        │
│  ↖  │                                            │  library          │
│  ✥  │          Infinite schematic canvas         │                   │
│  ─  │                                            ├───────────────────┤
│  •  │                                            │  Properties       │
│  ⊕  │                                            │                   │
│  ⚡  │                                            │                   │
│  ⏚  │                                            │                   │
│  A  │                                            │                   │
│  T  ├────────────────────────────────────────────┤                   │
│     │ Select  x: 0.0  y: 0.0  100%  ERC: —      │                   │
└─────┴────────────────────────────────────────────┴───────────────────┘
```

| Area | Description |
|------|-------------|
| Left toolbar | Tool palette — Select, Pan, Wire, Junction, Symbol, Power, Ground, Label, Text |
| Central canvas | Infinite schematic surface — zoom with mouse wheel, pan with middle-click |
| Right panel (top) | Component library browser |
| Right panel (bottom) | Properties panel for selected components |
| Status bar | Active tool · cursor position · zoom level · ERC status |

Press **F1** to open the MiguelBot AI assistant panel.

---

## 3. Place your first component

1. In the **Component library** panel (right side), type `TIC` in the search box
2. Double-click **Temperature indicator controller (ISA 5.1)**
3. The toolbar switches to the Symbol tool (⊕) and the cursor becomes a crosshair
4. Click anywhere on the canvas to place **TIC-1**
5. Click again to place **TIC-2**, and so on
6. Press **Escape** to return to the Select tool

---

## 4. Draw a wire

1. Press **W** to activate the Wire tool (or click **─** in the toolbar)
2. Click on a pin (small cross-hair on the symbol edge) to start a wire
3. Click on another pin or the end point to finish
4. The wire snaps to horizontal/vertical automatically
5. Press **Escape** to cancel a wire in progress

---

## 5. Save your project

Press **Ctrl+S**. The save dialog opens on first save — choose a location and name.

Projects are saved as `.maproj` files — human-readable JSON that you can commit to
git and diff in pull requests.

```bash
git add motor_starter.maproj
git commit -m "feat: add motor starter schematic"
```

---

## 6. Run the ERC check

Press **F5** or go to **Tools → Run ERC check**. The status bar shows:

- ✓ green — no violations
- 🔴 N issues — click to see details

Common ERC rules:

| Code | Meaning | Fix |
|------|---------|-----|
| ERC-001 | Unconnected pin | Wire the pin or add a No-Connect marker |
| ERC-002 | Dead-end wire (one endpoint) | Connect both ends of every wire |
| ERC-003 | Power-to-power short | Verify both power pins have the same voltage |
| ERC-004 | Output conflict | Two output pins on the same net |

Ask MiguelBot to explain any ERC error: select the error in the panel and click
**Ask MiguelBot**.

---

## 7. Export

Go to **File → Export** and choose a format:

| Format | Use case |
|--------|---------|
| **DXF** | Import into AutoCAD or SolidWorks Electrical |
| **PDF** | Print or share as a document |
| **SVG** | Embed in web pages or documentation |
| **KiCad netlist** | Hand off to a PCB designer |

---

## Next steps

- [Your first full schematic](first-schematic.md) — a complete motor starter example
- [Standards and symbols reference](standards.md)
- [MiguelBot AI assistant](miguelbot.md)
- [Keyboard shortcuts](shortcuts.md)
