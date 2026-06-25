# -*- mode: python ; coding: utf-8 -*-
"""
miguel_angel — PyInstaller Build Specification
Cloud Specialist implementation · Phase 4

Produces a single-directory bundle for all platforms:
  Windows  → dist/miguel_angel/miguel_angel.exe
  macOS    → dist/miguel_angel.app
  Linux    → dist/miguel_angel/miguel_angel  (then .deb via packaging/scripts/)

Usage:
  pyinstaller packaging/miguel_angel.spec

Options controlled via environment variables:
  MA_ONE_FILE=1      → produce a single .exe/.bin instead of a folder
  MA_CONSOLE=1       → show a terminal window (debugging)
  MA_VERSION=x.y.z   → embedded version string

Notes:
  - PyInstaller does NOT cross-compile: run on Windows to get .exe,
    on macOS to get .app, on Linux to get the Linux binary.
  - chromadb's ONNX runtime is excluded (heavy, optional): MiguelBot
    falls back to TF-IDF when ONNX is absent in the bundle.
  - Qt plugins are collected automatically by PyInstaller via PyQt6 hooks.
"""

import os
import sys
from pathlib import Path

# ── Configuration from environment ───────────────────────────────────────────
ONE_FILE     = os.environ.get("MA_ONE_FILE", "0") == "1"
SHOW_CONSOLE = os.environ.get("MA_CONSOLE",  "0") == "1"
VERSION      = os.environ.get("MA_VERSION",  "0.1.0")
ICON_WIN     = "packaging/icons/miguel_angel.ico"
ICON_MAC     = "packaging/icons/miguel_angel.icns"
ICON_LIN     = "packaging/icons/miguel_angel.png"

ROOT = Path(".").resolve()

# ── Hidden imports ────────────────────────────────────────────────────────────
# Packages imported dynamically or via string that PyInstaller can't trace
HIDDEN_IMPORTS = [
    # PyQt6 platform plugins loaded by name at runtime
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtPrintSupport",
    "PyQt6.sip",

    # SQLAlchemy dialects loaded by connection string
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.pool",

    # Pydantic v2 internals
    "pydantic.deprecated.class_validators",
    "pydantic_core",

    # networkx loaders
    "networkx.readwrite",
    "networkx.algorithms",

    # ezdxf entities registered by name
    "ezdxf.entities",
    "ezdxf.layouts",
    "ezdxf.sections",

    # reportlab fonts
    "reportlab.rl_settings",
    "reportlab.pdfbase.pdfmetrics",
    "reportlab.pdfbase._fontdata",

    # chromadb (optional — falls back gracefully if absent)
    "chromadb",
    "chromadb.db.impl.sqlite",

    # Alembic migration runner
    "alembic",
    "alembic.runtime.migration",

    # argon2 C extension
    "argon2._utils",

    # App packages
    "miguel_angel",
    "miguel_angel.auth",
    "miguel_angel.core",
    "miguel_angel.db",
    "miguel_angel.miguelbot",
    "miguel_angel.export",
    "miguel_angel.ui",
]

# ── Excluded modules ──────────────────────────────────────────────────────────
# Reduce bundle size by excluding heavy optional packages
EXCLUDES = [
    "matplotlib",
    "numpy",          # only needed by sentence-transformers (optional)
    "scipy",
    "pandas",
    "IPython",
    "jupyter",
    "pytest",
    "mypy",
    "ruff",
    "black",
    "torch",          # sentence-transformers heavy dep — use Ollama instead
    "torchvision",
    "torchaudio",
    "transformers",   # same — Ollama provides the model
    "onnxruntime",    # chromadb optional — excluded for bundle size
    "tensorflow",
    "jax",
    "tkinter",
    "wx",
]

# ── Data files ────────────────────────────────────────────────────────────────
# (source_pattern, destination_in_bundle)
DATAS = [
    ("docs/",          "docs"),            # MiguelBot ingests docs at startup
    ("README.md",      "."),
    ("LICENSE",        "."),
    ("CHANGELOG.md",   "."),
]

# Add Alembic migrations
DATAS.append(("miguel_angel/db/migrations/", "miguel_angel/db/migrations"))

# Add packaging metadata
DATAS.append(("packaging/", "packaging"))

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["miguel_angel/__main__.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=["packaging/hooks"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# ── PYZ archive ──────────────────────────────────────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# ── Platform-specific output ──────────────────────────────────────────────────
icon = (ICON_WIN if sys.platform == "win32"
        else ICON_MAC if sys.platform == "darwin"
        else ICON_LIN)

if ONE_FILE:
    # ── Single-file bundle ────────────────────────────────────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="miguel_angel",
        debug=SHOW_CONSOLE,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=SHOW_CONSOLE,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon if Path(icon).exists() else None,
        version_info=dict(
            FileVersion=VERSION,
            ProductVersion=VERSION,
            FileDescription="miguel_angel schematic editor",
            ProductName="miguel_angel",
            LegalCopyright="MIT License",
        ) if sys.platform == "win32" else None,
    )
else:
    # ── Directory bundle (default — faster startup) ───────────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="miguel_angel",
        debug=SHOW_CONSOLE,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        console=SHOW_CONSOLE,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon if Path(icon).exists() else None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="miguel_angel",
    )

    # ── macOS .app bundle ─────────────────────────────────────────────────────
    if sys.platform == "darwin":
        app = BUNDLE(
            coll,
            name="miguel_angel.app",
            icon=ICON_MAC if Path(ICON_MAC).exists() else None,
            bundle_identifier="com.ricrypto.miguel-angel",
            info_plist={
                "CFBundleName":                "miguel_angel",
                "CFBundleDisplayName":         "miguel_angel",
                "CFBundleIdentifier":          "com.ricrypto.miguel-angel",
                "CFBundleVersion":             VERSION,
                "CFBundleShortVersionString":  VERSION,
                "CFBundleExecutable":          "miguel_angel",
                "NSHighResolutionCapable":     True,
                "NSRequiresAquaSystemAppearance": False,   # dark mode support
                "LSMinimumSystemVersion":      "12.0",
                "CFBundleDocumentTypes": [{
                    "CFBundleTypeName":       "miguel_angel project",
                    "CFBundleTypeExtensions": ["maproj"],
                    "CFBundleTypeRole":       "Editor",
                    "LSHandlerRank":          "Owner",
                }],
            },
        )
