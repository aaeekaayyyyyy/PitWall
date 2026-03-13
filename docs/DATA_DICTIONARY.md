# Data dictionary & ingestion

**Week 1** is complete: full weekend ingest (FP1, FP2, FP3, Q, R), quality checks, manual and optional scheduled run, and the schema below (including `telemetry_snapshots`).

## Database tables

### `circuits`
| Column           | Type      | Description                                |
|------------------|-----------|--------------------------------------------|
| id               | SERIAL PK | Auto-increment id.                         |
| name             | VARCHAR   | Circuit name (e.g. Melbourne, Monza).      |
| country          | VARCHAR   | Country.                                   |
| location         | VARCHAR   | Location string (nullable).                |
| track_length_m   | FLOAT     | Track length in metres (nullable).         |
| corner_count     | INTEGER   | Number of corners (nullable).              |
| latitude         | FLOAT     | Latitude for weather (nullable).           |
| longitude        | FLOAT     | Longitude for weather (nullable).          |
| created_at       | TIMESTAMPTZ | Row creation time.                       |

### `sessions`
| Column       | Type      | Description                                  |
|--------------|-----------|----------------------------------------------|
| id           | SERIAL PK | Auto-increment id.                           |
| circuit_id   | INTEGER FK| References `circuits.id`.                    |
| season       | INTEGER   | Year (e.g. 2024).                            |
| round        | INTEGER   | Round number (1–24).                         |
| session_type | VARCHAR   | FP1, FP2, FP3, Q, R, Sprint, Sprint Qualifying. |
| session_date | DATE      | Date of the session.                         |
| created_at   | TIMESTAMPTZ | Row creation time.                         |

### `laps`
| Column        | Type      | Description                          |
|---------------|-----------|--------------------------------------|
| id            | SERIAL PK | Auto-increment id.                   |
| session_id    | INTEGER FK| References `sessions.id`.            |
| driver_number | INTEGER   | F1 driver number.                    |
| driver        | VARCHAR   | Driver identifier/name.              |
| lap_number    | INTEGER   | Lap index.                           |
| lap_time_sec  | FLOAT     | Lap time in seconds (nullable).      |
| sector1_sec   | FLOAT     | Sector 1 time in seconds (nullable). |
| sector2_sec   | FLOAT     | Sector 2 time in seconds (nullable). |
| sector3_sec   | FLOAT     | Sector 3 time in seconds (nullable). |
| compound      | VARCHAR   | Tyre compound: SOFT, MEDIUM, HARD (nullable). |
| tyre_age      | INTEGER   | Tyre life / laps on set (nullable).  |
| pit           | BOOLEAN   | True if pit-in or pit-out on this lap. |
| created_at    | TIMESTAMPTZ | Row creation time.                 |

### `weather`
| Column           | Type      | Description                    |
|------------------|-----------|--------------------------------|
| id               | SERIAL PK | Auto-increment id.             |
| session_id       | INTEGER FK| References `sessions.id`.     |
| timestamp_utc    | TIMESTAMPTZ | Time of reading.            |
| air_temp_c       | FLOAT     | Air temperature °C (nullable). |
| track_temp_c     | FLOAT     | Track temperature °C (nullable). |
| humidity_pct     | FLOAT     | Humidity % (nullable).        |
| wind_speed_kmh   | FLOAT     | Wind speed km/h (nullable).    |
| wind_direction_deg | FLOAT   | Wind direction degrees (nullable). |
| rainfall         | BOOLEAN   | True if rain/snow reported.    |
| created_at       | TIMESTAMPTZ | Row creation time.          |

### `results`
| Column        | Type      | Description                    |
|---------------|-----------|--------------------------------|
| id            | SERIAL PK | Auto-increment id.             |
| session_id    | INTEGER FK| References `sessions.id`.     |
| driver_number | INTEGER   | F1 driver number.              |
| driver        | VARCHAR   | Driver identifier/name.       |
| position      | INTEGER   | Finishing position.            |
| points        | NUMERIC   | Points awarded (nullable).     |
| status        | VARCHAR   | e.g. Finished, +1 Lap (nullable). |
| created_at    | TIMESTAMPTZ | Row creation time.          |

### `telemetry_snapshots`
| Column         | Type      | Description                              |
|----------------|-----------|------------------------------------------|
| id             | SERIAL PK | Auto-increment id.                       |
| session_id     | INTEGER FK| References `sessions.id`.               |
| driver_number  | INTEGER   | F1 driver number.                        |
| lap_number     | INTEGER   | Lap index.                               |
| timestamp_utc   | TIMESTAMPTZ | Sample time.                          |
| sample_key     | VARCHAR   | Optional key (e.g. sector, corner).      |
| payload_json   | TEXT      | Optional JSON blob of sampled telemetry. |
| created_at     | TIMESTAMPTZ | Row creation time.                    |

---

## Environment variables (ingestion)

| Variable                 | Description                                      | Required |
|--------------------------|--------------------------------------------------|----------|
| POSTGRES_HOST            | PostgreSQL host.                                 | Yes      |
| POSTGRES_PORT            | PostgreSQL port (default 5432).                  | No       |
| POSTGRES_DB              | Database name.                                  | Yes      |
| POSTGRES_USER            | Database user.                                  | Yes      |
| POSTGRES_PASSWORD        | Database password.                              | Yes      |
| FASTF1_CACHE_DIR         | Directory for FastF1 cache (default `data/raw/fastf1_cache`). | No |
| OPENF1_BASE_URL         | OpenF1 API base URL (default https://api.openf1.org/v1). | No |
| OPENWEATHERMAP_API_KEY  | OpenWeatherMap API key for weather ingestion.   | No (weather skipped if unset) |

---

## Ingestion flow

1. **Circuit metadata**  
   Loaded from FastF1 when fetching a session (event location/country), or from a seed JSON (e.g. `data/circuits_seed.json`) with columns: `name`, `country`, and optionally `location`, `track_length_m`, `corner_count`, `latitude`, `longitude`.

2. **Session + laps**  
   FastF1: `get_session(year, round, session_type)` then `session.load()`; laps are normalized (LapTime/Sector times in seconds, Pit from PitInTime/PitOutTime) and inserted into `sessions` and `laps`. Re-running deletes existing laps for that session and re-inserts.

3. **Weather**  
   OpenWeatherMap is called for the circuit’s lat/lon and session date; one row per session is written to `weather`. Skipped if `OPENWEATHERMAP_API_KEY` is unset or circuit has no coordinates.

4. **Quality checks**  
   After ingest, checks run for: missing/duplicate lap numbers, null lap times, outlier laps (pit or &gt;1.5× median lap time), and wet-session flag from `weather.rainfall`. Results are logged as warnings and returned in the flow result; the run does not fail.

---

## Running the pipeline

- **Full weekend (all session types):**  
  `python run_ingest.py 2026 1`  
  Or: `ingest_full_weekend(year=2026, round=1)` from `f1_strategy.pipelines`.

- **Single session:**  
  `python run_ingest.py 2026 1 R`  
  Or: `ingest_weekend_session(year=2026, round=1, session_type="R")`.

- **Scheduled run (optional):**  
  Use `prefect deploy` (see `prefect.yaml`) and run a Prefect worker. Deployment `scheduled-weekend-ingest` runs on a cron (e.g. every 6 hours). Ensure Postgres and `.env` are set.

- **One-off session + laps:**  
  Use `fetch_and_insert_session(db, year, round, session_type)` from `f1_strategy.ingestion`.

- **Circuit seed:**  
  `load_circuits_from_seed(db, Path("data/circuits_seed.json"))` from `f1_strategy.ingestion.circuits`.
