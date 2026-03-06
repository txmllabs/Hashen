#!/usr/bin/env python3
"""Verify evidence bundle. Wrapper for hashen.cli.verify (use hashen-verify after install)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hashen.cli.verify import main

if __name__ == "__main__":
    sys.exit(main())
