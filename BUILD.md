# miguel_angel — Packaging Guide

This directory contains all build artifacts for packaging miguel_angel
as a standalone desktop application.

---

## Quick build

```bash
# 1. Install build dependency
pip install pyinstaller==6.10.0

# 2. Build for your current platform
#    ⚠️  IMPORTANT: always run from the PROJECT ROOT (not from packaging/)
cd miguel_angel-main               # or wherever the project root is
pyinstaller packaging/miguel_angel.spec --clean --noconfirm

# 3. Find your output in:
#   Windows  →  dist\miguel_angel\miguel_angel.exe
#   macOS    →  dist/miguel_angel.app
#   Linux    →  dist/miguel_angel/miguel_angel
```

> **Note:** PyInstaller does NOT cross-compile. Run on each platform to get that platform's binary.
>
> **⚠️ Must run from the project root.** The spec uses `SPECPATH` (the directory
> containing the .spec file) to locate `miguel_angel/__main__.py` and all data files.
> Running `cd packaging && pyinstaller miguel_angel.spec` will fail.

---

## Build options

| Environment variable | Default | Effect |
|---------------------|---------|--------|
| `MA_VERSION` | `0.1.0` | Version string embedded in the binary |
| `MA_ONE_FILE` | `0` | `1` = produce a single executable file |
| `MA_CONSOLE` | `0` | `1` = show a terminal window (debugging) |

Example:
```bash
MA_VERSION=1.0.0 pyinstaller packaging/miguel_angel.spec --clean
```

---

## Platform-specific steps

### Windows → .exe

```powershell
pip install pyinstaller==6.10.0
$env:MA_VERSION="1.0.0"
pyinstaller packaging/miguel_angel.spec --clean --noconfirm
# Output: dist\miguel_angel\miguel_angel.exe
```

### macOS → .app + DMG

```bash
pip install pyinstaller==6.10.0
MA_VERSION=1.0.0 pyinstaller packaging/miguel_angel.spec --clean --noconfirm
# Notarise (optional, requires Apple Developer account):
bash packaging/scripts/notarise_mac.sh 1.0.0
# Create DMG:
hdiutil create -volname "miguel_angel 1.0.0" \
  -srcfolder dist/miguel_angel.app -ov -format UDZO \
  dist/miguel_angel_1.0.0_macos.dmg
```

### Linux → binary + .deb

```bash
# System deps (Ubuntu/Debian):
sudo apt-get install libxcb-cursor0 dpkg-dev fakeroot

pip install pyinstaller==6.10.0
MA_VERSION=1.0.0 pyinstaller packaging/miguel_angel.spec --clean --noconfirm

# Build .deb:
bash packaging/scripts/build_deb.sh 1.0.0
# Output: dist/miguel-angel_1.0.0_amd64.deb
# Install: sudo dpkg -i dist/miguel-angel_1.0.0_amd64.deb
```

---

## Automated releases via GitHub Actions

Push a version tag to trigger the release workflow:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow (`.github/workflows/release.yml`) will:
1. Build Windows .exe on `windows-latest`
2. Build macOS .app + DMG on `macos-latest`
3. Build Linux .deb on `ubuntu-22.04`
4. Create a GitHub Release with all three artifacts attached

Required GitHub Secrets (for macOS notarisation — optional):
- `APPLE_SIGNING_IDENTITY` — Developer ID Application certificate name
- `APPLE_ID` — Apple ID email
- `APPLE_APP_PASSWORD` — App-specific password from appleid.apple.com
- `APPLE_TEAM_ID` — 10-character Apple Team ID

---

## Directory structure

```
packaging/
├── miguel_angel.spec       ← PyInstaller build specification
├── BUILD.md                ← This file
├── hooks/
│   ├── hook-chromadb.py    ← chromadb PyInstaller hook
│   └── hook-ezdxf.py       ← ezdxf PyInstaller hook
├── scripts/
│   ├── build_deb.sh        ← Linux .deb builder
│   ├── notarise_mac.sh     ← macOS signing + notarisation
│   └── entitlements.plist  ← macOS Gatekeeper entitlements
└── icons/                  ← Application icons (add before first release)
    ├── miguel_angel.ico    ← Windows (multi-res ICO)
    ├── miguel_angel.icns   ← macOS (ICNS format)
    └── miguel_angel.png    ← Linux (256×256 PNG)
```

---

## Bundle size estimates

| Platform | Estimated size |
|----------|---------------|
| Windows (folder) | ~120 MB |
| Windows (single .exe) | ~80 MB (compressed) |
| macOS .dmg | ~100 MB |
| Linux .deb | ~90 MB |

The bundle includes: Python runtime, PyQt6, SQLite, all dependencies.
**Not included:** Ollama, torch, sentence-transformers (downloaded separately by user).
