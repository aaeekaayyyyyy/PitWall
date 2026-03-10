#!/usr/bin/env python3
"""Create database tables. Run from project root: python run_init_db.py"""

import sys
from pathlib import Path

# Add src so "f1_strategy" is importable when package isn't installed (e.g. pip install -e . not run)
_root = Path(__file__).resolve().parent
_src = _root / "src"
if _src.exists() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from f1_strategy.db import create_tables

if __name__ == "__main__":
    create_tables()
    print("Tables created successfully.")
