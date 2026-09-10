# Hackathon ingestion (Devpost + Devfolio) — production smoke test

A step-by-step manual check that Devpost and Devfolio → Supabase → the
existing frontend actually work end-to-end after deploying this backend.
Both sources share the same `/ingestion/*` routes, the same
`HACKATHON_DAILY_LIMIT`/`HACKATHON_CANDIDATE_POOL_SIZE` settings, and the
same `category='hackathons'` — everywhere below that differs by source is
called out explicitly (just swap `devpost` for `devfolio` in the URL/SQL
otherwise). Every command below is exact and copy-pasteable; replace the
placeholders in `<angle brackets>`.

Run this once after every deploy that touches `app/ingestion/`, and again
any time `DEVPOST_*`/`DEVFOLIO_*`/`HACKATHON_*`/`INGESTION_ADMIN_API_KEY`
change.

## Step 1 — Run the database migrations

In the Supabase SQL Editor (or via the CLI), run these two files **in
order**, exactly as they exist in the repo — do not edit them:

1. `supabase/schema/019_opportunities_ingestion.sql`
2. `supabase/schema/025_opportunities_ingestion_source_id_rename.sql`

Both are idempotent (`if not exists` / `if exists` guarded) — running them
again later, or against a database that already has some of these columns,
is safe and a no-op where nothing needs to change.

Verify they applied:

```sql
select column_name, data_type
from information_schema.columns
where table_schema = 'public'
  and table_name = 'opportunities'
  and column_name in ('source', 'source_id', 'source_url', 'fingerprint',
                       'enrichment_status', 'enrichment_queued_at');
```

Expect all six rows back. If `fingerprint`/`enrichment_status`/
`enrichment_queued_at` are missing, migration 019 did not apply — every
ingestion write will fail until it does.

```sql
select indexname, indexdef
from pg_indexes
where schemaname = 'public'
  and tablename = 'opportunities'
  and indexname in ('opportunities_source_source_id_unique', 'opportunities_fingerprint_idx');
```

Expect both indexes back — these are what makes dedup a database-level
guarantee, not just an application-level one.

## Step 2 — Configure environment variables

Set on the backend's actual deployment environment (not just `.env` on a
laptop):

```bash
INGESTION_ADMIN_API_KEY=<a long random secret — e.g. `openssl rand -hex 32`>

DEVPOST_ENABLED=true
DEVPOST_MAX_DISCOVERY_PAGES=6
DEVPOST_RATE_LIMIT_PER_SECOND=0.5
DEVPOST_REQUEST_TIMEOUT_SECONDS=15

DEVFOLIO_ENABLED=true
DEVFOLIO_RATE_LIMIT_PER_SECOND=0.5
DEVFOLIO_REQUEST_TIMEOUT_SECONDS=15

# Shared by both sources -- see app/core/config.py's comments on each.
HACKATHON_DAILY_LIMIT=20
HACKATHON_CANDIDATE_POOL_SIZE=60
```

