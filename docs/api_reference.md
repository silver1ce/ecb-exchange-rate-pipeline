# API Reference

Base URL: `http://localhost:8000`

Interactive docs: `/docs` (Swagger UI), `/redoc`

## Health

### `GET /health`

Returns service and database connectivity status.

**Response**

```json
{
  "status": "ok",
  "db": "ok",
  "timestamp": "2026-06-04T08:00:00Z"
}
```

## Series

### `GET /api/v1/series`

List exchange rate series.

**Query parameters**

| Name | Type | Description |
|---|---|---|
| `currency` | string | Filter by ISO code (e.g. `USD`) |
| `freq` | string | Filter by frequency code (e.g. `D`) |

**Example**

```bash
curl "http://localhost:8000/api/v1/series?currency=USD&freq=D"
```

## Observations

### `GET /api/v1/series/{series_key}/observations`

Paginated observations for a series.

**Path parameters**

- `series_key` — ECB series key (e.g. `D.USD.EUR.SP00.A`)

**Query parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `start` | date | — | Inclusive start date |
| `end` | date | — | Inclusive end date |
| `page` | int | 1 | Page number |
| `size` | int | 100 | Page size (max 1000) |

**Example**

```bash
curl "http://localhost:8000/api/v1/series/D.USD.EUR.SP00.A/observations?start=2026-01-01&end=2026-01-31&page=1&size=100"
```

### `GET /api/v1/observations/latest`

Most recent observation per series.

**Query parameters**

| Name | Type | Description |
|---|---|---|
| `currency` | string | Optional ISO currency filter |

**Example**

```bash
curl "http://localhost:8000/api/v1/observations/latest?currency=USD"
```

## Ingestion

### `POST /api/v1/ingest`

Trigger a manual ingestion run.

**Request body**

```json
{
  "start_period": "2026-01-01",
  "end_period": "2026-01-31"
}
```

**Example**

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"start_period":"2026-01-01","end_period":"2026-01-31"}'
```

### `GET /api/v1/ingestion-runs`

List recent ingestion runs.

**Query parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `limit` | int | 20 | Max runs to return (1–100) |

**Example**

```bash
curl "http://localhost:8000/api/v1/ingestion-runs?limit=10"
```

## Error Responses

| Status | Meaning |
|---|---|
| 400 | Invalid request payload or date range |
| 404 | Series not found |
| 422 | Validation error |
| 500 | Unhandled server error |
