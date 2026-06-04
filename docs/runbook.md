# Runbook

## Local run without Docker

```bash
./scripts/run_local.sh
```

Uses SQLite (`data/ecb_rates.db`). Initialize tables only: `python scripts/init_db.py`.

## Trigger a Backfill

For large historical ranges, use chunked backfill:

```bash
python scripts/backfill.py --start 2020-01-01 --end 2025-12-31 --chunk-days 31
```

For a single range:

```bash
python scripts/run_pipeline.py --start 2026-01-01 --end 2026-01-31
```

Or via API:

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"start_period":"2026-01-01","end_period":"2026-01-31"}'
```

## Check Ingestion Run History

```bash
curl http://localhost:8000/api/v1/ingestion-runs?limit=20
```

SQL:

```sql
SELECT id, status, started_at, finished_at, rows_fetched, rows_inserted, rows_updated, error_message
FROM ingestion_run
ORDER BY started_at DESC
LIMIT 20;
```

## ECB API Returns Unexpected Format

1. Inspect the failing `ingestion_run.api_url` and reproduce with `curl`.
2. Check application logs for transform warnings (`Skipping invalid row`).
3. If ECB adds columns, update `ObservationDTO` and transform parsing.
4. If `TIME_PERIOD` format changes, extend `parse_time_period()` in `pipeline/transform.py`.
5. If CSV comment/header layout changes, update `_parse_csv_response()` in `app/services/ecb_client.py`.
6. Re-run ingestion for the affected date range after deploying a fix.

## Add a New Currency Filter

1. Set `DEFAULT_CURRENCIES` in `.env`:

   ```env
   DEFAULT_CURRENCIES=USD,GBP,CHF
   ```

2. Pass currency to ingestion (future enhancement) or filter at API query time:

   ```bash
   curl "http://localhost:8000/api/v1/series?currency=CHF"
   ```

3. No schema migration is required — currencies are upserted dynamically during load.

## Failed Ingestion Recovery

1. Identify failure:

   ```sql
   SELECT * FROM ingestion_run WHERE status = 'failed' ORDER BY started_at DESC LIMIT 1;
   ```

2. Fix root cause (network, schema, parsing).
3. Re-trigger ingestion for the same period — upserts are idempotent.

## Database Migration

```bash
alembic upgrade head
```

In Docker, the `migrate` service runs this automatically on startup.

## Health Verification

```bash
curl http://localhost:8000/health
docker compose -f docker/docker-compose.yml ps
```

Expected: API `status=ok`, DB `db=ok`, Postgres container healthy.
