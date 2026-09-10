# Opportunity Ingestion Framework

Self-contained vertical slice, same convention as `app/profile_analysis/`,
`app/career_roadmap/`, `app/career_simulation/` and `app/ai_coach/` — it owns
its own `models/services/utils`, plus (specific to this module)
`agents/`, `pipeline/`, and `jobs/`.

**No source-specific crawler exists yet** — that's still true. Persistence,
however, now does: `OpportunityService` is the ONLY layer allowed to talk to
Supabase for opportunity ingestion. See "No crawler talks to Supabase"
below.

```
ingestion/
  models/
    config.py        AgentConfig, RetryConfig, RateLimitConfig
    discovery.py      DiscoveredListing, RawExtraction
    opportunity.py    NormalizedOpportunity
    persistence.py    OpportunitySaveResult, BatchSaveResult, IngestionStats
    validation.py     ValidationIssue, ValidationResult
    run.py            AgentRunResult, IngestionError, PipelineStage
  agents/
    base.py          BaseOpportunityAgent, AgentContext
    registry.py      AgentRegistry, agent_registry
  pipeline/
    runner.py        IngestionPipeline — discover -> extract -> normalize -> validate
  jobs/
    schedule.py      ScheduleConfig (interval | cron), should_run()
    registry.py       JobRegistry, job_registry
  services/
    ingestion_service.py     IngestionService — runs agents through the pipeline
    opportunity_service.py   OpportunityService — validates, dedupes, persists, queues enrichment
    repository.py            OpportunityRepository — the ONLY file that queries `opportunities` for ingestion
  utils/
    retry.py         retry_async / with_retry — exponential backoff + full jitter
    rate_limit.py    RateLimiter protocol + TokenBucketRateLimiter
    logging.py       IngestionLogAdapter — per-run/source/stage structured logs
    validation.py    basic_field_checks() — reusable common validate() rules
    fingerprint.py   generate_fingerprint() — deterministic, content-based dedupe key
```

## Flow

```
Agent
  |
  v
discover(ctx)          -> list[DiscoveredListing]     (one call, retried + rate-limited)
  |
  v  (per listing, bounded concurrency)
extract(ctx, listing)  -> RawExtraction                (retried + rate-limited)
  |
  v
normalize(ctx, raw)    -> NormalizedOpportunity         (pure, no I/O)
  |
  v
validate(ctx, opp)     -> ValidationResult              (pure, no I/O)
  |
  v
AgentRunResult { opportunities: [NormalizedOpportunity, ...], errors: [...] }
```

`IngestionPipeline.run()` (called by `BaseOpportunityAgent.run()`, called by
`IngestionService`) returns an `AgentRunResult` — **in memory only**. Nothing
in this call chain touches Supabase or any other datastore.

A failure at `extract()`/`normalize()`/`validate()` for one listing is
recorded as an `IngestionError` and that listing is skipped; it never aborts
the rest of the run (a scraper hitting one broken page is the normal case,
not an exceptional one). A failure at `discover()` — there being nothing to
process at all — does end the run early, since there's nothing left to do.

Persisting an `AgentRunResult`'s opportunities is a separate step, done by
the *caller* of `IngestionService`, not by the pipeline itself:

```python
run_result = await ingestion_service.run_source("aws-cloud-clubs")
batch_result = await opportunity_service.save_batch(run_result.opportunities)
```

## No crawler talks to Supabase

`OpportunityService` (`services/opportunity_service.py`) is the only layer
allowed to communicate with Supabase for opportunity ingestion. It owns:

