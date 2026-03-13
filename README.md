# F1 Strategy Intelligence

Foundational scaffolding for the F1 2026 Race Strategy Intelligence Platform.

## Week 1 (complete)

- Project structure, Python env, dependency management, config (.env)
- PostgreSQL schema: circuits, sessions, laps, weather, results, telemetry_snapshots
- Data ingestion: FastF1 session + laps, circuit metadata (FastF1 + seed JSON), weather (OpenWeatherMap)
- Full weekend ingest: FP1, FP2, FP3, Q, R (and optional Sprint) for a given year + round
- Data quality checks (missing/duplicate lap numbers, null lap times, outliers, wet-session flag)
- Prefect flows: single-session and full-weekend; optional scheduled run (cron)
- Data dictionary and ingestion env vars documented

## Quick Start

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and set `POSTGRES_*` (and optionally `OPENWEATHERMAP_API_KEY`).

### PostgreSQL setup (macOS)

PostgreSQL is required. Install and start it, then create the database and user:

```bash
# Install PostgreSQL (Homebrew)
brew install postgresql@16
brew services start postgresql@16

# Add Postgres tools to PATH (use the path Homebrew prints after install)
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"   # Apple Silicon
# export PATH="/usr/local/opt/postgresql@16/bin:$PATH"    # Intel

# Create user and database (match POSTGRES_USER and POSTGRES_DB in .env)
createuser -s f1_user
createdb -O f1_user f1_strategy

# Set a password for f1_user (replace YOUR_PASSWORD with your choice)
psql -U f1_user -d f1_strategy -c "ALTER USER f1_user WITH PASSWORD 'YOUR_PASSWORD';"
```

Put the same password in `.env` as `POSTGRES_PASSWORD=YOUR_PASSWORD`.

### Create tables

From project root with the venv activated:

```bash
# From project root (with venv activated). If you get "No module named 'f1_strategy'", run the script instead:
python run_init_db.py
```

Or install the package in editable mode first, then use the module:

```bash
pip install -e .
python -m f1_strategy.db.init_db
```

### Load circuit seed (for weather)

Weather needs circuit latitude/longitude. Preload circuits from the example seed so ingest can fetch weather:

```bash
cp data/circuits_seed.example.json data/circuits_seed.json
python run_seed_circuits.py
```

Or pass a path: `python run_seed_circuits.py data/circuits_seed.json`. Run this once (or when you add circuits); the ingest flow will reuse existing circuits and keep their lat/lon.

### Ingest a weekend

After tables exist (and optionally after loading the circuit seed):

**Full weekend (all session types: FP1, FP2, FP3, Q, R):**

```bash
python run_ingest.py 2026 1
```

**Single session (e.g. Race only):**

```bash
python run_ingest.py 2026 1 R
```

Or from Python:

```python
from f1_strategy.pipelines import ingest_full_weekend, ingest_weekend_session
ingest_full_weekend(year=2026, round=1)
ingest_weekend_session(year=2026, round=1, session_type="R")
```

Set `OPENWEATHERMAP_API_KEY` in `.env` for weather. Load the circuit seed (see above) so circuits have lat/lon.

### Scheduled run (optional)

To run ingest automatically (e.g. every 6 hours during the season), use Prefect with a schedule. Ensure Postgres is running and `.env` is set.

1. From project root with venv activated and package on path (`pip install -e .` or `PYTHONPATH=src`): `prefect deploy` (uses `prefect.yaml`; edit `parameters.year` and `parameters.round` per race calendar).
2. Start a worker: `prefect worker start` (or run a Prefect server and register the deployment).
3. The deployment `scheduled-weekend-ingest` runs `scheduled_ingest_weekend` on the cron in `prefect.yaml`. Update the cron or parameters as needed.

### Data dictionary and env vars

See [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) for table schemas, ingestion env vars, and pipeline steps.
