# ECB Exchange Rate Pipeline

Production-grade data engineering pipeline that ingests euro foreign exchange reference rates from the [European Central Bank (ECB) Open Data API](https://data-api.ecb.europa.eu/), stores them in a normalized PostgreSQL database, and exposes the data through a FastAPI REST API.

## Architecture

```mermaid
flowchart LR
    ECB[ECB Open Data API] --> Extract
    Extract --> Transform
    Transform --> Load
    Load --> PG[(PostgreSQL)]
    PG --> API[FastAPI REST API]
    Scheduler[Manual / Cron / POST ingest] --> Extract
```

See [docs/architecture.md](docs/architecture.md) for component details and error-handling strategy.

## Quick Start (Local — no Docker)

Best option when Docker Desktop is not available. Uses **SQLite** (file: `data/ecb_rates.db`).

```bash
cd ecb-exchange-rate-pipeline
cp .env.example .env
./scripts/run_local.sh
```

Or step by step:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export PYTHONPATH=.
python scripts/init_db.py
uvicorn app.main:app --reload --port 8000
```

Then ingest and query:

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"start_period":"2026-01-01","end_period":"2026-01-31"}'
```

## Quick Start (Docker)

```bash
cd ecb-exchange-rate-pipeline
cp .env.example .env
docker compose -f docker/docker-compose.yml up --build
```

Services:

- API: http://localhost:8000
- OpenAPI docs: http://localhost:8000/docs
- PostgreSQL: `localhost:5432`

Run an initial ingestion after the stack is healthy:

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"start_period":"2026-01-01","end_period":"2026-01-31"}'
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | Async SQLAlchemy URL (SQLite or `postgresql+asyncpg://...`) | see `.env.example` |
| `ECB_BASE_URL` | ECB EXR dataset base URL | ECB production URL |
| `ECB_REQUEST_TIMEOUT` | HTTP timeout in seconds | `30` |
| `ECB_RETRY_ATTEMPTS` | Retry count for 429/5xx | `3` |
| `DEFAULT_CURRENCIES` | Comma-separated ISO codes (empty = all) | empty |
| `LOG_LEVEL` | Python log level | `INFO` |
| `APP_ENV` | `development` \| `staging` \| `production` | `development` |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service and DB health |
| GET | `/api/v1/series` | List series (`?currency=USD&freq=D`) |
| GET | `/api/v1/series/{series_key}/observations` | Paginated observations |
| GET | `/api/v1/observations/latest` | Latest observation per series |
| POST | `/api/v1/ingest` | Trigger manual ingestion |
| GET | `/api/v1/ingestion-runs` | Recent ingestion audit runs |

Examples:

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/api/v1/series?currency=USD&freq=D"
curl "http://localhost:8000/api/v1/series/D.USD.EUR.SP00.A/observations?start=2026-01-01&end=2026-01-31"
curl "http://localhost:8000/api/v1/observations/latest?currency=USD"
curl http://localhost:8000/api/v1/ingestion-runs
```

Full reference: [docs/api_reference.md](docs/api_reference.md)

## Run Pipeline Manually

Using the CLI script:

```bash
pip install -e ".[dev]"
export DATABASE_URL=postgresql+asyncpg://ecb_user:ecb_password@localhost:5432/ecb_rates
python scripts/run_pipeline.py --start 2026-01-01 --end 2026-01-31
```

Historical backfill:

```bash
python scripts/backfill.py --start 2025-01-01 --end 2025-12-31 --chunk-days 31
```

Or trigger via API:

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"start_period":"2026-01-01","end_period":"2026-01-31"}'
```

## Run Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=app --cov=pipeline --cov-report=term-missing
```

With PostgreSQL (matches CI):

```bash
export DATABASE_URL=postgresql+asyncpg://ecb_user:ecb_password@localhost:5432/ecb_rates
alembic upgrade head
pytest tests/ -v
```

## Database Schema

Normalized 3NF schema with lookup tables (`frequency`, `currency`), series metadata (`exchange_rate_series`), observations (`exchange_rate_observation`), and ingestion audit logs (`ingestion_run`).

Details: [docs/database_schema.md](docs/database_schema.md)

**Before/after example for stakeholders:** [docs/data_transformation_example.md](docs/data_transformation_example.md) — raw ECB CSV vs normalised tables with side-by-side samples.

## Project Structure

```
app/          FastAPI application, ORM models, ECB client, ingestion service
pipeline/     Extract, transform, load modules
alembic/      Database migrations
tests/        Unit and integration tests
docker/       Dockerfile and docker-compose
docs/         Architecture, schema, API, runbook
scripts/      Manual pipeline, backfill, init_db, run_local.sh
```

## Contributing

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `chore:` tooling/build
- `test:` tests
- `refactor:` code restructuring

Before opening a PR:

```bash
ruff check .
mypy app/ pipeline/
pytest tests/ -v
```

Operational procedures: [docs/runbook.md](docs/runbook.md)

## License

MIT
