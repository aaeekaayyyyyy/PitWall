#!/usr/bin/env python3
"""Run the weekend ingest flow.
  Full weekend (all session types):  python run_ingest.py YEAR ROUND
  Single session:                   python run_ingest.py YEAR ROUND SESSION_TYPE
Example: python run_ingest.py 2026 1
         python run_ingest.py 2026 1 R
"""

import sys
from pathlib import Path

# Ensure src is on path when run as script
_root = Path(__file__).resolve().parent
_src = _root / "src"
if _src.exists() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from f1_strategy.pipelines import ingest_full_weekend, ingest_weekend_session

if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    round_num = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    if len(sys.argv) > 3:
        session_type = (sys.argv[3].strip().upper() or "R")
        if session_type == "RACE":
            session_type = "R"
        result = ingest_weekend_session(year=year, round=round_num, session_type=session_type)
    else:
        result = ingest_full_weekend(year=year, round=round_num)
    print("Result:", result)
