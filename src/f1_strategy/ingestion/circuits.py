"""Circuit metadata: load from FastF1 or seed JSON and upsert into DB."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import fastf1
from sqlalchemy.orm import Session

from f1_strategy.config import get_settings
from f1_strategy.db.models import Circuit

logger = logging.getLogger(__name__)


def _ensure_cache_dir() -> None:
    settings = get_settings()
    settings.fastf1_cache_dir.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(settings.fastf1_cache_dir))


def circuit_from_event(event: Any) -> dict[str, Any]:
    """Build circuit row dict from FastF1 Event object."""
    loc = getattr(event, "Location", None) or ""
    return {
        "name": getattr(event, "Location", None) or getattr(event, "EventName", "Unknown"),
        "country": getattr(event, "Country", "") or "",
        "location": loc if isinstance(loc, str) else str(loc),
        "track_length_m": None,
        "corner_count": None,
        "latitude": getattr(event, "Latitude", None),
        "longitude": getattr(event, "Longitude", None),
    }


def upsert_circuit_from_event(db: Session, event: Any) -> Circuit:
    """Create or get circuit from FastF1 event; return the Circuit model."""
    data = circuit_from_event(event)
    name = data["name"]
    country = data["country"]
    existing = db.query(Circuit).filter(Circuit.name == name, Circuit.country == country).first()
    if existing:
        for k, v in data.items():
            if v is not None and hasattr(existing, k):
                setattr(existing, k, v)
        db.flush()
        return existing
    circuit = Circuit(**data)
    db.add(circuit)
    db.flush()
    return circuit


def load_circuit_for_session(db: Session, year: int, round: int) -> Circuit | None:
    """Load FastF1 event for the weekend, upsert circuit, return it. Sets cache dir from settings."""
    _ensure_cache_dir()
    try:
        session = fastf1.get_session(year, round, "FP1")
        session.load()
        event = session.event
        if event is None:
            logger.warning("No event for %s R%s", year, round)
            return None
        return upsert_circuit_from_event(db, event)
    except Exception as e:
        logger.exception("Failed to load circuit for %s R%s: %s", year, round, e)
        return None


def load_circuits_from_seed(db: Session, path: Path | str) -> int:
    """
    Load circuits from a JSON file (array of objects with name, country, and optional
    location, track_length_m, corner_count, latitude, longitude). Upserts by (name, country).
    Returns number of circuits inserted or updated.
    """
    path = Path(path)
    if not path.exists():
        logger.warning("Seed file not found: %s", path)
        return 0
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        data = [data]
    count = 0
    for row in data:
        name = row.get("name") or row.get("circuit_name")
        country = row.get("country", "")
        if not name:
            continue
        existing = db.query(Circuit).filter(Circuit.name == name, Circuit.country == country).first()
        if existing:
            for k in ("location", "track_length_m", "corner_count", "latitude", "longitude"):
                if k in row and row[k] is not None:
                    setattr(existing, k, row[k])
            count += 1
        else:
            circuit = Circuit(
                name=name,
                country=country,
                location=row.get("location"),
                track_length_m=row.get("track_length_m"),
                corner_count=row.get("corner_count"),
                latitude=row.get("latitude"),
                longitude=row.get("longitude"),
            )
            db.add(circuit)
            count += 1
    db.flush()
    logger.info("Loaded %s circuits from seed %s.", count, path)
    return count
