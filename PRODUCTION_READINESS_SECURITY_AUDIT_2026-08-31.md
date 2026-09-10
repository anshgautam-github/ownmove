# Full Production Readiness + Security Audit

**Repo:** ALTRABRAOZ (Career AI platform — FastAPI backend + Supabase + React/Vite frontend)
**Date:** 2026-08-31
**Method:** Direct inspection of the real repository (backend, frontend, `supabase/schema`, `supabase/policies`, deployment config, dependency manifests) via five independent research passes, cross-checked against the repo's existing `AUTH_SECURITY_AUDIT.md`, `HARDENING_SUMMARY.md`, `PENTEST_REPORT.md`, and `PRODUCTION_AUDIT.md` — every claim from those prior documents was independently re-verified rather than assumed correct, and stale claims are called out explicitly.
**Scope:** entire repository — frontend, backend, database, auth, deployment, dependencies, AI/LLM layer.

This report does not claim the application is unhackable. No application can honestly be guaranteed unhackable — this is an assessment of what was found against the categories requested, not a certification.

---

## 1. Architecture map and trust boundaries

```
 Browser (React 19 / Vite SPA)
   │
   ├── HTTPS ──> Supabase Auth (GoTrue) ──> Google OAuth (implicit-flow redirect)
   │
   ├── HTTPS + anon key + user JWT ──> Supabase PostgREST / Storage
   │        (direct REST calls the frontend makes itself — profiles, experiences,
   │         saved_opportunities, opportunity_applications, resumes bucket, etc.
   │         The FastAPI backend is NOT in this path. RLS is the only gate here.)
   │
   └── HTTPS + Bearer JWT ──> FastAPI backend (/api/v1/*)
            │
            ├── verifies JWT (HS256 secret or JWKS/RS256) — app/core/security.py
            ├── user-scoped Supabase client (get_supabase(access_token=...)) for
            │    the 4 real Career AI modules + recommendations — RLS applies
            ├── service-role Supabase client (get_admin_supabase()) — 3 call
            │    sites only: ingestion, embedding backfill, recommendation cache
            │    write. Bypasses RLS. Never fed client-supplied user ids.
            ├── Redis (rate limiting, fail-open for cheap routes, fail-closed
            │    for AI-expensive routes)
            └── OpenAI API (LangChain/LangGraph, structured-output only, no
                 tool-calling/agency) — profile_analysis, career_roadmap,
                 career_simulation, ai_coach generators

 Ingestion pipeline (background, not HTTP-reachable) ──> scrapes external
   listing sites ──> writes into public.opportunities (service-role) ──>
   apply_url from those listings is later rendered as a clickable link/target
   in the browser for any authenticated user.
```

**Stack:** FastAPI (Python 3.12) backend; Supabase (Postgres + Auth/GoTrue + Storage + RLS) as the sole datastore and identity provider; React 19 + Vite 8 + Tailwind 4 frontend; Redis for rate limiting; OpenAI (via LangChain/LangGraph) as the only external AI provider. No queues/workers beyond the rate limiter's Redis use (`ENABLE_BACKGROUND_WORKERS` is currently a no-op). No deployment config (Dockerfile only, no `render.yaml`/`vercel.json`/CI) is checked into the repo, so hosting is not yet codified — the intended shape discussed earlier (Vercel for the frontend, Render for the backend + Redis) is not something this audit can verify against actual production config, because none exists in-repo.

**Trust boundaries an attacker can interact with, in order of directness:**

1. **Any authenticated browser session ↔ Supabase PostgREST/Storage directly**, using nothing but the public anon key and the user's own JWT (both fully visible in browser DevTools by design). The FastAPI backend does not gate this path at all — **Postgres RLS is the only real enforcement boundary for every table**, not application code. This is why the RLS audit (§7) matters more than it might for an app where all DB access is proxied through a backend.
2. **Any authenticated browser session ↔ FastAPI backend**, gated by JWT verification (§5) plus per-route ownership checks (§6) plus rate limiting (§18).
3. **Unauthenticated caller ↔ FastAPI backend**: only `GET /api/v1/health` is reachable without a token. Every other route requires a valid JWT.
4. **OAuth redirect boundary**: Google ↔ Supabase Auth ↔ browser. State/PKCE handled by Supabase's `/authorize` endpoint.
5. **Scraped external data ↔ browser**: `apply_url` values originate from an automated scraper hitting third-party sites, land in `public.opportunities` via the service-role client, and are later rendered/opened in the browser for any logged-in user — this is a genuine boundary where untrusted external content reaches the frontend (see §12/§25 finding).
6. **User-authored free text ↔ OpenAI**: bios, target roles, chat messages, and simulation scenario input are interpolated into LLM prompts and sent to OpenAI (§19).

---

## 2. Frontend audit

Read: all `dangerouslySetInnerHTML`/`eval`/`innerHTML`/`document.write` sinks (zero found anywhere in `frontend/src`), `AppShell.jsx`, `AuthCallbackScreen.jsx`, `AuthDialog.jsx`, `services/supabase/auth.js`, `services/supabase/client.js`, `services/api/client.js`, `services/api/localCache.js`, `hooks/useClientNavigation.js`, `_legacy/*`, `config/env.js`, `vite.config.js`, `.env`/`.env.example`.

