# DECISIONS.md

## Acdyon Technologies Engineering Challenge — Part 1

---

### 1. Why this ingestion strategy over the obvious alternative?

**The obvious alternative** — scraping LinkedIn, Indeed, Naukri, or Wellfound — was explicitly rejected for three reasons: those platforms actively block automated clients, the challenge asks for a live demo with low-risk data sources, and demonstrating evasion techniques (proxy rotation, stealth browsers, fingerprint spoofing) is both ethically wrong and outside the engineering goal of the assessment.

**What was chosen instead:** Arbeitnow's public REST API (`https://www.arbeitnow.com/api/job-board-api`), which requires no authentication, has no robots.txt restrictions on API access, and is explicitly designed for programmatic consumption.

**Provider-adapter architecture:** The ingestion layer defines a `JobSource` Protocol:

```python
class JobSource(Protocol):
    source_name: str
    async def fetch_jobs(self) -> list[RawJob]: ...
```

`ArbeitnowAdapter`, `MockAdapter`, and any future `RSSAdapter` all implement this interface. The ingestion service, REST API, and circuit breaker never import a concrete adapter — only the factory does. Adding a new permitted source means writing one new class and registering it in `factory.py`. Nothing else changes.

---

### 2. One trade-off made under the time limit

**SQLite over PostgreSQL.**

SQLite was chosen because the demo requires no distributed writes and zero infrastructure setup. This freed time to focus on the actually interesting engineering: resilience handling, circuit breaker state, deduplication, and observability.

The trade-off is real: SQLite has a single-writer limitation and no native connection pooling. In production with multiple backend workers, this would be a bottleneck. The mitigation:

- WAL journal mode is enabled, improving concurrent read performance.
- The database layer is fully decoupled from the ingestion logic via SQLAlchemy — switching to PostgreSQL means changing `DATABASE_URL` and dropping the `check_same_thread` connection argument. No service code changes are required.
- The `IngestionRun` audit table is append-only, which SQLite handles well.

With a full week: PostgreSQL + pgBouncer, distributed circuit breaker state in Redis, and a proper task queue for scheduled ingestion.

---

### 3. AI usage

AI assistance (Claude) was used in this project in the following specific ways:

- **Boilerplate scaffolding:** The Pydantic model structure, SQLAlchemy ORM column definitions, and FastAPI router registration followed patterns I described in natural language and AI generated the initial skeleton. I reviewed every field for correctness and adjusted types.
- **Test fixture debugging:** AI identified that SQLite in-memory databases use per-connection isolation and suggested `StaticPool` to share a single connection across the test session and the dependency override — I verified this was the actual root cause before applying it.
- **CSS design system:** The color tokens, typography scale, and animation keyframes were generated from a prompt describing the engineering-tool aesthetic. I adjusted the palette and removed several overdesigned elements.

What I personally wrote and verified:
- The `JobSource` Protocol design and adapter interface
- The ingestion pipeline flow and error classification logic
- The circuit breaker state machine transitions
- The deduplication strategy (composite unique key + content hash fallback)
- The rate limiter backoff formula and Retry-After parsing
- All test assertions and the StaticPool fix
- Deployment configuration choices
