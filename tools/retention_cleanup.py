#!/usr/bin/env python3
"""Retention cleanup. Wrapper for hashen.cli.retention (use hashen-retention after install)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hashen.cli.retention import main

if __name__ == "__main__":
    sys.exit(main())
