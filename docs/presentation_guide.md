# ECB Exchange Rate Pipeline
## Data Engineer Presentation & Demo Guide

**Author:** Jahangir | **GitHub:** https://github.com/silver1ce/ecb-exchange-rate-pipeline

---

## 30-Second Elevator Pitch

I built an end-to-end data pipeline that ingests euro foreign exchange reference rates from the European Central Bank (ECB) Open Data API, validates and normalizes them into a 3NF PostgreSQL schema, and exposes the data through a FastAPI REST API. The pipeline is idempotent (upserts, no duplicate observations), auditable (ingestion_run table), and production-oriented with Docker, Alembic migrations, automated tests (~88% coverage), and GitHub Actions CI.

---

## Pre-Demo Checklist

1. Start Docker Desktop
2. Clone: git clone https://github.com/silver1ce/ecb-exchange-rate-pipeline.git
3. cd ecb-exchange-rate-pipeline
4. cp .env.example .env
5. Pre-warm stack (optional, 5 min before):

   docker compose -f docker/docker-compose.yml up --build -d
   curl -s http://localhost:8000/health

6. Open browser tabs: GitHub repo, http://localhost:8000/docs, docs/architecture.md

---

## Architecture (What to Say — 2 min)

Data flow:

  ECB API (CSV) → Extract → Transform → Load → PostgreSQL → FastAPI REST API
                        ↑
              Ingestion orchestration + audit log

- Extract: Async httpx client; retries on HTTP 429 and 5xx; CSV parsing (skips # comment lines)
- Transform: pandas + Pydantic; handles ECB quirks ('.' = missing, YYYY-MM monthly dates)
- Load: Upserts into frequency, currency, series, observations (ON CONFLICT DO UPDATE)
- Serve: REST API for consumers; OpenAPI documentation at /docs

Key files:
- app/services/ecb_client.py — HTTP + retry + CSV
- pipeline/transform.py — Validation, skip bad rows
- pipeline/load.py — Upsert pattern
- app/services/ingestion.py — ETL orchestration + audit

---

## Database Model (What to Say — 2 min)

Normalized 3NF OLTP schema:

- frequency (D, M, Q…) → exchange_rate_series → exchange_rate_observation
- currency (USD, GBP, JPY…)
- ingestion_run — pipeline audit (status, row counts, errors)

Example series key: D.USD.EUR.SP00.A (daily USD vs EUR, spot average)

Unique constraint: (series_id, time_period) — enables idempotent reloads

Sample SQL:

  SELECT o.time_period, o.obs_value
  FROM exchange_rate_observation o
  JOIN exchange_rate_series s ON s.id = o.series_id
  WHERE s.series_key = 'D.USD.EUR.SP00.A'
  ORDER BY o.time_period DESC
  LIMIT 5;

---

## Live Demo Commands (15 min)

### Step 1 — Start stack

  cd ecb-exchange-rate-pipeline
  docker compose -f docker/docker-compose.yml up --build

Say: Postgres 16 with healthcheck; migrate runs Alembic; API on port 8000.

### Step 2 — Health check

  curl -s http://localhost:8000/health | python3 -m json.tool

Expect: "status": "ok", "db": "ok"

### Step 3 — Run ingestion

  curl -s -X POST http://localhost:8000/api/v1/ingest \
    -H "Content-Type: application/json" \
    -d '{"start_period":"2026-01-01","end_period":"2026-01-31"}' \
    | python3 -m json.tool

Say: Creates ingestion_run; calls real ECB API; shows rows_fetched, rows_inserted, rows_updated.

### Step 4 — Audit trail

  curl -s "http://localhost:8000/api/v1/ingestion-runs?limit=3" | python3 -m json.tool

### Step 5 — Idempotency (run ingest again)

Re-run the same POST /api/v1/ingest command.

Say: Second run updates existing rows; no duplicate observations per series/date.

### Step 6 — Query data

  curl -s "http://localhost:8000/api/v1/series?currency=USD&freq=D" | python3 -m json.tool

  curl -s "http://localhost:8000/api/v1/series/D.USD.EUR.SP00.A/observations?start=2026-01-01&end=2026-01-31" | python3 -m json.tool

  curl -s "http://localhost:8000/api/v1/observations/latest?currency=USD" | python3 -m json.tool

Open: http://localhost:8000/docs (Swagger UI)

### Step 7 — Tests & CI

  pip install -e ".[dev]"
  PYTHONPATH=. pytest tests/ -v --cov=app --cov=pipeline

Say: 21 tests, unit + integration; CI runs ruff, mypy, Postgres, alembic, pytest on every PR.

---

## Interview Talking Points

| Topic | Your answer |
|-------|-------------|
| Why PostgreSQL? | OLTP, dates/decimals, ON CONFLICT upserts, serves live API |
| Idempotency? | Unique (series_id, time_period) + upsert on load |
| Bad data? | Transform skips invalid rows; ingestion_run stores errors |
| Schema changes? | Alembic migrations; migrate service in Docker |
| Scheduling? | POST /ingest, run_pipeline.py, backfill.py, or cron/Actions |
| Scale? | Chunked backfill (--chunk-days 31); indexed time series |

---

## Likely Q&A

Q: Why not load CSV directly to a warehouse?
A: This is a serving-layer OLTP pipeline; a warehouse can consume from DB replication or API.

Q: What if ECB changes CSV format?
A: Extend transform/parser; check ingestion_run.error_message; see docs/runbook.md.

Q: How do you monitor failures?
A: ingestion_run table + GitHub Actions data_quality workflow (freshness check).

---

## Tech Stack (for CV / slide)

Python 3.12 | FastAPI | SQLAlchemy 2 (async) | PostgreSQL 16 | Alembic | pandas | httpx | Docker | GitHub Actions | pytest

---

## Demo Timing (20 min)

| Min | Activity |
|-----|----------|
| 0-2 | Pitch + architecture |
| 2-4 | Schema / 3NF |
| 4-6 | docker compose up |
| 6-10 | Ingest + audit + idempotent re-run |
| 10-13 | API queries + /docs |
| 13-16 | Code walkthrough + tests |
| 16-20 | Q&A |

---

## Cleanup

  docker compose -f docker/docker-compose.yml down

To remove database volume: add -v flag

---

## Backup: Without Docker

  export DATABASE_URL=postgresql+asyncpg://ecb_user:ecb_password@localhost:5432/ecb_rates
  alembic upgrade head
  uvicorn app.main:app --reload --port 8000
  python scripts/run_pipeline.py --start 2026-01-01 --end 2026-01-31

---

Good luck with your presentation!