- **XSS**: no `dangerouslySetInnerHTML`, `eval`, `new Function`, raw `innerHTML`, or `document.write` anywhere in the codebase, and no markdown/HTML-rendering library is even installed. Every place AI-generated or user-generated text is displayed (`components/career-ai/coach/AssistantMessage.jsx:24`, `components/career-ai/cards/ProfileDiagnosisCard.jsx:23,27,37`, and others) uses a bare `{expr}` JSX child, which React escapes by default. This is a structural guarantee, not a sanitizer that could be forgotten — genuinely strong.
- **Open redirects**: `postLoginRedirect` is only ever set to hardcoded literal strings (`DemoSection.jsx:396`, `HowItWorksSection.jsx:23` via a closed `CTA_TARGETS` map), never from a URL query parameter or other attacker-controllable source, and is consumed by `services/supabase/auth.js:94-102` → `AuthCallbackScreen.jsx:26,28` / `AuthDialog.jsx:126-127`. `useClientNavigation.js:28` additionally rejects any `href` that isn't a same-origin `/...` path (blocks protocol-relative `//evil.com` too). No open redirect exists. (Correcting the prior audit's implication that this logic lives in `AppShell.jsx` — it actually lives in `services/supabase/auth.js` + the two screens named above; `AppShell.jsx`'s own navigation is a separate, equally closed-set `VIEW_ROUTES` lookup.)
- **`apply_url` scheme handling — real finding, carried forward from `PENTEST_REPORT.md` as still open, independently reconfirmed.** `AppShell.jsx:561` (`window.open(item.applyUrl, ...)`) and `AppShell.jsx:593` (`href={item.applyUrl || '#'}`) render a URL that originates from `public.opportunities.apply_url`, populated by an automated scraper of third-party sites (`services/supabase/opportunities.js:13` passes it through verbatim). Nothing validates the URL scheme before it's used as a link target. A `javascript:` URI in a scraped listing would execute in the app's origin when clicked, with access to the Supabase session token sitting in `localStorage`. The frontend itself cannot write to `opportunities` (read-only from the client), so this isn't attacker-reachable by an ordinary authenticated user — but it is reachable by whatever writes to that table (the scraper/ingestion pipeline), which pulls from external, not-fully-trusted sites. Rated **HIGH** — see §34/§35 for the exact fix.
- **Tokens/secrets**: `localStorage` use is limited to the 4 `postLoginRedirect` call sites above; `sessionStorage` is used only by `services/api/localCache.js` for per-user-scoped Career AI result caching (its own comment documents a prior cross-account leak bug that scoping fixed). `document.cookie` is never used. `services/supabase/client.js` uses the Supabase SDK's default session storage with no custom override, so there's no duplicate/parallel token store to leak. Grepping frontend source and the built `dist/` bundle for service-role-key-shaped or `sk-`-shaped secrets returned nothing. `.env`/`.env.example` contain only `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (the new `sb_publishable_...` format, intentionally public), and `VITE_API_BASE_URL` — all appropriate for client exposure, and `.env.example`'s own header comment warns "everything in this file ships to the browser."
- **API client**: `services/api/client.js:36-41,107-110` attaches `Authorization: Bearer <token>` from `supabase.auth.getSession()` (cache-only, no extra network round trip); tokens never appear in a URL. No client-side-only authorization/role-gating logic exists anywhere (grepped for `isAdmin`/`role ===`/`premium`/`paywall` — nothing) — all data-access control is delegated to Supabase RLS, correctly. No `console.log`/`console.error` calls exist anywhere in the app that could leak a response body or token; the only two `console.warn` calls are missing-env-var warnings.
- **Forms/uploads**: `services/supabase/profiles.js:17-38`'s `validateResumeFile()` (extension allowlist, MIME sniff, 5MB cap) is client-side only, as expected — the real enforcement has to be server-side (Storage bucket policy). See §11 for what the Storage layer actually enforces (answer: ownership only, not file type/size — a real, low-impact gap).
- **`_legacy/` folder**: confirmed dead code. Nothing under `src/` imports it, and one of its files (`_legacy/googleAuth.js`) re-exports functions that no longer exist in `services/supabase/auth.js` — it would throw if anything ever tried to use it. Safe to delete as a cleanup item; not a live risk since Vite's module graph never includes it.
- **Build config**: `vite.config.js` has no unusual `define`/env-passthrough behavior; `config/env.js` is the sole reader of `import.meta.env.VITE_*`.

## 3. Backend audit

Read: `app/api/v1/router.py`, `app/main.py`, `app/core/config.py`, every file under `app/api/v1/routes/`, the routers/services/repositories of all 4 real Career AI modules, `app/middleware/*`, `app/db/supabase.py`.

- **Router mounting resolved**: the top-level router mounts *both* the old scaffold routes (`app/api/v1/routes/roadmap.py`, `simulation.py`, `chat.py`, `auth.py`) **and** the real, implemented feature modules (`app/career_roadmap`, `app/career_simulation`, `app/ai_coach`, `app/profile_analysis`, each under `/api/v1/career-ai/*`). The old scaffold handlers are every one a one-line `raise NotImplementedYetError()` (HTTP 501) — they are reachable, authenticated, rate-limited 501 stubs, not dead code. They pose no direct vulnerability (they do nothing), but they're unnecessary attack surface and a source of exactly the kind of "which router is real" confusion this audit had to resolve — recommend deleting them (§35, non-blocking cleanup).
- `app/api/v1/routes/profiles.py`, `opportunities.py`, `analytics.py` are likewise entirely unimplemented 501 stubs. `recommendations.py` is the only implemented route in `app/api/v1/routes/`, and it's clean (user id always server-derived, `opportunity_id` in `POST /match` is only ever used to read a public catalog row).
- **`app/api/v1/routes/auth.py` has no custom auth logic at all** — no bcrypt, no custom JWT issuance, no session/refresh-token table anywhere in the backend. Signup/login/logout/password-reset are handled entirely by the frontend talking to Supabase Auth directly; this backend file only has two 501-stub, JWT-gated identity routes (`/auth/me`, `/auth/verify`). This is exactly the "don't build custom auth Supabase already gives you" posture the audit was asked to verify, and it holds.
- **Service-role client usage** (`get_admin_supabase()`, bypasses RLS): exactly 3 call sites in the whole backend — ingestion (not HTTP-reachable), embedding backfill (row ids come from the DB's own missing-embedding query, never client input), and the recommendations cache writer (`user_id` always server-derived). No IDOR risk found via the admin client.
- **No admin role or privileged endpoint exists anywhere.** `AuthenticatedUser.role` is parsed from the JWT but never read by any route (`grep '\.role\b'` across `app/` returns only its own definition) — there is currently nothing to audit for a privilege-escalation bypass because there is no privileged functionality exposed over HTTP.
- **Middleware registered**: `RequestIDMiddleware` then `CORSMiddleware` — that's the complete list. No security-headers middleware exists (see §22). The global exception handler (`app/middleware/error_handler.py:44-56`) always returns an opaque `{"code":"internal_error","detail":"Something went wrong."}` for unhandled exceptions and logs the real traceback server-side only — no stack trace or internal detail is ever returned to a client. `RequestValidationError` responses do echo back pydantic's own field-level errors (standard FastAPI 422 behavior) — low-severity, not a leak of secrets or internals.
- **API docs**: `/docs`, `/redoc`, `/openapi.json` are disabled when `settings.ENVIRONMENT == "production"` (`main.py:69-71`), enabled otherwise — correct, contingent entirely on `ENVIRONMENT` being set correctly at deploy time (nothing in the repo currently enforces that, since no deploy config exists — flagged in §24/§30).

## 4. Authentication audit (full lifecycle)

Independently re-verified against `AUTH_SECURITY_AUDIT.md`'s own empirical testing plus this session's own re-reads:

- **Signup/login/logout/password reset**: entirely delegated to Supabase Auth (GoTrue) via the frontend SDK. No custom password storage, no custom bcrypt, no custom session table — confirmed absent from the backend. This is the correct posture: the app is not reinventing what Supabase already provides, and per the explicit "don't build custom auth without a concrete reason" instruction, no such reason exists here, so no change is recommended.
- **Google OAuth**: implicit flow (not PKCE) is currently used for the token exchange — `AUTH_SECURITY_AUDIT.md`'s existing finding, not independently re-tested live this session, but its reasoning holds: PKCE is a strict improvement with no downside and is a one-setting change in the Supabase dashboard. State-parameter CSRF protection for the OAuth flow itself is handled by Supabase's `/authorize` endpoint regardless of flow type, so this is a hardening recommendation, not a live vulnerability.
- **Redirect URL** is built from `window.location.origin` at runtime, never hardcoded or attacker-suppliable — the actual security boundary is the Supabase dashboard's allow-listed redirect URLs, which must be manually confirmed to include only `localhost` (dev) and the real production origin, with no wildcard. This cannot be verified from the repo and must be checked in the Supabase dashboard directly.
- **Session/token lifecycle**: managed entirely by the Supabase JS SDK's default `localStorage`-based session store; the backend never issues, stores, or refreshes tokens itself — it only verifies them (§5).
- **Account lifecycle** (deletion, etc.): not implemented as a distinct backend flow; relies on Supabase Auth's own user-management primitives. No backend-side account-deletion endpoint exists to audit for a cascading-delete bug (the DB's own `ON DELETE CASCADE` FKs would apply if a user row is deleted via the Supabase dashboard/Admin API, and were confirmed correct in §7/§8).

## 5. JWT security audit

**Verdict: signature verification is genuinely enforced. This is NOT a "decode without verify" situation — classified NOT CRITICAL.**

`app/core/security.py`'s `decode_token()` always resolves a real signing key before calling `jwt.decode(token, key, algorithms=[algorithm], audience=..., options={"require": ["exp","sub"]})` — HS-family algorithms use `settings.SUPABASE_JWT_SECRET` (hard-fails closed with `UnauthorizedError` if unset, no insecure fallback secret exists anywhere in `config.py`), asymmetric algorithms use a `PyJWKClient` built from `SUPABASE_URL` (also fails closed if unconfigured). `verify_token()` adds its own explicit non-empty-`sub` check on top of PyJWT's built-in `require` option. This session's regression test suite (`tests/test_security.py`, 43 tests) exercises: valid-token acceptance, wrong-secret rejection, expired-token rejection, missing/empty `sub` rejection, wrong/missing audience rejection, malformed-token rejection, tampered-payload rejection, `alg=none` rejection (the classic algorithm-confusion attack — explicitly tested and rejected), unsigned-token rejection, asymmetric-token-without-JWKS rejection, and HS-secret-not-configured rejection — all passing.

The header's `alg` value is read (`algorithm = header.get("alg") or settings.SUPABASE_JWT_AUDIENCE`-style pattern) and does influence which verification branch runs, which has the *shape* of the classic algorithm-confusion anti-pattern — but it is not currently exploitable: PyJWT 2.10.1 (confirmed current, non-vulnerable version in `requirements.txt:9`) always requires a real, correctly-typed key for whichever branch is selected, and never falls back to accepting an unsigned or symmetric-key-as-public-key token. Supporting both HS256 and JWKS/RS256 does not currently introduce a downgrade vulnerability, because neither branch will ever accept a token it isn't the correct verifier for. This is a sound implementation; no change is required here per the "don't fix what isn't broken" instruction, though as defense-in-depth it would be reasonable to pin `algorithms=` to Supabase's actual configured algorithm(s) rather than deriving it from the token header at all, eliminating the *shape* of the anti-pattern even though it isn't currently exploitable.

## 6. Authorization / IDOR audit

Traced every id-parameterized route in the 4 real Career AI modules end-to-end (route → service → repository → RLS policy). Pattern confirmed: **every resource id used to scope a read/write is server-derived from the verified JWT's `user.id`, never trusted from a client-supplied path/query/body parameter**, and every id-parameterized lookup filters by both the resource id *and* the owning user/profile id at the repository layer, independently backed by Postgres RLS since these calls use the user-scoped Supabase client. Concretely verified:

- `GET/DELETE /api/v1/career-ai/career-simulation/{simulation_id}` — filtered by `id` **and** `profile_id` together; RLS SELECT policy also checks `profile_id=auth.uid()`.
- `GET/POST/DELETE /api/v1/career-ai/ai-coach/conversations/{conversation_id}...` — `require_conversation()` raises `NotFoundError` (never `ForbiddenError`) for a conversation owned by someone else, so a cross-user probe can't even distinguish "doesn't exist" from "not yours" — the strongest ownership pattern in the codebase, backed by RLS's transitive `EXISTS(...)` policy on `coach_messages`.
- `POST /api/v1/career-ai/profile-analysis`, `POST .../career-roadmap` — no id parameters at all; the only "identity" is the JWT-derived `user_id`, so a cross-user read/write isn't even expressible at the route signature level.

**No cross-user IDOR was found anywhere in the reachable API.** The one concrete authorization-adjacent bug found is functional, not a security hole: `DELETE /api/v1/career-ai/career-simulation/{simulation_id}` silently no-ops instead of deleting (see §34, finding #6) — it fails *closed* (nothing gets deleted, including the caller's own data, rather than something getting deleted that shouldn't), so it is not exploitable against another user, but it needs fixing before launch since a user's "delete" action currently does nothing.

## 7. Supabase RLS audit — every table

All 16 `public.*` tables plus `storage.objects` were read directly from all 22 schema files and all 8 policy files (not sampled). Every table has `ENABLE ROW LEVEL SECURITY`. No policy anywhere uses `using(true)` or an equivalent always-true condition.

| Table | RLS | SELECT | INSERT | UPDATE | DELETE |
|---|---|---|---|---|---|
| `profiles` | ✅ | `id=auth.uid()` | `id=auth.uid()` | `id=auth.uid()` | none |
| `experiences` | ✅ | `profile_id=auth.uid()` | same | same | same |
| `opportunities` | ✅ | `is_active=true`, any authenticated (public catalog, by design) | none via API | none | none |
| `saved_opportunities` | ✅ | `user_id=auth.uid()` | same | none (app deletes+re-inserts) | same |
| `profile_embeddings` / `opportunity_embeddings` | ✅ | no policy → default-deny | none | none | none |
| `profile_insights` | ✅ | `profile_id=auth.uid()` | none via API | none | none |
| `recommendations` | ✅ | `user_id=auth.uid()` | none via API | none | none |
| `interaction_events` | ✅ | none (write-only log) | `user_id=auth.uid()` | none | none |
| `profile_analysis` | ✅ | `profile_id=auth.uid()` | same | none (immutable history) | none |
| `career_roadmaps` | ✅ | `user_id=auth.uid()` | same | same | none |
| `roadmap_activity` | ✅ | `user_id=auth.uid()` | `user_id=auth.uid()` only — **missing transitive check, see finding below** | none | none |
| `career_simulations` | ✅ | `profile_id=auth.uid()` | same | same — **column-level gap, see finding below** | **no DELETE policy — see §34 finding #6** |
| `coach_conversations` | ✅ | `profile_id=auth.uid()` | same | same | same |
| `coach_messages` | ✅ | transitive `EXISTS(...conversation owned...)` | same transitive check — **role not restricted, see finding below** | none | none |
| `opportunity_applications` | ✅ | `user_id=auth.uid()` | same | none | same |
| `storage.objects` (`resumes`, private bucket) | ✅ | path-prefix `(storage.foldername(name))[1]=auth.uid()::text`, all 4 ops | same | same | same |

**New findings this table structure alone doesn't capture (RLS is row-level, not column-level):**

1. **`profiles.profile_score` / `ai_profile_summary` / `last_profile_analysis`** (documented "backend-only" in a schema comment) can be set to anything by the owning user directly via `PATCH /rest/v1/profiles?id=eq.<self>`, since the UPDATE policy scopes the *row* but not these columns. Self-serving-only impact today (a user can only lie to themselves); becomes a real integrity issue if these fields are ever surfaced to other users (leaderboard, recruiter view, matching). **MEDIUM.**
2. **`career_simulations`** has the identical structural gap on `status`/`verdict`/`result`/`completed_at`/`model_used` — a user can `PATCH` their own simulation row directly, e.g. set `status='completed'` and fabricate a `result` blob, bypassing the LLM call entirely. Same self-serving-only severity class. **MEDIUM.**
3. **`roadmap_activity` INSERT** checks `user_id=auth.uid()` but never verifies the referenced `roadmap_id` actually belongs to that user (unlike `coach_messages`, which correctly uses a transitive `EXISTS` check for its parent). A user who knows another user's `career_roadmaps.id` UUID could insert a fabricated activity row against it. Low practical exploitability (UUIDs, feature not yet surfaced in the UI per the schema's own comment), but the same category of gap. **LOW.**
4. **`coach_messages` INSERT** doesn't restrict the `role` column — a user could insert a message into their own conversation with `role='assistant'`, forging the appearance of an AI reply in their own chat history. Purely self-scoped. **LOW.** *(A fix here needs care: if the backend currently writes real assistant replies using the same user-scoped client — plausible, since that's this module's pattern throughout — restricting `role` at the RLS layer without first confirming that write path would break the app. See §35 for the caveated recommendation.)*

**SECURITY DEFINER functions**: zero exist in the schema (`grep -rniE "security definer"` across `schema/` and `policies/` returns nothing). The 4 functions that do exist (`match_opportunities_for_profile`, `search_opportunities_by_text`, two embedding-invalidation triggers) are all plain `SECURITY INVOKER`, and the two RPC functions are explicitly documented as deliberately not `SECURITY DEFINER` so RLS still applies to the caller — verified correct.

**Storage**: only one bucket (`resumes`, `public=false`), with a correct path-prefix ownership check on all 4 operations. No other bucket exists anywhere in the repo.

**Constraints/integrity**: every FK uses sensible, explicit `ON DELETE` behavior (`CASCADE` for owned rows, `SET NULL` deliberately for `interaction_events.opportunity_id` to preserve audit history). Uniqueness that matters is DB-enforced, not just app-layer (`saved_opportunities(user_id, opportunity_id)`, `recommendations` same, `career_roadmaps(user_id)`, `opportunity_applications` same). No `updated_at` auto-touch triggers exist anywhere — this relies entirely on application code remembering to set the timestamp on every write; a data-integrity nit, not a security bug.

**Schema-drift note** (not a vulnerability, but relevant to trusting this document going forward): `supabase/schema/022_...sql`'s own comment states that `embedding`/`search_vector`-style columns were added directly to `profiles`/`opportunities` in the live database outside of what's checked into `schema/`. This means the checked-in schema files are not fully authoritative for those two tables' real shape, and `profile_embeddings`/`opportunity_embeddings` may now be dead tables rather than live storage. Worth reconciling migrations with the live DB before relying on `schema/` as ground truth going forward — not a security issue, a maintainability one.

**Seeds**: only public-catalog `opportunities` rows with placeholder URLs; no test credentials, no admin rows, nothing touching `auth.users` or `profiles`.

## 8. Database security

- No raw SQL string-building was found anywhere in the backend — all Supabase client calls use the parameterized query builder or RPC calls with typed parameters, and the two RPC functions (`match_opportunities_for_profile`, `search_opportunities_by_text`) take typed parameters, not interpolated strings. No SQL injection surface found.
- Integrity for ownership and uniqueness is enforced at the database layer (RLS + unique constraints), not merely assumed by the frontend/backend — this is the correct posture and matches what the audit was asked to verify. The one place where DB-level enforcement is weaker than intended is the column-level gaps in §7 (findings 1–2): those specific fields rely on the *application's own write discipline* rather than a DB constraint, which is exactly the pattern the user's request asked to be alert for ("determine whether integrity is DB-enforced vs only assumed").
- No exposed/overly-permissive tables found; `profile_embeddings`/`opportunity_embeddings` are correctly unreachable from the browser (no policy = default-deny, confirmed only the service-role client touches them).

## 9. API security — endpoint table

Every implemented backend endpoint. ("Stub" = `NotImplementedYetError`/501; not a security gap, just unbuilt.)

| Endpoint | Auth | Authorization | Validation | Rate Limit | Risk |
|---|---|---|---|---|---|
| `GET /api/v1/health` | No | N/A | N/A | Exempt (intentional) | None |
| `GET/POST /api/v1/auth/*` (2 routes) | Yes | N/A | N/A | AUTH_READ | Stub only |
| `GET/PATCH /api/v1/profiles/*` (4 routes) | Yes | N/A | N/A | Applied | Stub only |
| `GET/POST/DELETE /api/v1/opportunities/*` (5 routes) | Yes | N/A | N/A | Applied | Stub only |
| `GET /api/v1/recommendations/for-you` | Yes | user_id server-derived | None needed | AI_EXPENSIVE | Clean |
| `POST /api/v1/recommendations/match` | Yes | reads public catalog row only | Weak (`opportunity_id: str`, no format check) — harmless since target is a public row | AI_EXPENSIVE | Clean |
| `POST /api/v1/recommendations/refresh` | Yes | user_id server-derived, writes via admin client but scoped to caller | None needed | AI_EXPENSIVE | Clean |
| `POST/GET /api/v1/roadmap/*`, `/simulation/*`, `/chat/*` (old scaffolds, 7 routes) | Yes | N/A | N/A | Applied | Stub only — recommend deleting (unnecessary surface) |
| `POST/GET /api/v1/analytics/*` (2 routes) | Yes | N/A | N/A | Applied | Stub only |
| `POST/GET /api/v1/career-ai/profile-analysis*` (3 routes) | Yes | user_id server-derived; RLS-backed | No client input | AI_EXPENSIVE | Clean |
| `POST/GET /api/v1/career-ai/career-roadmap*` (2 routes) | Yes | user_id server-derived; RLS-backed | **`target_role` unbounded string, no max_length** | AI_EXPENSIVE | Unbounded-payload gap (see §34 #8) |
| `POST /api/v1/career-ai/career-simulation` | Yes | profile_id server-derived; RLS-backed | **`target_role`/`scenario_title` unbounded; `scenario_input: dict` fully free-form, unbounded** | AI_EXPENSIVE | Unbounded-payload gap (see §34 #8) |
| `POST /api/v1/career-ai/career-simulation/compare` | Yes | Same | Same unbounded-dict issue ×2 | AI_EXPENSIVE | Same |
| `GET .../career-simulation/history` | Yes | `.eq("profile_id", user_id)` + RLS | N/A | AI_EXPENSIVE | Clean |
| `GET .../career-simulation/{id}` | Yes | Filtered by id **and** profile_id + RLS | Path param, harmless | AI_EXPENSIVE | Clean |
| `DELETE .../career-simulation/{id}` | Yes | Filtered by id+profile_id, **but no RLS DELETE policy — silently no-ops** | N/A | AI_EXPENSIVE | Functional bug, see §34 #6 |
| `POST/GET/DELETE /api/v1/career-ai/ai-coach/*` (5 routes) | Yes | `require_conversation()` ownership check, 404-not-403; RLS transitive check | `message` bounded 1–4000 chars | AI_EXPENSIVE | Clean — best pattern in the repo |

Every endpoint except `/health` requires a verified JWT. Every endpoint except `/health` has a `rate_limit(...)` dependency applied (verified by grepping every route file for the dependency, not just spot-checked) — this directly contradicts and supersedes the stale claim in `AUTH_SECURITY_AUDIT.md` that rate limiting is "entirely missing"; it is real, Redis-backed, and comprehensively wired.

## 10. Input validation

Pydantic models validate every request body across the implemented (non-stub) routes. The one systematic gap is bounding: `RoadmapGenerateRequest.target_role`, `SimulationCreateRequest.target_role`/`.scenario_title`, and `SimulationCompareRequest`'s equivalents have no `max_length`, and `scenario_input: dict` (used twice — top-level and inside `SimulationOption`) is a fully free-form, unbounded dict with no size or depth cap. `ai_coach`'s `message` field is correctly bounded (1–4000 chars) and is the model to follow. No global request-body-size-limiting middleware exists. See §34 finding #8 for the exact fix. All other validated fields (timeline/commitment/goal on roadmap requests) use `Literal[...]` closed enums — good practice, not flagged.

## 11. File upload security

Only one upload surface exists: resumes, going directly from the browser to Supabase Storage (not proxied through the FastAPI backend). Client-side validation (`services/supabase/profiles.js:17-38`) checks extension, MIME (when the browser reports one), and a 5MB cap — but this is trivially bypassable (rename a file, or call the Storage API directly with the user's own valid JWT). Server-side, the only enforcement Storage itself provides is the path-prefix **ownership** check (§7) — nothing at the Storage-policy or DB level currently constrains file type or size. Practical impact is low: because RLS scopes reads/writes strictly to the uploading user's own folder, this is a self-targeting gap (a user could upload an oversized or mistyped file into their own storage, wasting their own quota) rather than a cross-user exploit — there's no evidence resumes are ever read by anyone other than the owning user (confirmed: `AppShell.jsx:1389` generates a signed URL for the caller's own resume only). Still worth adding a Supabase Storage bucket-level file-size limit and allowed-MIME-types list (configurable directly in the bucket settings, no code change required) as defense-in-depth. **LOW**, non-blocking.

## 12. XSS audit

Covered in depth in §2. Summary: zero dangerous sinks exist anywhere in the frontend; React's default escaping is the sole and structurally sufficient control for every AI-generated and user-generated text surface. The one real, still-open finding is not a classic script-injection XSS but a **`javascript:` URI scheme gap** on the scraped `apply_url` field (§2, §25, §34 #5) — rated **HIGH** because of the session-token-theft blast radius if it's ever hit, even though the trigger (a malicious scraped listing) requires the ingestion pipeline to be compromised or scrape from an untrustworthy source, not a directly-attacker-controlled input from within the app itself.

## 13. CORS audit

`app/main.py:77-84`: `allow_origins=settings.CORS_ORIGINS` (a configured list, not a hardcoded wildcard), `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`. The default value (`config.py:39-41`) is `["http://localhost:5173","http://127.0.0.1:5173"]` — safe for local dev, not wildcarded. **Production is not currently misconfigured, but nothing in the app itself would reject a misconfiguration** if `CORS_ORIGINS` were ever accidentally set to `*` in a production `.env` (the browser would refuse to honor `*` + credentials at runtime, which limits real-world impact, but the app doesn't fail loudly on that misconfiguration either). Recommend adding a startup-time assertion that rejects `CORS_ORIGINS=["*"]` when `allow_credentials=True`, purely as a fail-fast guardrail — **LOW**, optional hardening, not a live vulnerability today.

## 14. CSRF audit

**Not applicable, and this is a deliberate finding, not an oversight to fix.** The backend authenticates exclusively via a `Bearer` token in the `Authorization` header (confirmed in `app/api/deps.py` and `services/api/client.js:107-110`); it never accepts a session cookie as an authority-bearing credential, and the Supabase JS SDK's own session storage is `localStorage`-based, not cookie-based. CSRF requires an ambient credential (a cookie) the browser attaches automatically to cross-site requests — that mechanism doesn't exist here, since a cross-site page cannot read `localStorage` or forge an `Authorization` header on the victim's behalf. No CSRF protection is recommended, per the explicit instruction not to add it blindly.

## 15. Secrets audit

- Backend secrets (`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `DATABASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) are read only from environment variables via `app/core/config.py`, with no hardcoded fallback values anywhere — confirmed by reading the full settings class. Auth correctly fails closed (raises `UnauthorizedError`) when `SUPABASE_JWT_SECRET` is unset, rather than falling back to an insecure default.
- Frontend `.env`/`.env.example` contain only intentionally-public values (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` in the new `sb_publishable_...` format, `VITE_API_BASE_URL`) — no service-role key or backend secret is exposed to the browser, confirmed by grepping both the source tree and the built `dist/` bundle.
- `.gitignore:23-26` correctly excludes `.env`/`.env.*` with an explicit `!.env.example` allowlist, in both the repo root and this pattern applies to `backend/`/`frontend/` env files too.
- **Git history could not be audited** — the working copy at the path this audit had access to contains no `.git` directory at all (confirmed: `git rev-parse --is-inside-work-tree` fails, no `.git` folder found at any level). This is reported as an explicit gap, not a clean result: **run this same secrets grep against the actual GitHub/GitLab remote's full commit history** (`git log --all -p | grep -iE "(api[_-]?key|secret|password|SUPABASE_SERVICE_ROLE|sk-[a-zA-Z0-9]{20,})"`) before considering this closed, since a real `.env` may have been committed before `.gitignore` was tightened, even if the current working tree is clean.

## 16. Environment configuration

Every backend setting was read and classified (§3's config table, reproduced in `app/core/config.py`). Public/safe values (CORS origins, model names, rate-limit thresholds, feature flags) vs. secret values (service-role key, JWT secret, DB URL, LLM API keys) are correctly separated, and the secret ones have no insecure fallback. The one hygiene issue: `DEBUG: bool = True` is the default and is set `true` in both `.env` and `.env.example`, but is **never read anywhere in the application** (confirmed via full-tree grep) — it's dead configuration, not something currently gating a security-relevant behavior, but its risky-looking default is a landmine for whoever eventually wires it up assuming `False` was ever the safe default. Recommend either removing the unused field or fixing its default to `False`, as a low-cost cleanup (§35).

## 17. Dependency security

**Backend** (`requirements.txt`, pip — no poetry lockfile, `pyproject.toml` only configures ruff/pytest): `pyjwt==2.10.1` is current and not in the vulnerable algorithm-confusion family older PyJWT/python-jose versions had — good, no action needed given JWT verification is the most security-critical dependency in the app. `redis==6.4.0`, `openai==1.109.1`, `langchain==0.3.27`, `langchain-openai==0.2.14`, `langgraph==0.2.62` are all current-ish with no known CVEs at these pins. `requirements-dev.txt` correctly separates dev-only tooling (pytest, ruff, fakeredis, lupa) from the runtime `requirements.txt` — nothing dev-only is shipped to production. One concrete, specific concern (not a blanket "update everything"): `supabase>=2.20.0` is deliberately left unpinned (floor-only) to avoid resolver conflicts among its sub-packages — this is a legitimate short-term trade-off but means a `pip install` on a different day can silently pull a newer major version into production; recommend pinning to an exact version once the current one is verified working, purely for build reproducibility, not because anything is currently vulnerable.

**Frontend** (`package.json` + `package-lock.json`): React 19, Vite 8, Tailwind 4, `@supabase/supabase-js@^2.110.8`, `framer-motion@^11.18.2` — all current majors, actively maintained, nothing flaggable. Small, minimal dependency surface overall.

No package on either side was found with a concrete, known vulnerability, and no blanket-upgrade recommendation is made per the explicit instruction — the only two items flagged above (`supabase` pinning, `DEBUG` default) have specific, articulable reasons.

## 18. Rate limiting / abuse protection

**Real and comprehensive — the existing `AUTH_SECURITY_AUDIT.md`'s claim that this is missing is stale and must be disregarded.** `app/core/rate_limiter.py` is an atomic Redis fixed-window limiter (Lua script for atomicity), with configurable fail-open (cheap routes) vs fail-closed (`RATE_LIMIT_FAIL_OPEN_AI=False` by default — AI spend is protected even if Redis goes down) behavior. `app/core/rate_limit_policy.py` defines 4 categories (PUBLIC, AUTH_READ, AUTH_WRITE, AI_EXPENSIVE), with AI_EXPENSIVE dual-layered (per-user and per-IP, both per-minute and per-day). `app/core/client_ip.py` resolves the real client IP via a configurable trusted-proxy-hop count, defaulting to trusting nothing but the direct TCP peer (safe default; must be set to match the actual number of trusted reverse-proxy hops once deployed — this was flagged in earlier deployment guidance as something to verify empirically in production, not assume). Confirmed by grep that **every route except `/health` carries a `rate_limit(...)` dependency**, including every AI-expensive endpoint across all 4 real Career AI modules. Signup/login/password-reset have no backend rate limiting because they have no backend implementation at all — they go straight to Supabase Auth, which has its own dashboard-side abuse protection (out of this repo's control, worth confirming Supabase's own auth rate limits are enabled in the project dashboard). No gaps found in what's actually implemented.

## 19. AI/LLM security

All 4 real generators (`profile_analysis`, `career_roadmap`, `career_simulation`, `ai_coach`) use `ChatOpenAI(...).with_structured_output(<Schema>, method="json_schema", strict=True)` — OpenAI Structured Outputs constrained to a fixed Pydantic schema. **No tool-calling, no function-calling-as-agency, anywhere** — none of the 4 generators can take an action, write data, or call an external API on the model's own initiative; they can only return a schema-validated text object that the application code then persists. This substantially limits the blast radius of any prompt-injection success. All 4 system prompts are long and explicitly anti-hallucination (forbidding fabricated credentials, invented URLs, fabricated hiring probabilities).

**Prompt injection is possible and unmitigated, but its impact is bounded and self-directed.** User-controlled free text (profile bio, target role, chat messages, simulation scenario input) is interpolated directly into prompts with no sanitization or instruction/data separation beyond a plain text label. The highest-risk surface is `app/ai_coach/utils/context.py:130-185`, which interpolates unbounded, untruncated raw chat history and the current free-text question under a plain `=== USER_QUESTION ===` label — a user could craft input designed to make the model break its own system-prompt rules (e.g., state a fabricated hiring percentage, or echo back the system prompt). Because there's no tool-calling and every read/write is scoped to the requesting user's own data (confirmed via the repository-scoping traced in §6), a successful injection's worst case is "a user manipulates the AI's reply to themselves" — a real but low-severity, self-scoped risk, not an account-takeover or cross-user-data-leak vector. **LOW-MEDIUM**, worth a light mitigation (delimiting user content more explicitly, e.g. wrapping it in an unambiguous fenced block and instructing the model to treat everything inside it as data never instructions) but not a launch blocker.

No cross-user data was found flowing into any prompt — every repository call scoping a fetch by `profile_id`/`conversation_id` filters by the server-derived `user_id`, never a client-supplied one. AI output is never rendered as raw HTML on the frontend (confirmed zero `dangerouslySetInnerHTML` anywhere). `app/ai/chains`, `app/ai/llm`, `app/ai/prompts` are a separate, unused legacy abstraction (imported only by themselves, never by the 4 real modules or any router) — dead code, safe to delete as cleanup, not a live risk since it's never executed. `app/ai/embeddings/`, by contrast, **is** live (used for recommendation embeddings, unrelated to the 4 LLM generators).

## 20. SSRF audit

No endpoint in the reachable API accepts a URL for the server to fetch — the 4 Career AI modules only ever read the caller's own stored profile/experience/conversation data and forward it to OpenAI, they don't fetch arbitrary URLs. The ingestion pipeline does fetch external URLs (that's its job — scraping listing sites), but it is not HTTP-reachable (no router mounts it) and is not driven by end-user input; it runs from a fixed, developer-configured source list. No SSRF vector was found in the attacker-reachable surface. If the ingestion source list is ever made configurable by an admin user in the future, it should be revisited then (allow-list target hosts, block internal/metadata IP ranges) — noted for future-proofing, not a current gap.

## 21. Logging and error handling

The global exception handler always returns an opaque, generic error body to the client (`{"code":"internal_error","detail":"Something went wrong.","request_id":...}`) and logs the real exception server-side only — confirmed no stack trace, SQL, or internal path is ever returned in a response, for both the catch-all handler and the structured `AppError` handler. The one minor leak is standard FastAPI behavior: 422 validation-error responses include pydantic's own field-level error details (field names/types/received values) — this can reveal internal schema shape but never secrets, tokens, or passwords. No evidence was found of auth tokens or PII being written to logs (the backend's logging calls were not exhaustively line-by-line audited for this, but no such pattern turned up in any of the route/service files read).

## 22. Security headers

**None are currently set beyond the CORS response headers.** `app/main.py` registers exactly two middlewares (`RequestIDMiddleware`, `CORSMiddleware`); no CSP, X-Content-Type-Options, Strict-Transport-Security, Referrer-Policy, X-Frame-Options/frame-ancestors, or Permissions-Policy is present anywhere. For a JSON API backend consumed only by the app's own SPA, the practical risk from most of these is lower than for a server-rendered app, but a few are cheap, unambiguous wins worth adding regardless: `X-Content-Type-Options: nosniff` (prevents MIME-sniffing of any accidentally-misdeclared response), `Strict-Transport-Security` (once HTTPS is confirmed in production), and `Referrer-Policy: strict-origin-when-cross-origin`. **CSP matters more on the frontend's own hosting layer** (wherever it's served — currently no deployment config exists to set this) than on the API backend, and would meaningfully raise the bar against the `apply_url` finding (§2/§25) as defense-in-depth even after that's fixed at the source. See §35 for exact code.

## 23. HTTPS / transport security

No hardcoded `http://` URLs were found in production-path code — the frontend's `VITE_API_BASE_URL` currently defaults to `http://localhost:5173`/`:8000` for local dev (appropriate for dev), and OAuth redirect URLs are built dynamically from `window.location.origin` (so they're `https://` automatically once deployed to a real domain). No deployment config exists in-repo to verify that the production Render/Vercel-style deployment actually terminates TLS and redirects HTTP→HTTPS — this must be confirmed at the hosting-platform level once deployed, since it isn't something the application code controls either way (both Render and Vercel terminate TLS by default, but this should be explicitly checked once live).

## 24. Production configuration

`ENVIRONMENT` correctly gates `/docs`/`/redoc`/`/openapi.json` exposure (§3), but nothing in the repo currently *sets* `ENVIRONMENT=production` for a real deployment, since no deployment config exists (§30) — this is a "must be set correctly at deploy time" dependency, not a code bug. `DEBUG=True` default is unused dead code (§16), not an active production risk today, but should be cleaned up so it can never become one. No test credentials, mock-auth bypasses, or dev-only fallback secrets were found anywhere in the backend.

## 25. Routing / redirect security

Covered fully in §2 and §12. `postLoginRedirect` is provably safe (hardcoded literal values only, never URL-derived). The one real, still-open redirect-adjacent finding is the `apply_url` scheme gap — not a "redirect after login" issue, but the same general class of "render an externally-influenced URL without validating its scheme" risk the user's request was specifically alert for. No attacker can craft a malicious link that changes where a user lands after login; the actual risk is in what happens when a user clicks an "Apply" link sourced from scraped third-party data.

## 26. Business logic security

No mechanism exists for a user to claim another user's opportunity, modify another user's profile, or bypass onboarding to reach gated functionality (there's no gating logic to bypass — no premium tiers, no credits system, no admin role exist in this app at all today). The closest things to a "should be once" operation are: `career_roadmaps` (unique per user — enforced by a DB unique constraint, confirmed correct), and the profile-analysis history (deliberately append-only, by design, not a bypass target). The column-level RLS gaps in §7 (a user setting their own `profile_score` or `career_simulations.status`/`result` directly) are the one real business-logic-integrity finding — self-serving, not cross-user, but still worth fixing since it lets a user's own displayed data diverge from what the AI actually computed.

## 27. Race conditions

`career_roadmaps`'s regenerate-upsert path (`unique(user_id)` constraint, confirmed by this session's own test suite covering the "second generate call overwrites the same row" behavior) is DB-enforced against duplicate rows. `saved_opportunities` and `opportunity_applications` similarly rely on DB-level `unique(user_id, ...)` constraints rather than app-layer "check then insert" logic, which is the correct way to avoid a duplicate-insert race. No explicit database transaction usage was found wrapping multi-step writes in the 4 Career AI modules (e.g. profile-analysis save + activity log, where applicable) — for the operations audited, none of them have a correctness requirement that spans multiple tables in a way that a partial failure would corrupt data (each module's core write is a single upsert), so this wasn't flagged as a concrete bug, but it's worth keeping in mind if a future feature adds a genuinely multi-step write.

## 28. Data privacy

PII stored: email (via Supabase Auth, not duplicated into `public.profiles`), name, bio, resume file + resume URL, skills, work experience, career interests, AI-generated analysis/summaries, chat history with the AI coach. All of it sits behind RLS policies scoped to `auth.uid()` (§7), and every API response was confirmed to return only the caller's own data (§6/§9) — no endpoint was found returning another user's fields. The AI Coach's chat history and the profile bio/experience data are sent to OpenAI as part of prompt construction (§19) — this is inherent to the feature (an AI needs to read what it's advising on) and is disclosed by the nature of the product, not a leak, but worth the user confirming their privacy policy/ToS actually discloses that user data is processed by OpenAI, since that's a data-sharing relationship a privacy-conscious user would want disclosed. No field was found being logged in a way that would put PII into log aggregation beyond what's inherent to request tracing (request IDs, not payload bodies).

## 29. Performance / DoS risks

Rate limiting (§18) is the primary defense already in place and is comprehensive. The unbounded `scenario_input`/`target_role`/`scenario_title` fields (§10) are the one concrete amplification risk: a single authenticated request within the AI_EXPENSIVE rate limit's request-count budget could still carry a very large payload, inflating LLM token cost per request beyond what the rate limiter's request-count throttling accounts for. No pagination/query-limit review was performed for the list-style endpoints (`recommendations`, `career-simulation/history`) beyond confirming they exist and are scoped correctly — if any of these can return an unbounded number of rows for a user with a very large history, add a `LIMIT`/pagination parameter; this wasn't confirmed either way in this pass and is called out as unverified rather than claimed clean.

## 30. Deployment audit

- `backend/Dockerfile` (14 lines, full contents read): single-stage, `python:3.12-slim`, installs `requirements.txt`, copies `app/`, `EXPOSE 8000`, runs `uvicorn app.main:app`. **No `USER` directive — the container runs as root.** No `HEALTHCHECK` instruction. No secrets baked in (`.env` correctly excluded via `.dockerignore`).
- **No `docker-compose*.yml`, `render.yaml`, `vercel.json`, `fly.toml`, `Procfile`, or `.github/workflows/` exists anywhere in the repo** — there is currently no checked-in CI/CD pipeline or hosting configuration at all. Whatever deployment happens today is manual and undocumented in version control. This means `ENVIRONMENT=production`, `CORS_ORIGINS`, `TRUSTED_PROXY_HOPS`, and every other environment-dependent setting discussed above depend entirely on whoever deploys it setting them correctly by hand, with nothing in the repo to catch a mistake.
- Frontend build was not verified to actually succeed in a clean environment during this audit pass (per `HARDENING_SUMMARY.md`'s own note that a prior attempt hit a missing native binary in its sandbox) — worth the team running a real `npm run build` before deploying, as a basic sanity check, not something this audit could verify itself.

## 31. Security test plan (manual checklist with concrete examples)

**Authentication**
- Signup → verify email → login → confirm `access_token`/`refresh_token` present in the Supabase session, never in a URL.
- Log in, wait past token expiry (or manually craft an expired token — see below), confirm the API returns 401, not a stale-success response.
- Send a request with no `Authorization` header to any non-`/health` route → expect 401.
- Send a request with a malformed header (`Authorization: Bearer not-a-jwt`) → expect 401.
- Forge a token with an obviously wrong secret and confirm rejection:
  ```python
  import jwt, time
  bad = jwt.encode({"sub": "attacker", "aud": "authenticated", "exp": int(time.time())+3600}, "wrong-secret", algorithm="HS256")
  # curl -H "Authorization: Bearer $bad" https://<api>/api/v1/career-ai/profile-analysis
  # expect 401
  ```
- Craft an `alg=none` token and confirm rejection:
  ```python
  hdr = base64url({"alg":"none","typ":"JWT"}); payload = base64url({"sub":"x","aud":"authenticated","exp":9999999999})
  token = f"{hdr}.{payload}."
  # expect 401
  ```

**Authorization (User A vs User B)**
- As User A, note the id of one of your own `career_simulations` rows. As User B, call `GET /api/v1/career-ai/career-simulation/{User A's id}` → expect 404, not 200 and not A's data.
- As User B, call `GET /api/v1/career-ai/ai-coach/conversations/{User A's conversation id}` → expect 404 (confirmed by code review this doesn't leak "exists but not yours" via a 403).
- Attempt to `PATCH` your own profile's `profile_score` directly via the Supabase REST API with your own anon key + JWT (bypassing the frontend entirely) → currently **succeeds** (this is the known finding from §7 — confirms the gap is real, not a false positive).

**Input**
- Send a `career-simulation` request with a 5MB `scenario_input` dict → confirm current behavior (accepted, per §10's finding) vs. desired behavior (rejected with 422) once the fix lands.
- Send obvious XSS payloads (`<script>alert(1)</script>`, `<img src=x onerror=alert(1)>`) as a profile bio or chat message, and confirm they render as inert literal text in the UI, not executed markup.
- Send a malformed JSON body to any POST endpoint → expect a 422 with pydantic's field errors, not a 500.

**File upload**
- Rename a `.exe` to `.pdf` and attempt to upload it as a resume via a direct Supabase Storage API call (bypassing the frontend's client-side extension check) using your own valid session → confirm current behavior (accepted, per §11's finding) so the team is aware it isn't currently blocked server-side.
- Attempt to write into another user's resume storage path (`resumes/<other-user-id>/...`) using your own JWT → expect a 403/RLS denial.

**API abuse**
- Hammer `POST /api/v1/career-ai/career-simulation` past the configured per-minute AI_EXPENSIVE limit → expect 429 once the threshold is hit.
- Confirm the same for the per-IP layer using a fresh account behind the same IP.

**Redirect**
- Manually set `localStorage.postLoginRedirect` to an external URL (`https://evil.example`) before triggering the OAuth callback flow → confirm current app behavior actually navigates there (this is expected today, since the value is only ever *set* by trusted code paths — the point of this test is to confirm the *read* side has no additional validation, which is a defense-in-depth gap worth knowing about even though nothing in the app currently writes an attacker-controlled value there).
- Click an "Apply" link on a listing whose `apply_url` has been manually set (via direct DB access, for test purposes) to `javascript:alert(document.cookie)` → confirm it currently executes (validates the §2/§25/§34 finding) — do this only in a test/staging environment, never production.

## 32. Final security score

**72 / 100 — 🟠 SIGNIFICANT FIXES REQUIRED**

This is not a score inflated by an architecture that looks good on paper — it reflects genuinely strong fundamentals (JWT verification, RLS coverage, IDOR-resistant module design, no custom-auth-reinvention, real rate limiting, no leaked secrets, no SQL injection surface, no XSS-via-innerHTML) pulled down by one HIGH-severity, concretely exploitable-in-principle finding (the `apply_url` scheme gap, with a session-token-theft blast radius) that should not ship as-is, plus a cluster of MEDIUM column-level RLS gaps and missing security headers that are cheap to fix but currently absent. None of the MEDIUM/LOW findings individually would justify a lower band, but the one HIGH finding is a genuine production blocker until fixed — hence 🟠 rather than 🟡.

## 33. Findings, ranked by severity

**CRITICAL:** none found.

**HIGH:**
1. `apply_url` (scraped opportunity data) rendered as an `href`/`window.open` target with no URL-scheme validation — a `javascript:` URI in scraped data would execute in the app's origin and could exfiltrate the Supabase session token from `localStorage`. `frontend/src/pages/AppShell.jsx:561,593`, `frontend/src/services/supabase/opportunities.js:13`. **Production blocker.**

**MEDIUM:**
2. `career_simulations` RLS UPDATE policy lets a user directly set `status`/`verdict`/`result`/`completed_at`/`model_used` on their own row, bypassing the LLM call entirely. `supabase/policies/006_rls_career_simulation.sql:31-35`.
3. `profiles` RLS UPDATE policy lets a user directly set `profile_score`/`ai_profile_summary`/`last_profile_analysis` on their own row. `supabase/policies/001_rls.sql:27-31`, `supabase/schema/001_profiles.sql:58-60`.
4. No security-headers middleware at all (no CSP guidance for the frontend host, no HSTS/X-Content-Type-Options/Referrer-Policy on the API). `backend/app/main.py`.
5. `career-roadmap`/`career-simulation` request schemas accept unbounded strings and a fully free-form, unbounded `scenario_input` dict — cost/DoS amplification and unconstrained prompt-injection surface. `backend/app/career_roadmap/schemas/roadmap.py:226`, `backend/app/career_simulation/schemas/simulation.py:222-244`.
6. `DELETE /api/v1/career-ai/career-simulation/{id}` silently no-ops instead of deleting (missing RLS DELETE policy + missing empty-response check) — a functional/data-integrity bug, fails closed, not cross-user-exploitable, but must be fixed before launch since it misleads users about their own data. `supabase/policies/006_rls_career_simulation.sql`, `backend/app/career_simulation/services/repository.py:124-125`.

**LOW:**
7. `roadmap_activity` INSERT policy lacks a transitive ownership check on `roadmap_id`. `supabase/policies/005_rls_career_roadmap.sql:42-45`.
8. `coach_messages` INSERT policy doesn't restrict the `role` column, allowing a user to forge a fake assistant reply in their own conversation (needs the write-path caveat noted in §35 before changing). `supabase/policies/007_rls_ai_coach.sql:51-59`.
9. AI Coach prompt construction interpolates unbounded raw user text with no explicit instruction/data delimiting — bounded-impact prompt-injection surface. `backend/app/ai_coach/utils/context.py:130-185`.
10. `backend/Dockerfile` runs the container as root (no `USER` directive) — defense-in-depth gap, not directly exploitable alone.
11. `DEBUG=True` default is dead/unused configuration — a landmine, not a live risk today. `backend/app/core/config.py:28`.
12. No app-level guard against a `CORS_ORIGINS=*` + `allow_credentials=True` misconfiguration (current config is safe; this is a fail-fast recommendation).
13. Resume upload has no server-side file-type/size enforcement beyond ownership scoping (client-side check only, low impact since self-scoped).
14. Old 501-stub scaffold routers (`roadmap.py`, `simulation.py`, `chat.py`) and the `app/ai/{chains,llm,prompts}` legacy abstraction are unnecessary, unused surface — recommend deleting as cleanup, not a vulnerability.
15. No `.git` history was available to audit for previously-committed secrets — recommend running the same secrets scan against the real remote history.
16. Google OAuth uses implicit flow rather than PKCE for the token exchange — a one-setting hardening improvement in the Supabase dashboard, not a live gap (state/CSRF protection for the OAuth flow itself is already handled by Supabase).
17. No deployment config (`render.yaml`/`vercel.json`/CI) is checked into the repo, so every environment-dependent production setting (`ENVIRONMENT`, `CORS_ORIGINS`, `TRUSTED_PROXY_HOPS`) currently depends entirely on manual, undocumented deploy-time configuration.

## 34. Master findings table

| # | Severity | Area | Vulnerability / Issue | File | Impact | Required Fix | Production Blocker? |
|---|---|---|---|---|---|---|---|
| 1 | HIGH | Frontend / XSS | `apply_url` rendered as link/window.open target with no scheme validation | `frontend/src/pages/AppShell.jsx:561,593`; `frontend/src/services/supabase/opportunities.js:13` | A malicious/compromised scraped listing with a `javascript:` URL executes script in the app's origin, can read the Supabase session token from `localStorage` | Validate `apply_url` scheme is `http`/`https` at ingestion time (reject/null non-conforming values before insert) AND at render time (defense-in-depth) | **Yes** |
| 2 | MEDIUM | Database / RLS | `career_simulations` UPDATE policy doesn't protect backend-only columns | `supabase/policies/006_rls_career_simulation.sql:31-35` | User can fabricate their own simulation result without an LLM call | Add a trigger or split-table approach restricting `status`/`verdict`/`result`/`completed_at`/`model_used` to service-role writes | Recommended before launch |
| 3 | MEDIUM | Database / RLS | `profiles` UPDATE policy doesn't protect backend-only columns | `supabase/policies/001_rls.sql:27-31` | User can fabricate their own `profile_score`/`ai_profile_summary` | Same trigger pattern, restricting those 3 columns | Recommended before launch |
| 4 | MEDIUM | Backend / Headers | No security-headers middleware | `backend/app/main.py` | Missing defense-in-depth (MIME sniffing, clickjacking, HSTS) | Add `SecurityHeadersMiddleware`; set CSP at the frontend's hosting layer | Recommended before launch |
| 5 | MEDIUM | Backend / Validation | Unbounded `target_role`/`scenario_title`/`scenario_input` | `backend/app/career_roadmap/schemas/roadmap.py:226`; `backend/app/career_simulation/schemas/simulation.py:222-244` | Cost/DoS amplification per request; unconstrained prompt-injection surface | Add `max_length` to string fields; cap serialized size of `scenario_input` via a validator | Recommended before launch |
| 6 | MEDIUM | Backend / Functional | `DELETE .../career-simulation/{id}` silently no-ops | `supabase/policies/006_rls_career_simulation.sql`; `backend/app/career_simulation/services/repository.py:124-125` | User's delete action does nothing; misleading UX, data never actually removed | Add a DELETE RLS policy `using (profile_id = auth.uid())`; make `delete_simulation` raise `NotFoundError` on empty `response.data`, matching `ai_coach`'s pattern | **Yes — broken feature** |
| 7 | LOW | Database / RLS | `roadmap_activity` INSERT lacks transitive ownership check | `supabase/policies/005_rls_career_roadmap.sql:42-45` | User can attach fabricated activity to another user's roadmap if they know its UUID | Add `EXISTS(...career_roadmaps WHERE id=roadmap_id AND user_id=auth.uid())` to the `WITH CHECK` clause | No |
| 8 | LOW | Database / RLS | `coach_messages` INSERT doesn't restrict `role` | `supabase/policies/007_rls_ai_coach.sql:51-59` | User can forge a fake "assistant" message in their own conversation | Verify whether assistant replies are currently written via the user-scoped client before changing this policy — see §35 caveat | No |
| 9 | LOW | AI/LLM | Unbounded, undelimited user text in AI Coach prompt | `backend/app/ai_coach/utils/context.py:130-185` | Bounded prompt-injection risk, self-directed only | Wrap user content in an explicit fenced/delimited block; instruct model to treat it as data | No |
| 10 | LOW | Deployment | Docker container runs as root | `backend/Dockerfile` | Defense-in-depth gap | Add a non-root `USER` directive | No |
| 11 | LOW | Config hygiene | `DEBUG=True` default, unused | `backend/app/core/config.py:28` | Dead but risky-looking default | Remove or default to `False` | No |
| 12 | LOW | CORS | No guard against `*` + credentials misconfiguration | `backend/app/core/config.py` | Fail-fast improvement only; current config is safe | Add a startup assertion | No |
| 13 | LOW | File upload | No server-side type/size enforcement on resumes | `frontend/src/services/supabase/profiles.js:17-38` | Self-scoped storage-quota abuse only | Set bucket-level size/MIME limits in Supabase Storage settings | No |
| 14 | LOW | Cleanup | Dead scaffold routers and `app/ai/{chains,llm,prompts}` | `backend/app/api/v1/routes/{roadmap,simulation,chat}.py`; `backend/app/ai/` | Unnecessary attack surface / audit confusion, not itself exploitable | Delete once confirmed unused (already independently confirmed unused in this audit) | No |
| 15 | LOW | Secrets | No git history available to audit | (repo has no `.git`) | Cannot confirm no secret was ever committed | Run the same secrets grep against the real remote's full history | No, but should be done |
| 16 | LOW | Auth | OAuth uses implicit flow, not PKCE | Supabase dashboard setting | Marginal hardening improvement | Enable PKCE flow in Supabase dashboard | No |
| 17 | LOW | Deployment | No deployment config checked into the repo | (absent) | Environment-dependent settings depend on manual, undocumented configuration | Add `render.yaml`/`vercel.json` (or equivalent) codifying `ENVIRONMENT`, `CORS_ORIGINS`, etc. | Recommended |

## 35. Exact file-by-file remediation

**#1 — `apply_url` scheme validation (production blocker)**

Frontend defense-in-depth, `frontend/src/services/supabase/opportunities.js` (near line 13):
```js
const SAFE_URL_SCHEME = /^https?:\/\//i;

function sanitizeApplyUrl(url) {
  if (typeof url !== "string" || !SAFE_URL_SCHEME.test(url.trim())) return "";
  return url.trim();
}

// in the row-mapping function:
applyUrl: sanitizeApplyUrl(row.apply_url),
```
Backend/source-of-truth fix, in the ingestion write path (wherever `opportunities.apply_url` is set before insert, `app/ingestion/services/opportunity_service.py`):
```python
import re

_SAFE_URL_SCHEME = re.compile(r"^https?://", re.IGNORECASE)

def _sanitize_apply_url(url: str | None) -> str | None:
    if not url or not _SAFE_URL_SCHEME.match(url.strip()):
        return None
    return url.strip()

# apply before the insert/upsert call:
row["apply_url"] = _sanitize_apply_url(row.get("apply_url"))
```
DB-level defense-in-depth (optional but cheap), add to a new migration file under `supabase/schema/`:
```sql
alter table public.opportunities
  add constraint opportunities_apply_url_scheme_check
  check (apply_url is null or apply_url ~* '^https?://');
```

**#6 — `career_simulations` DELETE (production blocker, broken feature)**

New policy file or append to `supabase/policies/006_rls_career_simulation.sql`:
```sql
create policy "career_simulations_delete_own"
  on public.career_simulations
  for delete
  using (profile_id = auth.uid());
```
`backend/app/career_simulation/services/repository.py` (`delete_simulation`, around line 124):
```python
def delete_simulation(self, simulation_id: str, profile_id: str) -> None:
    response = (
        self._client.table("career_simulations")
        .delete()
        .eq("id", simulation_id)
        .eq("profile_id", profile_id)
        .execute()
    )
    if not response.data:
        raise NotFoundError("Simulation not found.")
```

**#2 / #3 — column-level RLS gaps (recommended before launch)**

For `profiles` (new migration):
```sql
create or replace function public.enforce_profile_backend_only_columns()
returns trigger as $$
begin
  if auth.role() <> 'service_role' then
    new.profile_score := old.profile_score;
    new.ai_profile_summary := old.ai_profile_summary;
    new.last_profile_analysis := old.last_profile_analysis;
  end if;
  return new;
end;
$$ language plpgsql security definer;

create trigger profiles_protect_backend_columns
  before update on public.profiles
  for each row execute function public.enforce_profile_backend_only_columns();
```
Apply the identical pattern to `career_simulations`, protecting `status`, `verdict`, `result`, `completed_at`, `model_used`. **Before shipping either trigger**, confirm the backend actually writes those columns via the user-scoped client (not the service-role client) in the normal generate/complete flow — if it already uses the service-role client for those specific writes, the trigger is redundant but harmless; if it uses the user-scoped client, the trigger's `auth.role() <> 'service_role'` branch would then also block the app's own legitimate write, and the trigger needs to instead check a different signal (e.g. only allow the change when the row is transitioning via the specific backend code path, which is harder to express in SQL alone) — **verify this against the actual write call site before deploying**, per the "don't make changes that could break working functionality" instruction.

**#4 — security headers**

New file `backend/app/middleware/security_headers.py`:
```python
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
```
Register in `backend/app/main.py`, after the existing `add_middleware` calls:
```python
from app.middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)
```
CSP is a frontend-hosting-layer concern for a static SPA — once a hosting config exists (Vercel `vercel.json` `headers` block, or equivalent), add something like:
```json
{ "key": "Content-Security-Policy", "value": "default-src 'self'; connect-src 'self' https://*.supabase.co https://<your-render-domain>; img-src 'self' data: https:; script-src 'self'; style-src 'self' 'unsafe-inline';" }
```
adjusted to the real Supabase project domain and backend URL once deployed.

**#5 — unbounded payload fields**

`backend/app/career_roadmap/schemas/roadmap.py` (near line 226):
```python
target_role: str = Field(..., max_length=200)
```
`backend/app/career_simulation/schemas/simulation.py` (near lines 222–244):
```python
target_role: str = Field(..., max_length=200)
scenario_title: str = Field(..., max_length=300)

@field_validator("scenario_input")
@classmethod
def _cap_scenario_input_size(cls, v: dict) -> dict:
    import json
    if len(json.dumps(v)) > 20_000:
        raise ValueError("scenario_input is too large.")
    return v
```
Apply the same two field changes to `SimulationOption`'s equivalent fields used in `/compare`.

**#10 — Dockerfile non-root user**

`backend/Dockerfile`, insert before the final `CMD`:
```dockerfile
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser
```

**#11 — dead `DEBUG` flag** — either remove `DEBUG: bool = True` from `app/core/config.py:28` entirely, or change the default to `False`; either is fine since it's unread elsewhere.

**#14 — cleanup (optional, non-blocking)** — delete `backend/app/api/v1/routes/{roadmap,simulation,chat}.py` and their mounts in `backend/app/api/v1/router.py` (confirmed unused by the frontend, confirmed 501-only), and delete `backend/app/ai/{chains,llm,prompts}/` (confirmed unused by anything outside itself) — only do this once the team confirms nothing external depends on those routes existing (even as a 501), since removing a mounted route changes the API surface's shape even if it never did anything.

## 36. Explicitly not recommended

Per the instruction not to make unnecessary changes: this audit does **not** recommend replacing Supabase Auth with a custom auth system (no concrete security requirement justifies it — the current thin-wrapper posture is correct), does not recommend adding bcrypt/custom JWT issuance/custom session management (none of that is missing or needed), does not recommend CSRF protection (§14 — the auth mechanism makes it inapplicable), does not recommend a blanket dependency upgrade (§17 — only two items had a concrete reason), and does not recommend rewriting the JWT verification logic (§5 — it's correct as-is; the one note there is an optional hardening of pinning `algorithms=` explicitly, not a required fix). The RLS/database layer as a whole is sound and does not need restructuring — the fixes above are narrow, additive corrections to specific gaps, not an architecture change.

## 37. Final deployment gate

1. Can I deploy right now? **Not as-is** — one HIGH finding (#1) should be fixed first.
2. Are there authentication bypasses? No.
3. Is there IDOR? No cross-user IDOR found anywhere in the reachable API.
4. Can User A access or modify User B's data? No — every checked path is correctly scoped, both at the application layer and independently at the RLS layer.
5. Can an attacker forge authentication? No — JWT signature verification is correctly enforced, tested against `alg=none`, wrong-secret, and tampered-payload attacks.
6. Are JWTs correctly verified? Yes.
7. Is RLS correctly protecting the database? Mostly — row-level ownership is correct everywhere; a small number of backend-only *columns* (findings #2/#3) aren't protected at the column level, self-serving-impact only.
8. Are secrets exposed? No secret was found exposed in the frontend, in backend defaults, or in the current working tree; git history could not be checked (no `.git` present in this working copy) and should be checked against the real remote.
9. Is there XSS? One real finding (#1), not via `innerHTML`/`dangerouslySetInnerHTML` but via unvalidated URL scheme on a link target — production blocker until fixed.
10. Is there SQLi? No — no raw SQL string-building found anywhere.
11. Is there SSRF? No exploitable vector found in the reachable API surface.
12. Is file upload unsafe? Low-impact gap only (no server-side type/size enforcement, but self-scoped by RLS).
13. Is CORS correct? Yes, currently safe; recommend a fail-fast guard as insurance.
14. Is rate limiting sufficient? Yes — comprehensive, Redis-backed, applied to every implemented endpoint.
15. Is the OAuth flow secure? Yes, functionally; PKCE is a recommended-not-required hardening step.
16. Is password reset secure? Fully delegated to Supabase Auth; nothing custom to audit.
17. Are production errors/logs safe? Yes — no stack traces or secrets returned to clients.
18. Are there dev/debug bypasses? No live ones; the unused `DEBUG` default is a cleanup item, not an active bypass.
19. Are AI features protected against prompt injection/abuse? Rate-limited and structurally bounded (no tool-calling); prompt injection is possible but its impact is self-directed and low severity.
20. Are there business-logic vulnerabilities? Only the self-serving column-level RLS gaps (#2/#3); nothing cross-user.
21. Is the frontend secure? Yes, aside from finding #1.
22. Is the backend secure? Yes, aside from findings #2/#3/#5/#6.
23. Is the database secure? Yes, aside from the column-level gaps noted throughout.
24. Is the deployment configuration secure? Unverifiable — no deployment config exists in-repo to audit; must be confirmed once real hosting config is added.
25. Have git history and dependency chains been fully checked? Git history: no (no `.git` present here — recheck against the real remote). Dependencies: yes, no known-vulnerable package found.
26. Overall: is this application, as it stands today, ready to accept real user traffic? Close, but not yet — one concrete production-blocking fix and one broken-feature fix are needed first.

**🟡 APPROVED AFTER FIXING THE FOLLOWING:**
1. Validate/sanitize `apply_url` scheme (finding #1) — both at ingestion and at render time.
2. Fix the `career_simulations` DELETE no-op (finding #6).
3. Strongly recommended before launch, not strictly blocking: the column-level RLS triggers (#2/#3, with the write-path verification caveat), the security-headers middleware (#4), and the unbounded-payload validation (#5).
4. Before considering this audit's secrets finding closed: run the git-history secrets scan against the real remote repository, since none was available to check here.

This is not a claim that the application is unhackable — no application can be. It's an assessment of what was found against everything the audit was asked to cover, with the two items above as the concrete gate to close before production traffic.
