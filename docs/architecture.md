# JobPulse Architecture

## System Overview

JobPulse is a provider-agnostic job ingestion pipeline with a FastAPI backend and React frontend. The architecture prioritizes resilience and observability over simplicity.

```
Arbeitnow Public API
        │
        │ HTTPS (single request per run, conservative)
        ▼
┌─────────────────────┐
│   ArbeitnowAdapter  │  ← Implements JobSource Protocol
│   (or MockAdapter)  │
└──────────┬──────────┘
           │ list[RawJob]
           ▼
┌─────────────────────┐
│   Rate Limiter      │  ← timeout, retry, backoff+jitter, Retry-After
│   Request Policy    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Circuit Breaker    │  ← CLOSED / OPEN / HALF_OPEN
│  (guards fetch)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Pydantic Validator │  ← HTTP status, JSON structure, field types
│  (RawJob model)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Normalization      │  ← Provider fields → internal RawJob model
│  (per adapter)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Deduplication      │  ← source + external_id (UNIQUE), hash fallback
│  (DB-level + Python)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   SQLite DB (WAL)   │  ← jobs + ingestion_runs tables
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   FastAPI REST API  │  ← /api/jobs, /api/ingestion/*, /health
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  React Dashboard    │  ← Polls status, renders metrics + jobs
└─────────────────────┘
```

---

## Source Adapter Interface

Any job source must implement the `JobSource` Protocol:

```python
class JobSource(Protocol):
    source_name: str

    async def fetch_jobs(self) -> list[RawJob]:
        ...
```

Current implementations:
- `ArbeitnowAdapter` — fetches from `https://www.arbeitnow.com/api/job-board-api`
- `MockAdapter` — in-process mock with configurable scenarios

Future adapters can be added in `app/sources/` without touching any other code. Register in `app/sources/factory.py`.

---

## Detection / Access Surface

Since JobPulse uses a **permitted public API**, we do not implement or need any evasion techniques. This section documents what makes automated clients detectable on *hostile* platforms — for educational context only.

### Signals hostile platforms use to detect automated clients:

| Signal | How it manifests |
|---|---|
| **Request frequency** | Requests faster than human browsing speed; no idle time between pages |
| **Missing/incorrect headers** | No `Referer`, wrong `Accept-Language`, missing cookies |
| **Abnormal request patterns** | Sequential resource loading, no asset requests, perfect timing |
| **Session behavior** | No cookie jar maintenance, missing CSRF tokens |
| **IP reputation** | Known datacenter IP ranges, Tor exit nodes, known proxy providers |
| **Browser automation signals** | `navigator.webdriver=true`, missing browser APIs, DevTools markers |
| **CAPTCHA** | reCAPTCHA, hCaptcha triggered on suspicious behavior |
| **TLS fingerprint** | `JA3` fingerprint reveals non-browser TLS stack |
| **Response anomalies** | Bot traps (invisible links), honeypot fields in forms |

> **The live implementation does not attempt to bypass these controls.** It uses a permitted public API (`arbeitnow.com/api/job-board-api`) and conservative request behavior (single request per run, honest User-Agent, respect for Retry-After).

---

## Ingestion Strategy

### Primary flow

```
POST /api/ingestion/run
    │
    ├── Circuit breaker check
    │       OPEN? → return CIRCUIT_OPEN (serve cached data)
    │
    ├── source.fetch_jobs()
    │       │
    │       ├── HTTP 200 → parse JSON → validate schema → normalize
    │       │
    │       ├── HTTP 429 → SourceRateLimitedError
    │       │       └── status = RATE_LIMITED, preserve existing data
    │       │
    │       ├── HTTP 5xx → retry (max_retries) → SourceUnavailableError
    │       │       └── status = FAILED, preserve existing data
    │       │
    │       ├── Timeout → retry (max_retries) → SourceUnavailableError
    │       │       └── status = FAILED, preserve existing data
    │       │
    │       ├── Empty response → SourceEmptyError
    │       │       └── status = EMPTY_SOURCE, preserve existing data
    │       │
    │       └── Schema error → SourceSchemaError
    │               └── status = SCHEMA_ERROR, preserve existing data
    │
    ├── Persist (deduplication in Python + DB UNIQUE constraint)
    │
    └── Record IngestionRun (always, success or failure)
```

### What happens if...

| Scenario | Behavior |
|---|---|
| Source changes field names | Schema validation fails → `SCHEMA_ERROR`, existing data preserved |
| Source returns 429 | `RATE_LIMITED` recorded, circuit breaker failure counted |
| Source returns 500 | Retried up to `HTTP_MAX_RETRIES` times with backoff |
| Source returns empty response | `EMPTY_SOURCE` — **existing jobs are NOT deleted** |
| Source becomes unavailable | Circuit breaker opens after N failures; `CIRCUIT_OPEN` on next run |
| Database error | Run status = `FAILED`, error logged, API returns 500 |

---

## Database Schema

### `jobs`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `external_id` | TEXT | Provider's slug/ID |
| `source` | TEXT | "arbeitnow", "mock", etc. |
| `title` | TEXT | Required |
| `company` | TEXT | Required |
| `location` | TEXT | Nullable |
| `description` | TEXT | HTML, nullable |
| `url` | TEXT | Original listing URL |
| `remote` | BOOLEAN | |
| `category` | TEXT | First tag |
| `tags` | TEXT | JSON array |
| `published_at` | DATETIME | From provider |
| `first_seen_at` | DATETIME | When first ingested |
| `last_seen_at` | DATETIME | Updated on re-ingestion |
| `content_hash` | TEXT | SHA-256 of company+title+url |

Unique constraint: `(source, external_id)`

### `ingestion_runs`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `source` | TEXT | |
| `started_at` | DATETIME | |
| `completed_at` | DATETIME | |
| `status` | TEXT | SUCCESS, FAILED, etc. |
| `records_fetched` | INTEGER | |
| `records_accepted` | INTEGER | |
| `duplicates` | INTEGER | |
| `validation_failures` | INTEGER | |
| `http_status` | INTEGER | Nullable |
| `latency_ms` | INTEGER | End-to-end |
| `error_message` | TEXT | Nullable |
