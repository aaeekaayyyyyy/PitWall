"""Prefect flow: fetch session + laps, circuit metadata, weather, then run quality checks."""

from __future__ import annotations

import logging
from typing import Any

from prefect import flow
from prefect.task_runners import ConcurrentTaskRunner

from f1_strategy.db import get_session
from f1_strategy.ingestion.fastf1_session import fetch_and_insert_session
from f1_strategy.ingestion.weather import fetch_weather_for_session
from f1_strategy.quality.checks import run_quality_checks

logger = logging.getLogger(__name__)

# Session types to ingest for a full weekend (Sprint / Sprint Qualifying only on some rounds)
DEFAULT_SESSION_TYPES = ("FP1", "FP2", "FP3", "Q", "R")
ALL_SESSION_TYPES = ("FP1", "FP2", "FP3", "Q", "Sprint Qualifying", "Sprint", "R")


@flow(name="ingest-weekend-session", task_runner=ConcurrentTaskRunner())
def ingest_weekend_session(
    year: int,
    round: int,
    session_type: str = "R",
) -> dict[str, Any]:
    """
    Single Prefect flow: load circuit (via FastF1), fetch session and laps,
    fetch weather for the session, run quality checks. Can be triggered manually.
    """
    with get_session() as db:
        db_session = fetch_and_insert_session(db, year, round, session_type)
        if db_session is None:
            return {"ok": False, "session_id": None, "message": "Failed to fetch/insert session."}
        session_id = db_session.id
        fetch_weather_for_session(db, db_session)
        report = run_quality_checks(db, session_id)
    return {
        "ok": True,
        "session_id": session_id,
        "year": year,
        "round": round,
        "session_type": session_type,
        "warnings": report.warnings,
        "null_lap_times": report.null_lap_times,
        "outlier_laps": report.outlier_laps,
        "wet_session": report.wet_session,
    }


@flow(name="ingest-full-weekend", task_runner=ConcurrentTaskRunner())
def ingest_full_weekend(
    year: int,
    round: int,
    session_types: tuple[str, ...] = DEFAULT_SESSION_TYPES,
) -> dict[str, Any]:
    """
    Ingest all session types for a given year and round (FP1, FP2, FP3, Q, R by default).
    Runs fetch + weather + quality for each session type in sequence.
    """
    results: list[dict[str, Any]] = []
    with get_session() as db:
        for st in session_types:
            db_session = fetch_and_insert_session(db, year, round, st)
            if db_session is None:
                results.append({"session_type": st, "ok": False, "message": "No data or load failed."})
                continue
            fetch_weather_for_session(db, db_session)
            report = run_quality_checks(db, db_session.id)
            results.append({
                "session_type": st,
                "ok": True,
                "session_id": db_session.id,
                "warnings_count": len(report.warnings),
                "null_lap_times": report.null_lap_times,
                "outlier_laps": report.outlier_laps,
                "wet_session": report.wet_session,
            })
    return {"year": year, "round": round, "results": results}


@flow(name="scheduled-ingest-weekend", task_runner=ConcurrentTaskRunner())
def scheduled_ingest_weekend(
    year: int = 2026,
    round: int = 1,
) -> dict[str, Any]:
    """
    Entrypoint for scheduled runs (e.g. cron). Runs ingest_full_weekend for the given
    year/round. When deploying with a schedule, set default parameters or use a
    calendar lookup for "last completed weekend".
    """
    return ingest_full_weekend(year=year, round=round)
