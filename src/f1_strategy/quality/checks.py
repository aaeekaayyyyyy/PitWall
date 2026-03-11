"""Data quality checks: missing lap numbers, null lap times, outliers, wet-session flags."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from f1_strategy.db.models import Lap, Session as DBSession, Weather

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Result of quality checks: list of warnings and optional summary counts."""

    session_id: int
    warnings: list[str] = field(default_factory=list)
    missing_lap_numbers: int = 0
    null_lap_times: int = 0
    outlier_laps: int = 0
    wet_session: bool = False

    def log_and_return(self) -> QualityReport:
        for w in self.warnings:
            logger.warning("[session_id=%s] %s", self.session_id, w)
        return self


def _is_outlier_lap(lap: Lap, median_lap_time_sec: float | None) -> bool:
    """Consider lap an outlier if pit, or lap_time far from median (e.g. VSC/red flag/slow)."""
    if lap.pit:
        return True
    if median_lap_time_sec is None or lap.lap_time_sec is None:
        return False
    if lap.lap_time_sec <= 0:
        return True
    if lap.lap_time_sec > median_lap_time_sec * 1.5:
        return True
    return False


def run_quality_checks(db: Session, session_id: int) -> QualityReport:
    """
    Run quality checks for the given session: missing lap numbers, null lap times,
    outlier laps (pit, very slow), and wet-session flag. Emits warnings and returns
    a report; does not fail the run.
    """
    report = QualityReport(session_id=session_id)
    result = db.execute(select(Lap).where(Lap.session_id == session_id).order_by(Lap.driver_number, Lap.lap_number))
    laps = [row[0] for row in result.all()]
    if not laps:
        report.warnings.append("No laps found for session.")
        return report.log_and_return()

    seen_driver_lap: set[tuple[int, int]] = set()
    null_lt = 0
    lap_times = []
    for lap in laps:
        key = (lap.driver_number, lap.lap_number)
        if key in seen_driver_lap:
            report.warnings.append(f"Duplicate lap (driver={lap.driver_number}, lap={lap.lap_number}).")
        seen_driver_lap.add(key)
        if lap.lap_time_sec is None:
            null_lt += 1
        elif lap.lap_time_sec > 0:
            lap_times.append(lap.lap_time_sec)

    report.null_lap_times = null_lt
    if null_lt:
        report.warnings.append(f"Laps with null lap time: {null_lt}.")

    import statistics
    median_lt = statistics.median(lap_times) if lap_times else None
    outlier_count = 0
    for lap in laps:
        if _is_outlier_lap(lap, median_lt):
            outlier_count += 1
    report.outlier_laps = outlier_count
    if outlier_count:
        report.warnings.append(f"Outlier laps (pit or >1.5x median): {outlier_count}.")

    w_row = db.execute(select(Weather).where(Weather.session_id == session_id)).first()
    weather = w_row[0] if w_row else None
    report.wet_session = getattr(weather, "rainfall", False) if weather else False
    if report.wet_session:
        report.warnings.append("Session flagged as wet (rainfall=True).")

    return report.log_and_return()
