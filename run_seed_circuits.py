#!/usr/bin/env python3
"""Load circuit metadata from a JSON seed file. Run from project root: python run_seed_circuits.py [path]"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
_src = _root / "src"
if _src.exists() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from f1_strategy.db import get_session
from f1_strategy.ingestion.circuits import load_circuits_from_seed

if __name__ == "__main__":
    default_path = _root / "data" / "circuits_seed.json"
    path = default_path
    if len(sys.argv) > 1:
        path = Path(sys.argv[1]).resolve()
    if not path.exists():
        print(f"Seed file not found: {path}")
        if path != default_path:
            print(f"To use the default: python run_seed_circuits.py  (or python run_seed_circuits.py data/circuits_seed.json)")
        print("Copy data/circuits_seed.example.json to data/circuits_seed.json and edit as needed.")
        sys.exit(1)
    with get_session() as db:
        count = load_circuits_from_seed(db, path)
    print(f"Loaded {count} circuit(s) from {path}.")
