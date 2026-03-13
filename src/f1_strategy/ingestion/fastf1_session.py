"""FastF1 session and laps: fetch for a weekend/session, normalize, insert into DB."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import fastf1
import pandas as pd
from sqlalchemy.orm import Session

from f1_strategy.config import get_settings
from sqlalchemy import delete
from f1_strategy.db.models import Lap, Session as DBSession
from f1_strategy.ingestion.circuits import load_circuit_for_session

logger = logging.getLogger(__name__)

SESSION_TYPE_MAP = {"Practice 1": "FP1", "Practice 2": "FP2", "Practice 3": "FP3", "Qualifying": "Q", "Race": "R", "Sprint": "Sprint", "Sprint Qualifying": "Sprint Qualifying"}


def _ensure_cache_dir() -> None:
    settings = get_settings()
    settings.fastf1_cache_dir.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(settings.fastf1_cache_dir))


def _session_type_name(f1_session: Any) -> str:
    name = getattr(f1_session, "session_name", None) or ""
    return SESSION_TYPE_MAP.get(name, name) or "FP1"


def _lap_time_seconds(val: Any) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if hasattr(val, "total_seconds"):
        return val.total_seconds()
    if isinstance(val, (int, float)):
        return float(val)
    return None


def fetch_and_insert_session(
    db: Session,
    year: int,
    round: int,
    session_type: str = "R",
) -> DBSession | None:
    """
    Load FastF1 session for the given weekend and session type; ensure circuit exists,
    insert session and laps into DB. Returns the created/updated DBSession or None on failure.
    """
    _ensure_cache_dir()
    circuit = load_circuit_for_session(db, year, round)
    if circuit is None:
        logger.warning("No circuit for %s R%s; cannot insert session.", year, round)
        return None

    try:
        f1_session = fastf1.get_session(year, round, session_type)
        f1_session.load()
    except Exception as e:
        logger.exception("FastF1 load failed for %s R%s %s: %s", year, round, session_type, e)
        return None

    session_date = getattr(f1_session, "date", None) or getattr(getattr(f1_session, "event", None), "EventDate", None)
    if session_date is None:
        logger.warning("No session date for %s R%s %s", year, round, session_type)
        return None
    if hasattr(session_date, "date"):
        session_date = session_date.date()
    if not isinstance(session_date, date):
        session_date = date(session_date.year, session_date.month, session_date.day)

    # Use caller-provided session_type for DB so each session type gets its own record.
    # (FastF1 session_name can be missing or inconsistent; do not use _session_type_name for lookup.)
    db_session_type = session_type
    existing = (
        db.query(DBSession)
        .filter(
            DBSession.circuit_id == circuit.id,
            DBSession.season == year,
            DBSession.round == round,
            DBSession.session_type == db_session_type,
        )
        .first()
    )
    if existing:
        db_session = existing
        db.execute(delete(Lap).where(Lap.session_id == db_session.id))
        db.flush()
    else:
        db_session = DBSession(
            circuit_id=circuit.id,
            season=year,
            round=round,
            session_type=db_session_type,
            session_date=session_date,
        )
        db.add(db_session)
        db.flush()

    laps_df = f1_session.laps
    if laps_df is None or laps_df.empty:
        logger.info("No laps for %s R%s %s", year, round, session_type)
        return db_session

    for _, row in laps_df.iterrows():
        driver_number = int(row.get("DriverNumber", row.get("Driver", 0)) or 0)
        driver_str = str(row.get("Driver", driver_number))[:128]
        lap_number = int(row.get("LapNumber", 0) or 0)
        compound = row.get("Compound")
        compound = str(compound).upper() if compound is not None and pd.notna(compound) else None
        tyre_age = row.get("TyreLife")
        tyre_age = int(tyre_age) if tyre_age is not None and pd.notna(tyre_age) else None
        pit_in = row.get("PitInTime")
        pit_out = row.get("PitOutTime")
        pit = (pit_in is not None and pd.notna(pit_in)) or (pit_out is not None and pd.notna(pit_out))
        lap = Lap(
            session_id=db_session.id,
            driver_number=driver_number,
            driver=driver_str[:128],
            lap_number=lap_number,
            lap_time_sec=_lap_time_seconds(row.get("LapTime")),
            sector1_sec=_lap_time_seconds(row.get("Sector1Time")),
            sector2_sec=_lap_time_seconds(row.get("Sector2Time")),
            sector3_sec=_lap_time_seconds(row.get("Sector3Time")),
            compound=compound,
            tyre_age=tyre_age,
            pit=pit,
        )
        db.add(lap)
    db.flush()
    logger.info("Inserted session %s R%s %s with %s laps.", year, round, session_type, len(laps_df))
    return db_session
