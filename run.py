"""
miguel_angel — Standalone run script
Use this as the PyInstaller entry point if __main__.py has path issues.

Usage:
  python run.py
  pyinstaller --onedir --name miguel_angel run.py
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

from miguel_angel.__main__ import main
sys.exit(main())
