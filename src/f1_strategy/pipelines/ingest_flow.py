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
