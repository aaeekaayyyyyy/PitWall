# F1 Strategy Intelligence

Foundational scaffolding for the F1 2026 Race Strategy Intelligence Platform.

## Week 1 Scope

- Project folder structure
- Local Python virtual environment
- Dependency management
- Environment-based configuration handling

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

### Ingest a weekend session

After tables exist, run the Prefect flow to fetch one session (circuit, session, laps, weather) and run quality checks:

```bash
python run_ingest.py 2024 1 R
```

Or from Python:

```python
from f1_strategy.pipelines import ingest_weekend_session
ingest_weekend_session(year=2024, round=1, session_type="R")
```

Optional: set `OPENWEATHERMAP_API_KEY` in `.env` for weather; copy `data/circuits_seed.example.json` to `data/circuits_seed.json` to preload circuit metadata (e.g. lat/lon for weather).

### Data dictionary and env vars

See [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) for table schemas, ingestion env vars, and pipeline steps.
