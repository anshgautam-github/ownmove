# Marketeam

AI-powered career platform — discover internships, programs, hackathons and
open-source opportunities, matched to your profile.

## Architecture

Three independent pieces, each with one clear responsibility:

```
ALTRABRAOZ/
├── frontend/    React 19 + Vite SPA      — UI only
├── backend/     FastAPI                  — business logic + AI
└── supabase/    SQL (version-controlled) — schema, RLS policies, seeds
```

### Responsibility boundaries

| Concern | Owner |
| --- | --- |
| UI, components, pages, hooks, client state | **frontend** |
| Business rules, AI, embeddings, vector search, background jobs | **backend** |
| Postgres, Auth (Google OAuth), Storage, Row Level Security | **Supabase** |

The frontend never contains business logic. The backend never renders. Supabase
is infrastructure, not an application layer.

### Request flow

```
Browser ──JWT──> FastAPI ──user JWT / service-role──> Supabase (Postgres + RLS)
   │                 │
   │                 └──> LLM providers, embeddings, vector search
   └──────────────────────> Supabase Auth (Google OAuth)
```

Supabase Auth issues the JWT. The browser forwards it to FastAPI as a bearer
token; FastAPI verifies it against the Supabase JWT secret. **Supabase remains
the single identity provider** — FastAPI never issues its own tokens.

### Current migration status

Data access still goes **directly** from the browser to Supabase
(`frontend/src/services/supabase/*`), secured by Row Level Security. This is
intentional and works today.

The FastAPI backend is **scaffolded but not implemented** — every route returns
`501 Not Implemented`. As each capability lands, the corresponding call moves
from `services/supabase/` to `services/api/`, one endpoint at a time, with no UI
changes required. `frontend/src/services/api/client.js` is the seam this happens
through.

## Getting started

### Frontend

```bash
cd frontend
npm install
cp .env.example .env     # fill in your Supabase project values
npm run dev              # http://localhost:5173
```

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env     # fill in Supabase URL / keys / JWT secret
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

### Database

Run the SQL in order against your Supabase project (SQL Editor or Supabase CLI):

```
supabase/schema/    001 → 003   tables and indexes
supabase/policies/  001         Row Level Security  (required — see note)
supabase/seeds/     001         sample opportunities (safe to re-run)
```

> **RLS is the actual security boundary.** The browser holds only the anon key
> and queries Postgres directly, so any table without a policy is effectively
> public. Never disable RLS on these tables.

## Documentation

- [`frontend/README.md`](frontend/README.md) — frontend structure, conventions, OAuth setup
- [`backend/README.md`](backend/README.md) — backend architecture, how to add a feature
- [`supabase/README.md`](supabase/README.md) — schema, policies, migration workflow