The first line is the only one that's *required* to be set explicitly —
everything else already has the sane default shown above (see
`app/core/config.py`'s "Hackathon ingestion (Devpost)" and "Hackathon
ingestion (Devfolio)" sections) and only needs to be set if you want to
override it. If `INGESTION_ADMIN_API_KEY` is left unset, every
`/ingestion/*` request returns `503` by design (fail closed) — that itself
is a valid way to confirm the route is wired up before you're ready to
actually use it.

## Step 3 — Start the backend

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

(Or however this is actually deployed — Docker via the repo's
`Dockerfile`, a managed platform, etc. The point of this step is just:
confirm the process starts cleanly and logs
`Starting Marketeam API v0.1.0 (env=...)` with no traceback.)

Confirm the ingestion routes are live:

```bash
curl -s http://localhost:8000/api/v1/ingestion/due \
  -H "X-Ingestion-Admin-Key: <your INGESTION_ADMIN_API_KEY>" | python3 -m json.tool
```

Expected: `{"due": [...]}`. `"devpost"` only appears within its 06:00 UTC
matching minute, and `"devfolio"` only within its 12:00 UTC matching
minute (the two are offset on purpose so their daily runs don't collide —
see `devfolio.py`'s own scheduling comment) — that's correct behavior, not
a bug; use Step 4 below to run either one on demand regardless of the
schedule.

## Step 4 — Call the ingestion endpoint manually

Run this whole step once for `devpost` and once for `devfolio` — just swap
the source name in the URL; the response shape is identical either way.

**Dry run first** (zero writes — safe to run anytime, including against a
production database, to sanity-check config/connectivity before writing
anything real):

```bash
curl -s -X POST "http://localhost:8000/api/v1/ingestion/run/devpost?dry_run=true" \
  -H "X-Ingestion-Admin-Key: <your INGESTION_ADMIN_API_KEY>" | python3 -m json.tool

curl -s -X POST "http://localhost:8000/api/v1/ingestion/run/devfolio?dry_run=true" \
  -H "X-Ingestion-Admin-Key: <your INGESTION_ADMIN_API_KEY>" | python3 -m json.tool
```

Expect a `200` with a body shaped like (Devpost shown; Devfolio's looks
identical with `"source": "devfolio"`):

```json
{
  "source": "devpost",
  "dry_run": true,
  "status": "success",
  "discovered": 47,
  "selected": 47,
  "extracted": 47,
  "normalized": 47,
  "validated": 45,
  "invalid": 2,
  "duplicates": 0,
  "inserted": 20,
  "updated": 0,
  "skipped_due_to_cap": 25,
  "failed": 0,
  "daily_save_limit": 20,
  ...
}
```

If `status` is `"failed"` or `discovered` is `0`, check the backend logs
for `stage=discover` warnings first:
- For Devpost, that almost always means its public `/api/hackathons`
  response shape changed, or the outbound request is being blocked
  (firewall/proxy/egress policy).
- For Devfolio, check specifically whether the warning mentions "no
  buildId found in `__NEXT_DATA__`" — that means Devfolio's own frontend
  markup changed shape (see `devfolio.py`'s module docstring for the
  two-step buildId mechanism this depends on). Anything else is the same
  firewall/proxy/egress-policy story as Devpost.

**Then the real runs:**

```bash
curl -s -X POST "http://localhost:8000/api/v1/ingestion/run/devpost" \
  -H "X-Ingestion-Admin-Key: <your INGESTION_ADMIN_API_KEY>" | python3 -m json.tool

curl -s -X POST "http://localhost:8000/api/v1/ingestion/run/devfolio" \
  -H "X-Ingestion-Admin-Key: <your INGESTION_ADMIN_API_KEY>" | python3 -m json.tool
```

Same response shape, `"dry_run": false`, and this time `inserted`/`updated`
reflect rows actually written.

## Step 5 — Query Supabase directly

```sql
select id, title, organization, source, source_id, apply_url,
       application_deadline, is_active, category, created_at
from public.opportunities
where category = 'hackathons'
order by source, created_at desc;
```

Expect up to `HACKATHON_DAILY_LIMIT` (20 by default) rows per source, each
with `is_active = true` and a non-null `apply_url`: Devpost's pointing at a
`*.devpost.com` page with a numeric-looking `source_id`, Devfolio's
pointing at a `*.devfolio.co` page (or, for the handful where Devfolio's
own `external_apply_url` was set, wherever that literal field pointed) with
a 32-character hex `source_id` (Devfolio's `uuid`).

## Step 6 — Run ingestion again

```bash
curl -s -X POST "http://localhost:8000/api/v1/ingestion/run/devpost" \
  -H "X-Ingestion-Admin-Key: <your INGESTION_ADMIN_API_KEY>" | python3 -m json.tool
```

## Step 7 — Verify no duplicates were created

Run once per source:

```sql
select source,
       count(*) as total_rows,
       count(distinct source_id) as distinct_source_ids,
       count(distinct fingerprint) as distinct_fingerprints
from public.opportunities
where category = 'hackathons'
  and source in ('devpost', 'devfolio')
group by source;
```

For each source, `total_rows` and `distinct_source_ids` must be equal (and
`distinct_fingerprints` <= `distinct_source_ids`, since two different
source_ids are still allowed to legitimately share a fingerprint only if
they really are the same real-world opportunity — in practice, for either
source alone, expect all three numbers equal).

Each rerun's JSON response is also informative here: `inserted` should be
`0` (or close to it) and `updated`/`duplicates` should account for most or
all of what was previously created — that's the dedup guarantee working,
not a partial failure.

If `total_rows` > `distinct_source_ids` for either source, STOP and
investigate before relying on this in production — that would mean the
`opportunities_source_source_id_unique` index from Step 1 either didn't
apply or isn't being hit the way `OpportunityRepository` expects.

## Step 8 — Confirm the frontend shows them

No frontend change was needed for this (see the main response's
"Architecture" section) — `frontend/src/services/supabase/opportunities.js`
already queries `is_active = true` and filters client-side by
`category === 'hackathons'`. Open the app's Hackathons tab and confirm the
Devpost rows from Step 5 appear. If they don't, check RLS
(`supabase/policies/001_rls.sql`'s "Opportunities are readable by
authenticated users" policy) rather than the ingestion code — ingestion
writes with the service-role client, which bypasses RLS by design; reads
go through the normal per-user client, which does not.

## Wiring up the daily schedule

None of the steps above run on a timer by themselves — an external
scheduler still needs to call this on a cadence at least as fine as the
tighter of the two hackathon sources' own registered schedules (Devpost
daily at 06:00 UTC, Devfolio daily at 12:00 UTC — see the bottom-of-module
`job_registry.set(...)` call in each of `devpost.py`/`devfolio.py`). A
single hourly (or more frequent) call below covers both; each source is
silently skipped until its own matching minute. Point it at:

```bash
curl -s -X POST "https://<your-deployed-backend>/api/v1/ingestion/run-due" \
  -H "X-Ingestion-Admin-Key: <your INGESTION_ADMIN_API_KEY>"
```

Calling this more often than once a day (e.g. hourly) is safe — sources
that aren't due yet are silently skipped, not re-run.

## Next recommended step

Once both Devpost and Devfolio have run reliably in production for a few
days (no repeated `failed` statuses, dedup holding across multiple daily
runs for each, the frontend showing sensible results from both), Unstop,
MLH, and HackerEarth are the next hackathon sources worth considering —
see this directory's `README.md`'s "Adding a new source" section for the
extension pattern. None of them are implemented yet.
