# Backend

FastAPI service owning **all business logic and AI**. Supabase stays the
database, auth provider and storage layer.

> **Status: scaffold.** The structure, config, auth verification, error
> handling and health check are real. Every feature route raises
> `NotImplementedYetError` → HTTP `501`. No business logic is implemented yet.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

pytest        # health + auth-guard tests
ruff check .
```

Docs: http://localhost:8000/docs · Health: `/api/v1/health`

## Structure

```
app/
├── main.py               App factory, middleware, router mounting
│
├── core/                 Cross-cutting infrastructure
│   ├── config.py           Pydantic settings — the only place env is read
│   ├── security.py         Supabase JWT verification
│   ├── exceptions.py       AppError hierarchy (status + code + message)
│   └── logging.py          Console (dev) / JSON (prod) logging
│
├── api/
│   ├── deps.py             get_current_user, pagination — shared dependencies
│   └── v1/
│       ├── router.py       Mounts every feature router
│       └── routes/         One module per feature; thin HTTP layer only
│
├── schemas/              Pydantic request/response — the WIRE contract
├── models/               Row shapes as they exist in Postgres
├── services/             Business logic. Routes and workers both call these
│
├── ai/
│   ├── llm/                Provider interface + OpenAI/Anthropic + factory
│   ├── embeddings/         Embedding generation, document assembly
│   ├── chains/             RAG, profile analysis, roadmap pipelines
│   └── prompts/            Versioned prompt registry
│
├── vector/               pgvector store + semantic search
├── db/
│   ├── supabase.py         User-scoped (RLS) and service-role clients
│   └── repositories/       Raw queries, isolated from service logic
│
├── middleware/           Request ID, error envelope, rate limiting
├── workers/              Background jobs (embeddings, recommendations)
└── utils/                Pagination, time, text helpers
```

## Design decisions

**`schemas/` and `models/` are separate on purpose.** `schemas` is the public
API contract; `models` describes database rows. Keeping them apart means the
table can change without breaking clients, and vice versa.

**Services never import FastAPI.** They raise `AppError` subclasses; the
middleware maps those to HTTP. The same service is therefore callable from a
route, a background worker, or a script.

**Two Supabase clients, deliberately.** `get_supabase(token)` runs queries *as
the user*, so RLS still applies — this is the default. `get_admin_supabase()`
uses the service-role key and **bypasses RLS**; it is for trusted background
work only and must never be driven by user input.

**Prompts are versioned assets**, registered in `ai/prompts/`, not string
literals inside business logic — so they can be diffed, reviewed and evaluated
independently.

**AI dependencies are active** in `requirements.txt` (`openai`, `langchain`,
`langchain-openai`, `langgraph`) now that `profile_analysis` (see its own
README) imports them. They were pinned without network access in this
environment — run `pip install -U langchain langchain-openai langgraph openai`
and re-freeze if the pins conflict on your machine.

**`app/profile_analysis/` is a self-contained module, not a layer.** It has
its own `routers/services/schemas/models/utils`, unlike the rest of the app.
See `app/profile_analysis/README.md` for why. `app/career_roadmap/`,
`app/career_simulation/`, `app/ai_coach/` and `app/ingestion/` follow the
same convention.

**`app/ingestion/` is the Opportunity Ingestion Framework** — agents that
will eventually crawl external opportunity sources, the shared
pipeline/retry/rate-limiting/scheduling machinery they run through, and
`OpportunityService`, the only layer allowed to write ingested opportunities
to Supabase (validation, fingerprint-based duplicate detection, insert/
update, AI-enrichment queueing). No source-specific crawler exists yet. See
`app/ingestion/README.md`.

## Authentication

Supabase issues the JWT (Google OAuth). The browser forwards it as
`Authorization: Bearer <jwt>`. `core/security.py` verifies the signature,
expiry and audience against `SUPABASE_JWT_SECRET`, then `api/deps.py` exposes
the caller:

```python
from app.api.deps import CurrentUser

@router.get("/me")
async def read_me(user: CurrentUser):
    return {"id": user.id, "email": user.email}
```

`user.id` is the Supabase `auth.uid()` the RLS policies match on.

## Rate limiting

Every `/api/v1/*` route is rate limited (Redis-backed, atomic, distributed
across workers/instances) — a per-route FastAPI dependency, not global
middleware, so different routes (a cheap read vs. an LLM call) get
different limits. `/health` is deliberately exempt. Supabase Auth's own
abuse protection on signup/login/OAuth is a separate, dashboard-configured
concern — this only covers our own FastAPI endpoints.

See **[`RATE_LIMITING.md`](./RATE_LIMITING.md)** for the full picture:
configured limits per category, the atomic Lua-script algorithm and why it
was chosen, client-IP/trusted-proxy handling, fail-open vs. fail-closed
behavior on Redis failure, and how to run the rate-limit test suite
locally.

## Adding a feature

1. `schemas/<feature>.py` — request/response models
2. `services/<feature>_service.py` — the logic
3. `api/v1/routes/<feature>.py` — thin route calling the service
4. Register the router in `api/v1/router.py`
5. Add the path to `frontend/src/services/api/endpoints.js`
6. Point the frontend service module at the new endpoint

## Error contract

Every error returns the same envelope, which
`frontend/src/services/api/client.js` already parses:

```json
{ "code": "not_found", "detail": "…", "request_id": "…" }
```