- **validation** — `validate()` re-checks `basic_field_checks()` before
  persistence, independent of whatever an agent's own `validate()` already
  did (this service can't assume every caller went through the pipeline).
- **insert/update** — `save_opportunity()` (dedupe-then-upsert),
  `save_batch()` (per-item error isolation + a `BatchSaveResult` summary),
  `update_opportunity()` (explicit update-by-id).
- **deterministic fingerprinting** — `generate_fingerprint()`
  (`utils/fingerprint.py`), a SHA-256 over normalized (title, organization,
  apply_url), so the exact same real-world opportunity always hashes
  identically regardless of which agent produced it.
- **duplicate detection** — `find_duplicate()` checks `(source,
  source_id)` first (exact, per-source identity —
  `schema/005_opportunities_v2.sql`), then the fingerprint (catches a
  *different* source listing the *same* opportunity —
  `schema/019_opportunities_ingestion.sql`).
- **ingestion statistics** — `get_stats()` / `IngestionStats`: cumulative
  created/updated/rejected/error/queued-for-enrichment counters for the
  service instance's lifetime.
- **logging** — every outcome (created, updated, rejected, error, queued)
  is logged via `app.core.logging`, the same console/JSON setup as the rest
  of the API.
- **queueing AI enrichment** — `mark_for_enrichment()` sets
  `enrichment_status='pending'` on the row and enqueues an
  `enrich_opportunity` task via the existing `app.workers.queue`
  abstraction (not a new one). Called automatically on every newly
  *created* row inside `save_opportunity()`; not on updates (see that
  method's docstring).

`OpportunityRepository` (`services/repository.py`) is the only file that
actually issues Supabase queries for any of this — it uses the
service-role client (`get_admin_supabase()`), since ingestion is trusted
background work, not a user-driven request (`opportunities` is writable by
nobody through the anon-key API; see `backend/README.md`'s "Why RLS is not
optional"). Agents never import it, never import `app.db.supabase`, and
never import `supabase` — an agent's entire contract is "return
`NormalizedOpportunity` objects," which is what makes "future agents
require zero database logic" true by construction, not just by convention.

**Python naming note:** the framework spec's method names
(`saveOpportunity()`, `saveBatch()`, `updateOpportunity()`,
`findDuplicate()`, `markForEnrichment()`) are camelCase; this codebase is
100% snake_case Python (see `pyproject.toml`'s `ruff` config and every
other service in the repo), so they're implemented as `save_opportunity()`,
`save_batch()`, `update_opportunity()`, `find_duplicate()`,
`mark_for_enrichment()` — same responsibilities, adapted spelling.

## Naming: `source_id`, not `external_id`

This framework was originally written against a column named `external_id` (see `005_opportunities_v2.sql`'s comment). The live `public.opportunities` table was renamed to `source_id` directly, outside source control, before this framework's first real agent (Devpost) was written against it -- `025_opportunities_ingestion_source_id_rename.sql` brings that into source control and every reference in this package (`NormalizedOpportunity.source_id`, `OpportunityRepository.get_by_source_and_source_id()`, `OpportunitySaveResult.source_id`) was renamed to match. Use `source_id` everywhere in new code; `external_id` should not appear anywhere under `app/ingestion/` going forward.

## Adding a new source

Exactly one new class, in one new file (e.g.
`agents/sources/aws_cloud_clubs.py` — that `sources/` subpackage doesn't
exist yet; create it when the first real agent lands):

```python
from app.ingestion.agents.base import AgentContext, BaseOpportunityAgent
from app.ingestion.agents.registry import agent_registry
from app.ingestion.models.discovery import DiscoveredListing, RawExtraction
from app.ingestion.models.opportunity import NormalizedOpportunity
from app.ingestion.models.validation import ValidationResult
from app.ingestion.utils.validation import basic_field_checks, to_validation_result


@agent_registry.register
class AwsCloudClubsAgent(BaseOpportunityAgent):
    source = "aws-cloud-clubs"          # stable forever; becomes NormalizedOpportunity.source
    default_category = "programs"

    async def discover(self, ctx: AgentContext) -> list[DiscoveredListing]:
        await ctx.rate_limiter.acquire()
        response = await ctx.http_client.get("https://builder.aws.com/community/student-builder-groups")
        # ... parse `response.text` for listing URLs ...
        return [DiscoveredListing(url=url, source=self.source) for url in urls]

    async def extract(self, ctx: AgentContext, listing: DiscoveredListing) -> RawExtraction:
        response = await ctx.http_client.get(listing.url)
        return RawExtraction(
            url=listing.url, source=self.source,
            http_status=response.status_code, raw_content=response.text,
        )

    def normalize(self, ctx: AgentContext, raw: RawExtraction) -> NormalizedOpportunity:
        # ... parse raw.raw_content (BeautifulSoup, regex, whatever the source needs) ...
        return NormalizedOpportunity(
            category="programs", title=..., apply_url=raw.url,
            source=self.source, source_id=..., source_url=raw.url,
        )

    def validate(self, ctx: AgentContext, opportunity: NormalizedOpportunity) -> ValidationResult:
        issues = basic_field_checks(opportunity)
        # add source-specific rules here if needed
        return to_validation_result(issues)
```

That's it — no changes anywhere else. `IngestionService.run_source("aws-cloud-clubs")`
or `IngestionService.run_all()` will pick it up via `agent_registry`. Note
`run()` is **not** overridden: it's inherited from `BaseOpportunityAgent` and
already wires the four methods above through `IngestionPipeline` with retry,
rate limiting, structured logging, and per-listing error isolation.

To give it a schedule (optional — an unscheduled agent is still runnable
on-demand via `run_source()`):

```python
from app.ingestion.jobs.registry import job_registry
from app.ingestion.jobs.schedule import ScheduleConfig

job_registry.set("aws-cloud-clubs", ScheduleConfig.every(6 * 60 * 60))   # every 6 hours
# or: ScheduleConfig.cron("0 */6 * * *")
```

Note the agent above never imports Supabase, a repository, or
`OpportunityService` — persistence happens after `run()` returns, driven by
whatever calls `IngestionService` (see "No crawler talks to Supabase"
below), not by the agent itself.

## Design decisions

**`run()` is concrete, not abstract, even though the spec says "every agent
implements discover/extract/normalize/validate/run."** Making `discover`
through `validate` abstract and `run` a template method on the base class
satisfies that requirement through inheritance — every agent *does* have a
working `run()` — while being the entire reason a new source is one class
instead of one class plus a hand-copied orchestration loop. Overriding `run()`
itself should be rare; see the docstring on `BaseOpportunityAgent.run()`.

**Dependency injection via `AgentContext`.** `discover`/`extract`/`normalize`/
`validate` never construct their own `httpx.AsyncClient` or rate limiter —
they receive one on `ctx`. `IngestionService` builds a fresh context per run
in production; a test can construct an `AgentContext` with a fake HTTP client
and call `agent.run(ctx)` directly without any monkeypatching.

**`models/` here is not `app/models/`'s convention.** The rest of the repo
splits `schemas/` (wire contract) from `models/` (DB row) — see
`backend/README.md`. Ingestion never touches the database, so there's no DB
row to model; `models/` here holds pipeline-internal DTOs instead. This was
the explicit folder name requested for this module, and is documented here
so the deviation from the repo-wide convention isn't mistaken for an
inconsistency. `NormalizedOpportunity` still mirrors
`app.schemas.opportunity.Opportunity` / `app.models.opportunity.OpportunityRow`
field-for-field (and reuses the same `OpportunityCategory` literal) so a
future persistence step is a straight attribute copy.

**Retry wraps `discover()` and `extract()` only.** Those are the I/O stages.
`normalize()`/`validate()` are specified as pure transforms — no network
calls — so retrying them would only mask a real bug in the parser, not a
transient failure.

**Rate limiting is a `Protocol`, not a concrete class, on `AgentContext`.**
`TokenBucketRateLimiter` is the real implementation; `NullRateLimiter` exists
for tests and for a source with no meaningful limit. One instance is shared
across every concurrent `extract()` call within a run (via `AgentConfig.
max_concurrency`'s semaphore), so the token bucket actually bounds the whole
run's request rate, not just each call in isolation.

**Cron scheduling has no external dependency.** `jobs/schedule.py` implements
a minimal 5-field cron matcher itself rather than adding `croniter` to
`requirements.txt`, since the only thing needed right now is "does this
expression match this instant," evaluated by a caller polling roughly once a
minute — not calendar-accurate "list the next N run times" math. If that
becomes a real requirement later, swap the matcher for `croniter` without
changing `ScheduleConfig`'s shape.

**No new third-party dependencies.** Retry, rate limiting, and scheduling are
all implemented on the standard library (`asyncio`, `time`, `re`) plus
`httpx` and `pydantic`, both already in `requirements.txt`. Nothing new to
add.

**`OpportunityRepository` does not extend `app.db.repositories.base.
BaseRepository`.** That base class is unused everywhere else in the
codebase — every self-contained module (`career_simulation`,
`career_roadmap`, `ai_coach`) writes its own small repository class holding
a client directly, and this follows that actual, proven convention rather
than the nominal one.

**Supabase calls in `OpportunityRepository` are synchronous, even though
`OpportunityService`'s methods are `async def`.** Same convention as every
other repository in this codebase (`career_simulation`'s, `career_roadmap`'s)
— `supabase-py`'s client is sync, and nothing here wraps it in
`asyncio.to_thread`. `save_batch()` processes its list sequentially rather
than with `asyncio.gather` for the same reason: gathering synchronous calls
doesn't add real parallelism, just complexity.

**`OpportunityService` lives in `app.ingestion.services`, not
`app.services`.** `app/services/opportunity_service.py` already exists and
already defines a class named `OpportunityService` — but for a different
concern entirely (the read-facing Discover catalogue: list/search/save-for-
user). This module's `OpportunityService` is the ingestion write path. Same
class name, different module, no collision — but worth knowing both exist
before importing one when you meant the other.

**Row writes are sparse.** `_to_row()` omits any field the agent didn't
determine (`None`) rather than sending it explicitly — so updating an
already-known opportunity never nulls out a value a previous, more complete
ingestion pass had already set.

## Status (updated after the Devfolio agent landed)

- **Two real source agents**, both `category="hackathons"`, sharing the
  same `HACKATHON_DAILY_LIMIT`/`HACKATHON_CANDIDATE_POOL_SIZE` save-target
  design (candidates are *selected* up to the pool size;
  `OpportunityService.save_batch()`'s `max_success_count` is what
  actually stops each source's own run once `HACKATHON_DAILY_LIMIT`
  opportunities are created/updated — this is a per-run, per-source cap,
  not a budget shared across sources):
  - `agents/sources/devpost.py` (`DevpostHackathonAgent`) — see
    `select_top_candidates()`'s docstring for its ranking. Discovery hits
    Devpost's own `/api/hackathons` JSON endpoint directly.
  - `agents/sources/devfolio.py` (`DevfolioAgent`) — discovery is a
    two-request, self-healing sequence (read the current Next.js buildId
    out of a plain `/hackathons` page's own `__NEXT_DATA__` tag, then
    fetch that buildId's `_next/data/.../hackathons.json`, Devfolio's own
    client-side data route) — see that module's docstring for the full
    mechanism and why it was chosen over anything undocumented/guessed.
- **An HTTP route exists**: `api/v1/routes/ingestion.py` —
  `POST /ingestion/run/{source}`, `GET /ingestion/due`,
  `POST /ingestion/run-due`, all behind the `X-Ingestion-Admin-Key` shared
  secret (`INGESTION_ADMIN_API_KEY`, fails closed if unset). Every route
  also accepts `?dry_run=true` (see `OpportunityService.preview_batch()`)
  to run discovery/validation/dedup without writing.
- **No AI enrichment worker.** `mark_for_enrichment()` sets
  `enrichment_status='pending'` and enqueues a task, but
  `app/workers/tasks/opportunity_enrichment.py`'s `enrich_opportunity()`
  itself raises `NotImplementedYetError` — what "enrichment" actually
  produces (richer tags, a cleaned description, embeddings, something else)
  isn't decided yet. The Devpost agent does not depend on it: discover ->
  extract -> normalize -> validate -> save all work standalone.
- **No production job queue.** `mark_for_enrichment()` goes through
  `app.workers.queue.get_queue()`, which returns an in-memory, executes-
  nothing stand-in until `ENABLE_BACKGROUND_WORKERS`/a real broker is
  configured (see that module).
- **No scheduler daemon runs `/ingestion/run-due` itself.**
  `JobRegistry.due_sources()` (and `GET /ingestion/due`) tell you what
  *should* run; nothing inside this backend process calls
  `POST /ingestion/run-due` on a timer. An external scheduler (cron,
  Supabase's `pg_cron` + `pg_net`, a Supabase scheduled Edge Function, a
  GitHub Actions scheduled workflow, etc.) still needs to be pointed at it
  — see `PRODUCTION_SMOKE_TEST.md` in this directory for the exact request.
- **No embeddings.** Out of scope per the framework spec; would hook in via
  the existing `app/services/embedding_service.py` path once triggered by
  the (not yet implemented) enrichment worker, same as any other
  opportunity row.
- **Two sources are registered (Devpost, Devfolio).** Unstop/MLH/
  HackerEarth and any LLM-based discovery are deliberately NOT
  implemented yet — see this file's "Adding a new source" section and
  `PRODUCTION_SMOKE_TEST.md`'s closing recommendation for what to add
  next, once both existing sources have run in production for a while.

## Verifying this module

```bash
cd backend
pip install -r requirements-dev.txt
ruff check app/ingestion api/v1/routes/ingestion.py
pytest tests/test_ingestion_pipeline.py tests/test_opportunity_service.py \
       tests/test_devpost_agent.py tests/test_devfolio_agent.py \
       tests/test_ingestion_schedule.py tests/test_ingestion_route.py -v
```

- `tests/test_ingestion_pipeline.py` — the framework itself, source-agnostic:
  successful runs, partial failures with retry exhaustion,
  `AgentRegistry`/`JobRegistry`, `IngestionService.run_source()`/
  `run_all()`, `retry_async`'s backoff/exhaustion behavior,
  `TokenBucketRateLimiter`, both `ScheduleConfig` kinds, that
  `result.opportunities` preserves `discover()`'s own candidate order
  despite concurrent extraction, and that `AgentConfig.daily_save_limit`
  relays onto `AgentRunResult`.
- `tests/test_opportunity_service.py` — `OpportunityService` against a fake
  in-memory `OpportunityRepository` and a fake queue: fingerprint
  determinism, rejection on invalid input, `find_duplicate()`'s
  (source, source_id) -> fingerprint fallback order, create-vs-update
  branching, `save_batch()`'s per-item error isolation/stats AND its
  `max_success_count` stop condition, and `preview_opportunity()`/
  `preview_batch()`'s zero-write dry-run guarantee.
- `tests/test_devpost_agent.py` — `DevpostHackathonAgent` end-to-end against
  a fake HTTP client: discovery filtering/pagination/ranking, normalization,
  validation, the candidate-pool-vs-daily-save-limit distinction, dedup
  across 3 consecutive runs, and dry-run previews.
- `tests/test_devfolio_agent.py` — `DevfolioAgent` end-to-end against a
  fake HTTP client covering its own two-request discovery mechanism
  (buildId extraction, the `hackathons.json` bucket snapshot, excluding
  `past_hackathons`, deduping `featured_hackathons` against
  open/upcoming), normalization (including the apply_url vs. source_url
  distinction), validation, the candidate-pool-vs-daily-save-limit
  distinction, dedup across 3 consecutive runs, and dry-run previews.
- `tests/test_ingestion_schedule.py` — both hackathon sources' own
  registered cron schedules (Devpost at 06:00 UTC, Devfolio at 12:00
  UTC — offset so they don't collide), timezone correctness (a local
  "06:00" in another offset must NOT be treated as due), and
  invalid/missing `ScheduleConfig` rejection.
- `tests/test_ingestion_route.py` — the `/ingestion/*` routes' security
  (fail-closed when unconfigured, 401 on a wrong secret, success on the
  right one, the secret never appears in a response body, no other route
  accidentally requires it) and the `?dry_run=true` wiring end-to-end.

Applying `schema/019_opportunities_ingestion.sql` AND
`schema/025_opportunities_ingestion_source_id_rename.sql` (see
`supabase/README.md`) is required before `OpportunityService` is used
against a real database — see `PRODUCTION_SMOKE_TEST.md` for the exact SQL
and the order to run it in.
