#!/usr/bin/env python3
"""Produce evidence bundle. Wrapper for hashen.cli.bundle (use hashen-bundle after install)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hashen.cli.bundle import main

if __name__ == "__main__":
    sys.exit(main())
