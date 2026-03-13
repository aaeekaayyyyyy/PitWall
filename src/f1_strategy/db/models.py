"""SQLAlchemy models for Week 1 core tables."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all models."""

    pass


class SessionType(str, PyEnum):
    """F1 session type."""

    FP1 = "FP1"
    FP2 = "FP2"
    FP3 = "FP3"
    Q = "Q"
    R = "R"
    Sprint = "Sprint"
    Sprint_Qualifying = "Sprint Qualifying"


class Circuit(Base):
    """Circuit metadata (track, location, geometry)."""

    __tablename__ = "circuits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    track_length_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    corner_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="circuit")


class Session(Base):
    """Race weekend session (practice, qualifying, race)."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    circuit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("circuits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    round: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    session_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # FP1, FP2, Q, R, etc.
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    circuit: Mapped["Circuit"] = relationship("Circuit", back_populates="sessions")
    laps: Mapped[list["Lap"]] = relationship("Lap", back_populates="session")
    weather: Mapped[list["Weather"]] = relationship("Weather", back_populates="session")
    results: Mapped[list["Result"]] = relationship("Result", back_populates="session")
    telemetry_snapshots: Mapped[list["TelemetrySnapshot"]] = relationship(
        "TelemetrySnapshot", back_populates="session"
    )


class Lap(Base):
    """Per-lap timing and tyre data."""

    __tablename__ = "laps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    driver_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    driver: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    lap_time_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    sector1_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    sector2_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    sector3_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    compound: Mapped[str | None] = mapped_column(String(16), nullable=True)  # SOFT, MEDIUM, HARD
    tyre_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="laps")


class Weather(Base):
    """Weather readings for a session (matched to session timestamps)."""

    __tablename__ = "weather"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    air_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    track_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_direction_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="weather")


class Result(Base):
    """Session result (position, points, status)."""

    __tablename__ = "results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    driver_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    driver: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    points: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Finished, +1 Lap, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="results")


class TelemetrySnapshot(Base):
    """Sampled telemetry for a lap (session_id, driver, lap, timestamp + optional blob)."""

    __tablename__ = "telemetry_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    driver_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    sample_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="telemetry_snapshots")
