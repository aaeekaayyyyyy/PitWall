"""Weather: fetch from OpenWeatherMap for session time/place and insert into DB."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests
from sqlalchemy.orm import Session

from f1_strategy.config import get_settings
from f1_strategy.db.models import Circuit, Session as DBSession, Weather

logger = logging.getLogger(__name__)


def fetch_weather_for_session(
    db: Session,
    db_session: DBSession,
) -> int:
    """
    Fetch weather at circuit location for the session date and insert into weather table.
    Uses OpenWeatherMap; requires OPENWEATHERMAP_API_KEY in settings.
    Returns number of weather rows inserted (0 or 1).
    """
    settings = get_settings()
    if not settings.openweathermap_api_key:
        logger.warning("OPENWEATHERMAP_API_KEY not set; skipping weather fetch.")
        return 0

    circuit = db_session.circuit
    if circuit is None:
        circuit = db.query(Circuit).filter(Circuit.id == db_session.circuit_id).first()
    if circuit is None or (circuit.latitude is None and circuit.longitude is None):
        logger.warning("Circuit has no lat/lon; cannot fetch weather for session %s.", db_session.id)
        return 0

    lat = circuit.latitude or 0.0
    lon = circuit.longitude or 0.0
    session_date = db_session.session_date
    dt = datetime(session_date.year, session_date.month, session_date.day, 14, 0, 0, tzinfo=timezone.utc)
    ts = int(dt.timestamp())

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": settings.openweathermap_api_key, "units": "metric"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.exception("OpenWeatherMap request failed: %s", e)
        return 0

    main = data.get("main", {})
    wind = data.get("wind", {})
    rain = data.get("rain") or data.get("snow")
    air_temp = main.get("temp")
    humidity = main.get("humidity")
    wind_speed_ms = wind.get("speed")
    wind_deg = wind.get("deg")
    wind_speed_kmh = (wind_speed_ms * 3.6) if wind_speed_ms is not None else None

    existing = db.query(Weather).filter(
        Weather.session_id == db_session.id,
        Weather.timestamp_utc == dt,
    ).first()
    if existing:
        existing.air_temp_c = air_temp
        existing.track_temp_c = None
        existing.humidity_pct = humidity
        existing.wind_speed_kmh = wind_speed_kmh
        existing.wind_direction_deg = wind_deg
        existing.rainfall = bool(rain)
        db.flush()
        return 0

    row = Weather(
        session_id=db_session.id,
        timestamp_utc=dt,
        air_temp_c=air_temp,
        track_temp_c=None,
        humidity_pct=humidity,
        wind_speed_kmh=wind_speed_kmh,
        wind_direction_deg=wind_deg,
        rainfall=bool(rain),
    )
    db.add(row)
    db.flush()
    logger.info("Inserted weather for session %s.", db_session.id)
    return 1
