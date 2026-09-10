# OwnMove — Authentication & Authorization Security Audit

Scope: complete auth lifecycle across `frontend/`, `backend/`, and `supabase/` (schema + RLS policies). Read-only — nothing changed. Every finding below is grounded in a specific file, and the JWT-verification claims were additionally verified empirically (scripts run against the actual installed `PyJWT==2.3.0` in `backend/.venv`), not inferred from reading code alone. Two prior audits exist in this repo (`PENTEST_REPORT.md`, `PRODUCTION_AUDIT.md`) — their #1 finding ("email/password auth is fake") is now **fixed** per `HARDENING_SUMMARY.md`; this audit independently re-verifies that and goes further into the backend, RLS, and JWT layers those two audits explicitly couldn't reach.

---

## Verdict

**B — Production-ready after minor fixes.**

The core decision this audit was asked to make: **is Supabase correctly the sole authority for passwords, tokens, and sessions, or is the app dangerously reinventing auth?** Answer: **Supabase is correctly the sole authority.** There is no bcrypt, no password table, no hand-rolled JWT issuance, no custom session table anywhere in this codebase. The backend only *verifies* Supabase-issued tokens; it never *creates* identity. That is the correct architecture and should **not** be changed.

What keeps this from an unqualified "A" is a short list of real gaps — none of them "Supabase was implemented wrong," all of them "production-hardening steps that haven't been done yet": no password-reset flow, no backend rate limiting (an explicit TODO in the code), the OAuth client using the weaker implicit flow instead of PKCE, and one JWT-verification code pattern that is fragile-by-design even though it isn't exploitable against the library version currently installed (details in §7).

---

## 1–2. The auth lifecycle, traced in actual code, and whether custom bcrypt/JWT/session code is needed

Answer to your core question up front, then the trace: **no bcrypt, no custom JWT generation, no custom refresh-token table, no custom session table exists or is needed.** Every one of those responsibilities is handled by Supabase Auth (GoTrue) end-to-end. Duplicating any of them yourself would be pure regression — it would mean maintaining a second, weaker copy of what Supabase already does correctly, with none of Supabase's key-rotation, refresh-token-reuse-detection, or abuse-monitoring built in.

| Responsibility | Who does it | Where in code |
|---|---|---|
| Store the user's password | **Supabase Auth's `auth.users` table** (its own Postgres schema, not `public.profiles`) | Nowhere in this repo — by design |
| Hash/verify the password | **Supabase Auth**, server-side, at `supabase.co` | `frontend/src/services/supabase/auth.js:81` (`signInWithPassword`) just calls the SDK; no hashing code anywhere in the repo |
| Generate the JWT (access token) | **Supabase Auth** | Same — `supabase.auth.signUp` / `signInWithPassword` / `signInWithOAuth` return a session; the app never constructs a token |
| Generate/rotate the refresh token | **Supabase Auth**, automatically | `@supabase/auth-js` (installed dep, v2.111.0) — `autoRefreshToken: true` by default (verified in `node_modules/@supabase/auth-js/dist/main/GoTrueClient.js:20`) |
| Where the session is stored | **Browser `localStorage`**, key `sb-<project-ref>-auth-token` | `persistSession: true` + no custom `storage` passed in `client.js` → falls back to `globalThis.localStorage` (`GoTrueClient.js:241`) |
| Session restoration after reload | `supabase.auth.getSession()` reads the persisted session from `localStorage` on next load | `frontend/src/pages/AppShell.jsx` (mount effect), `AuthCallbackScreen.jsx` |
| Token refresh | Handled internally by `@supabase/auth-js` on a timer before expiry — no app code involved | N/A — library-internal |
| Logout | `supabase.auth.signOut()` clears the session client-side and revokes the refresh token server-side | `frontend/src/components/landing/HeroSection.jsx` (`handleLogout`) |
| Verifying a request server-side | **FastAPI backend independently re-verifies** the JWT's cryptographic signature on every protected call — it does not trust the frontend | `backend/app/core/security.py`, `backend/app/api/deps.py` |

**Sign-up** (`AuthDialog.jsx:112` → `signUpWithEmail()` in `auth.js:57`): calls `supabase.auth.signUp()`. Whether a session comes back immediately or the user must confirm their email first is a **Supabase project setting** ("Confirm email", Authentication → Providers → Email), not app logic — the code correctly handles both outcomes (`needsEmailConfirmation` flag). Anti-enumeration: Supabase returns success with an empty `identities` array for an email that's already registered rather than an error; the code explicitly checks for that (`auth.js:70`) and raises a friendly "account already exists" message — see §12 for the trade-off this implies.

**Login** (`signInWithEmail()`, `auth.js:81`): `supabase.auth.signInWithPassword()`. On success, `@supabase/auth-js` persists the returned access+refresh token pair to `localStorage` itself — no app code touches the tokens directly at any point.

**Google OAuth** (`startGoogleSupabaseAuth()`, `auth.js:39` → `AuthCallbackScreen.jsx`): browser navigates to Supabase's `/auth/v1/authorize`, then Google, then back to Supabase, then to `${origin}/auth/callback`. `AuthCallbackScreen.jsx` just calls `getSession()` — it never manually parses the URL fragment; `detectSessionInUrl: true` (library default, confirmed in `GoTrueClient.js:22`) means `@supabase/auth-js` does that parsing itself before `getSession()` is even called. Full trace and flow-type finding in §5.

**Logout**: `HeroSection.jsx`'s `handleLogout` calls `supabase.auth.signOut()`, which triggers `onAuthStateChange('SIGNED_OUT')` app-wide — `AppShell.jsx:1842` listens for this and drops the UI back to signed-out state live, not just on next load.

**Session restoration**: `AppShell.jsx`'s mount effect calls `getSession()`; if a valid persisted session exists in `localStorage`, it's returned synchronously from the SDK's cache without a network round trip (the SDK validates expiry locally and only hits the network to refresh if the access token is stale).

---

## 3. Supabase client configuration audit

File: `frontend/src/services/supabase/client.js` (full content — this is the *entire* file):

```js
export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

That's it — **no options object at all.** Every behavior is a library default. Per your instruction not to assume defaults, these were read directly out of the installed `@supabase/auth-js@2.111.0` source (`node_modules/@supabase/auth-js/dist/main/GoTrueClient.js:17-22`):

```js
const DEFAULT_OPTIONS = {
    storageKey: 'sb-<project-ref>-auth-token',
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
    flowType: 'implicit',   // <-- see finding below
};
```

- **URL/key**: `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` from `frontend/.env`, read once through `import.meta.env` — correct, this is the publishable key, safe to ship to the browser.
- **Persistence/storage**: `localStorage`. This is standard for an SPA and is *not* itself a finding — every mainstream SPA auth library (Supabase, Auth0, Firebase) does this, because the alternative (in-memory only) means every page refresh logs the user out. The real question is what protects it, covered next.
- **XSS/token-theft implication**: a token in `localStorage` is readable by any JS that runs on the page's origin. This is not a vulnerability in the Supabase client — it's the standard SPA trade-off, and it's why §6's "no `dangerouslySetInnerHTML`/`eval` anywhere" finding matters: there is currently no way for attacker JS to run on this app's origin, so the token is not currently exposed. If that ever changes (a future markdown renderer, a new `dangerouslySetInnerHTML` call, a dependency-supply-chain issue), it immediately becomes a full session-hijack vector — this is the exact chain flagged as finding #2+#3 in the old `PENTEST_REPORT.md`, and it's still architecturally true today, it's just that the one concrete XSS vector that report worried about (unsanitized `apply_url`) turned out to already be blocked server-side (see §6/§12 detail below). Treat "keep the app XSS-free" as a standing security requirement, not a one-time fix.
- **`flowType: 'implicit'` — Medium finding.** Since no `flowType` is configured, the client defaults to the **implicit** OAuth flow rather than **PKCE**. This matches what the real OAuth redirect URL showed in this session's live debugging (`.../authorize?provider=google&redirect_to=...` — no `code_challenge` param, which a PKCE flow would include). PKCE is the flow Supabase and the OAuth community recommend for public clients (SPAs, mobile apps) specifically because implicit flow puts the access token directly in the redirect URL fragment, which is more exposed to referrer leakage, browser history, and any code that reads `location.hash`. **Fix**: `createClient(url, key, { auth: { flowType: 'pkce' } })` — one line, no other code changes required, `AuthCallbackScreen.jsx` needs no changes since it already just calls `getSession()`.

---

## 4. Signup/login security audit

| Protection | Status | Who provides it |
|---|---|---|
| Email confirmation | Supported, toggle lives in Supabase dashboard, app handles both states correctly | Supabase (config) + app (`auth.js:75`) |
| Enumeration handling on signup | Explicit `identities.length === 0` check maps to a friendly message | App (`auth.js:70`) — see §12 for the trade-off |
| Password requirements | Frontend only enforces `minLength={6}` (`AuthDialog.jsx`); actual minimum is whatever the Supabase project's Auth settings say | Mixed — **verify the Supabase dashboard's password policy matches or exceeds 6**, since the frontend's `minLength` is a UX hint only, not enforcement (a request can always be sent directly to Supabase's API bypassing the HTML form) |
| Login failure handling | Generic "Incorrect email or password" (`auth.js:23`) — does not reveal whether the email exists | App — correct, safe pattern |
| Rate limiting / brute force | Supabase Auth has built-in platform-level rate limits on its `/auth/v1/*` endpoints (sign-in attempts, email sends) | **Supabase only** — nothing in this app adds any of its own; do not rely on this codebase for it |
| CAPTCHA | **Not integrated.** `signUp`/`signInWithPassword`/`signInWithOAuth` calls in `auth.js` never pass a `captchaToken` option, and Supabase captcha protection (hCaptcha/Turnstile) has to be explicitly wired on both the dashboard and the client call | Neither — gap, see remediation |
| OAuth account linking | Governed entirely by Supabase dashboard settings (Authentication → Providers → "allow manual linking" / same-email auto-linking) — **not visible in this repo at all** | Supabase (config) — must be verified directly in the dashboard |
| Duplicate accounts | Same as above; Supabase's own identity-linking rules decide whether `same-email` + `different provider` merges into one user or errors | Supabase (config) |
| **Password reset** | **Not implemented anywhere.** The "Forgot?" button in `AuthDialog.jsx` has no `onClick` handler at all — it's dead UI. Grepped the entire `frontend/src` for `resetPasswordForEmail`/`updateUser`/any recovery pattern: zero matches | **Missing — High-priority gap, see remediation** |
| Email change | Not implemented (no `updateUser({ email })` call anywhere) | Missing — lower priority than password reset, but a real gap if users ever need it |
| Session behavior after password change | Untestable — there's no password-change UI to trigger it. Supabase's own default behavior (does not globally revoke other sessions unless you explicitly call `admin.signOut(userId, 'global')`) would apply once a reset flow exists | N/A today |
| Account deletion | **Not implemented.** No `auth.admin.deleteUser` call or equivalent anywhere, frontend or backend | Missing — worth having before a real public launch, for support requests and any GDPR/right-to-erasure obligation |
| Suspicious/expired sessions | Handled by `AppShell.jsx`'s `onAuthStateChange('SIGNED_OUT')` listener — an expired/revoked session drops the UI live | App — correct |

---

## 5. Google OAuth audit

Traced end-to-end: `AuthDialog.jsx` → `startGoogleSupabaseAuth()` (`auth.js:39`) → browser navigates to `<SUPABASE_URL>/auth/v1/authorize?provider=google&redirect_to=<origin>/auth/callback` → Google → back to Supabase → `<origin>/auth/callback` → `AuthCallbackScreen.jsx` → `getSession()` → `resolvePostAuthRedirect()`.

- **Redirect URL**: built from `window.location.origin` at runtime (`auth.js:44`), never a hardcoded or attacker-suppliable string — correct. This *does* mean the actual allowed redirect targets are whatever's allow-listed in the Supabase dashboard (Authentication → URL Configuration → Redirect URLs) — confirm `http://localhost:5173/auth/callback` (dev) and your real production origin's `/auth/callback` are both listed there, and that no wildcard/overly-broad entry is present, since Supabase will refuse to redirect anywhere not on that list — that's the actual security boundary for this step, not app code.
- **Open redirect**: none. Traced every `window.location.assign/replace` call site — all are hardcoded internal paths or `postLoginRedirect` from `localStorage`, which is only ever set by the app itself to literal strings (`HowItWorksSection.jsx:23`, `DemoSection.jsx:396`), never from a URL query parameter. `useClientNavigation.js:29` additionally rejects any `href` that doesn't start with `/` or that starts with `//`.
- **PKCE/state**: state-parameter CSRF protection for the OAuth flow is handled by Supabase's `/authorize` endpoint itself regardless of flow type. What *isn't* enabled is PKCE for the token exchange (see §3 finding) — recommend turning it on.
- **Callback handling**: correct — no manual token parsing, relies entirely on the SDK's `detectSessionInUrl`.
- **Token leakage**: none found — tokens are never put in a URL by app code, never logged to console (grepped).
- **Production vs. localhost**: `redirectTo` is dynamic (`window.location.origin`), so no code change is needed between environments — but the Supabase dashboard's allow-list (see above) must include the production origin, and this could not be verified from the repo (and currently can't even be reached — see the note in §10 about the Supabase project URL returning `DNS_PROBE_FINISHED_NXDOMAIN` in this session's live testing, which blocks *all* auth, Google included, until resolved).

---

## 6. PostgreSQL RLS — every table, checked individually

Read every file in `supabase/policies/` (8 files) and cross-referenced against every table created in `supabase/schema/`. Summary table, then attack scenarios.

| Table | RLS enabled | SELECT | INSERT | UPDATE | DELETE | Cross-user access possible? |
|---|---|---|---|---|---|---|
| `profiles` | ✅ | `id = auth.uid()` | `id = auth.uid()` | `id = auth.uid()` | none (no policy — deletes blocked entirely except via the `auth.users` cascade) | **No** |
| `experiences` | ✅ | `profile_id = auth.uid()` | `profile_id = auth.uid()` | `profile_id = auth.uid()` | `profile_id = auth.uid()` | **No** |
| `opportunities` | ✅ | `is_active = true`, any authenticated user (intentional — shared catalog) | none via API (service-role/dashboard only) | none | none | N/A — public catalog by design, not user-owned data |
| `saved_opportunities` | ✅ | `user_id = auth.uid()` | `user_id = auth.uid()` | — (no update policy; app deletes+re-inserts) | `user_id = auth.uid()` | **No** |
| `profile_embeddings` / `opportunity_embeddings` | ✅ | **no policy for `authenticated`** → default-deny | none | none | none | **No** — correctly unreachable from the browser at all; only `get_admin_supabase()` (service-role) touches these, confirmed in `embedding_service.py` |
| `profile_insights` | ✅ | `profile_id = auth.uid()` | none via API (backend service-role writes) | none | none | **No** |
| `recommendations` | ✅ | `user_id = auth.uid()` | none via API | none | none | **No** |
| `interaction_events` | ✅ | none (write-only log) | `user_id = auth.uid()` | none | none | Can't even read own events back — append-only log, correct for its purpose |
| `profile_analysis` | ✅ | `profile_id = auth.uid()` | `profile_id = auth.uid()` | none (immutable history) | none | **No** |
| `career_roadmaps` | ✅ | `user_id = auth.uid()` | `user_id = auth.uid()` | `user_id = auth.uid()` | none | **No** |
| `roadmap_activity` | ✅ | `user_id = auth.uid()` | `user_id = auth.uid()` | none | none | **No** |
| `career_simulations` | ✅ | `profile_id = auth.uid()` | `profile_id = auth.uid()` | `profile_id = auth.uid()` | none | **No** |
| `coach_conversations` | ✅ | `profile_id = auth.uid()` | `profile_id = auth.uid()` | `profile_id = auth.uid()` | `profile_id = auth.uid()` | **No** |
| `coach_messages` | ✅ | `EXISTS(...coach_conversations WHERE id=conversation_id AND profile_id=auth.uid())` | same EXISTS pattern | none | none | **No** — correct transitive-ownership pattern |
| `opportunity_applications` | ✅ | `user_id = auth.uid()` | `user_id = auth.uid()` | — | `user_id = auth.uid()` | **No** |
| `storage.objects` (`resumes` bucket) | ✅ | `(storage.foldername(name))[1] = auth.uid()::text` | same | same | same | **No** — private bucket, path-prefix ownership check on every operation |

**No table was found using `using (true)`, a missing `WHERE` clause, or otherwise exposing all rows.** Every ownership check correctly uses `auth.uid()` (Postgres's built-in "who is the current JWT's subject" function, populated by PostgREST from the bearer token) rather than a client-suppliable column.

**Can a client manipulate server-controlled fields?** One relevant case: `public.profiles` has AI-derived columns (`profile_score`, `ai_profile_summary`, `last_profile_analysis`) that the schema comment explicitly says should only ever be written by the backend. **RLS does not enforce this at the column level** — Postgres RLS is row-level, not column-level, so the existing `UPDATE ... USING (id = auth.uid())` policy technically permits an authenticated user to `PATCH` their own profile row and set `profile_score` to anything they want directly via PostgREST, since the frontend's own `saveOnboardingProfile()` upsert already writes to that row anyway. **This is a real, concrete finding** (Medium): a user could inflate their own `profile_score`/`ai_profile_summary` by calling PostgREST directly (bypassing the app's UI, which is trivial — Supabase's REST API is directly reachable with the same anon key + user JWT any browser DevTools session already has). Impact is limited to self-serving data integrity (a user can only lie to themselves/be shown a wrong score, not to the AI-analysis backend which recomputes it) rather than reading/modifying anyone else's data, but if `profile_score` or `ai_profile_summary` are ever surfaced to *other* users (a leaderboard, a recruiter view, matching logic) this becomes a real integrity issue.

**Concrete attack scenarios that would succeed if a policy were wrong (for context — none of these currently work):**
- If `experiences` used `using (true)` instead of `profile_id = auth.uid()`: `GET /rest/v1/experiences` with any valid logged-in JWT would return every user's work history. **Not possible today — confirmed correct policy.**
- If `saved_opportunities` INSERT used `with check (true)` instead of `user_id = auth.uid()`: a user could `POST` a row with `user_id` set to someone else's UUID, silently adding to another user's saved list (or corrupting their data at insert time). **Not possible today.**
- If `coach_messages` had no policy at all (RLS enabled, zero policies = correctly default-deny) but a *different* table forgot `alter table ... enable row level security` entirely: that table would be **completely public** to anyone with the anon key, which is public by design. **Every table checked has RLS enabled** — none were found missing it.

---

## 7. FastAPI backend JWT verification — empirically tested, not just read

This was the single most important thing to verify precisely, per your explicit ask ("determine whether the backend ever merely DECODES a JWT without VERIFYING its signature — that would be critical"). I didn't just read `backend/app/core/security.py` — I extracted its exact verification call and ran it against the real installed `PyJWT==2.3.0` (`backend/.venv`) with four forged tokens.

**Result: the backend genuinely, cryptographically verifies every token. It is not merely decoding.**

```
Forged HS256 token signed with the WRONG secret → InvalidSignatureError (rejected)
Expired token                                   → ExpiredSignatureError (rejected)
Token missing "sub" claim                        → MissingRequiredClaimError (rejected)
Token with wrong "aud" claim                     → InvalidAudienceError (rejected)
```

Checked individually:
- **Signature verification**: ✅ confirmed above — a token signed with the wrong secret is rejected, meaning `jwt.decode()` is genuinely checking the signature, not skipping it.
- **Algorithm validation**: partially — see the finding below.
- **Expiration**: ✅ enforced twice over — `options={"require": ["exp", "sub"]}` forces the claim to be present, and PyJWT independently validates it's not in the past.
- **Audience**: ✅ enforced (`audience=settings.SUPABASE_JWT_AUDIENCE`, defaults to `"authenticated"`, matching what Supabase actually issues).
- **Subject**: ✅ `verify_token()` (`security.py`) has its own explicit `if not claims.get("sub")` check *in addition to* PyJWT's `require` option — belt-and-braces.
- **JWKS/key rotation/`kid` handling**: uses `PyJWKClient`, the standard library-supported pattern for Supabase's newer asymmetric ("JWT Signing Keys") mode — matches by `kid` against Supabase's real published key set, cached with re-fetch on cache miss (i.e., on rotation).
- **Missing token**: `api/deps.py`'s `get_current_user` raises `UnauthorizedError` (401) if no `Authorization` header is present — correct, uniform error shape.
- **Malformed token**: `jwt.get_unverified_header()` failure is caught and converted to a 401, not a 500 — correct, no internals leaked.

**Finding — Medium, hardening not a live exploit: the algorithm used to verify a token is chosen from the token's own (attacker-controlled) header, not from a fixed server config.**

```python
# security.py
algorithm = header.get("alg") or settings.SUPABASE_JWT_ALGORITHM
...
return jwt.decode(token, signing_key, algorithms=[algorithm], ...)
```

This is the shape of the classic JWT "alg confusion" / "`alg: none`" vulnerability family — letting the token dictate how it should be checked is a well-known anti-pattern (OWASP JWT Cheat Sheet explicitly warns against it). I tested the two concrete variants of that attack directly:

1. **`alg: none` forgery** (attacker crafts an unsigned token, claims `alg: none`, sets `sub` to any victim's UUID): **blocked**, but not by this code — by PyJWT itself. Verified empirically: `jwt.decode(forged_none_alg_token, key=<anything>, algorithms=['none'])` raises `InvalidKeyError: When alg = "none", key value must be None.` Since `security.py` always passes a real key object into `signing_key` (either the configured secret, or a JWKS-resolved key — never `None`), PyJWT 2.3.0 refuses the combination outright.
2. **RS256→HS256 key-confusion** (attacker HMAC-signs a forged token using Supabase's *public* JWKS key bytes as if it were a shared secret, hoping the verifier reuses that same public key value as an HMAC secret): **not applicable in this codebase** — the HS-family branch always uses `settings.SUPABASE_JWT_SECRET` (a private, server-only value) as the key, and never touches JWKS-derived key material. The two code paths never share key material, which is exactly what prevents this attack class.

**So: not exploitable today, verified rather than assumed — but still worth fixing**, because both of those protections currently live in "PyJWT happened to guard against this" rather than "this code guards against this." A future PyJWT version, a switch to a different JWT library, or a copy-paste of this pattern elsewhere without the same library-level guard would silently reintroduce the vulnerability. **Recommended fix**: pin `algorithms=[...]` to a fixed, server-config-driven allow-list (e.g., derive it from `settings.SUPABASE_JWT_ALGORITHM` plus an explicit `{"RS256", "ES256"}` set for the JWKS branch — never `[header_value]`), and add an explicit `if algorithm == "none": raise UnauthorizedError(...)` guard so the protection doesn't depend on library internals at all. This is a one-function change in `security.py`, no callers affected.

**Downgrade risk from supporting both HS256 and JWKS?** No meaningful downgrade risk found — an attacker cannot force a token down the weaker path, because a real HS256-signed token requires the actual `SUPABASE_JWT_SECRET`, and a real JWKS-verifiable token requires a private key Supabase controls; there's no scenario where supporting both lets an attacker pick whichever is easier to forge, since neither is forgeable without the actual corresponding secret/key.

---

## 8. Authorization (IDOR) audit — separate from authentication

Two backend "layers" exist and were both audited:

**Layer A — the eight scaffold routers** (`routes/profiles.py`, `opportunities.py`, `roadmap.py`, `simulation.py`, `chat.py`, `analytics.py`, plus `auth.py`): every handler is a one-line `raise NotImplementedYetError()` (HTTP 501). They do require `CurrentUser` (so an unauthenticated caller still gets 401 before ever reaching the 501), but there is no business logic to have an IDOR in yet.

**Layer B — the real, implemented feature modules** (`recommendations.py`, `app/profile_analysis/`, `app/career_roadmap/`, `app/career_simulation/`, `app/ai_coach/`) — this is where an IDOR would actually matter, and where I focused. Every single one of these routes derives the acting user's identity **exclusively from the verified JWT** (`user.id` from `CurrentUser`), **never** from a client-supplied `user_id` field in the request body or query string. For the two modules that also take a resource ID in the path (`GET/DELETE /career-simulation/{simulation_id}`, `GET/DELETE/POST /conversations/{conversation_id}...`), I traced the repository layer's actual SQL construction:

```python
# career_simulation/services/repository.py
def get_by_id(self, simulation_id: str, profile_id: str) -> dict | None:
    ... .eq("id", simulation_id).eq("profile_id", profile_id) ...   # both, not just id

def delete_simulation(self, simulation_id: str, profile_id: str) -> None:
    ... .delete().eq("id", simulation_id).eq("profile_id", profile_id).execute()
```

```python
# ai_coach/services/repository.py — same pattern
def get_conversation(self, conversation_id: str, profile_id: str) -> dict | None:
    ... .eq("id", conversation_id).eq("profile_id", profile_id) ...
```

`ai_coach/services/coach_service.py:139/163` additionally calls `repository.require_conversation(conversation_id, user_id)` — which 404s (not 403s, deliberately, per the code comment — avoids confirming to a prober that a given ID even exists) — **before** ever calling `list_messages()`, so message history for a conversation you don't own is unreachable at the service layer *and* would separately be blocked by the `coach_messages` RLS `EXISTS(...)` policy even if that app-level check were ever removed by mistake.

**Verdict: no IDOR found.** Every ID-parameterized endpoint enforces ownership twice — once explicitly in application code (`.eq("id", x).eq("profile_id"/"user_id", caller_id)`), and again independently at the database layer (RLS, since these queries execute through `get_supabase(access_token=...)`, the user-scoped client, not the service-role client). This directly resolves the "unverified, backend-dependent" IDOR finding the old `PENTEST_REPORT.md` flagged (finding #4) as something it couldn't check from the frontend alone — it's now checked, and it's clean.

**Authorization vs. authentication, stated explicitly**: authentication (`CurrentUser`) answers "is this a valid Supabase user"; every route above additionally answers "does *this* Supabase user own *this* specific row" via the `.eq(..., profile_id)` pattern — the two are correctly not conflated.

---

## 9. Frontend route protection audit

`AppShell.jsx` gates protected screens behind a `status` state (`'loading' | 'signed-out' | 'ready'`), set from `supabase.auth.getSession()` on mount and kept live via `onAuthStateChange('SIGNED_OUT')`. `App.jsx` itself has **no router-level guard** — any of `/discover`, `/career-ai`, `/profile`, `/saved` will render `<AppShell>`, which then internally decides whether to show a sign-in prompt or real content.

**This is explicitly, correctly understood as UX-only in the code's own comments** (`AppShell.jsx`, right above the `onAuthStateChange` effect): *"Client-side route protection is only ever a UX convenience here — the real enforcement is Supabase RLS."* I found nothing that contradicts that comment — no sensitive read/write anywhere in the frontend skips RLS (every Supabase call goes through the single anon-key client), and no backend route trusts a frontend-supplied identity claim instead of re-verifying the JWT itself. So: **the frontend guard is exactly what it claims to be, nothing more, and nothing sensitive incorrectly depends on it.**

One related, minor gap: because the guard is per-screen rather than centralized, a future screen added to `SHELL_ROUTES` without wiring into `AppShell`'s existing `status` check would silently render with no gate — not a vulnerability today, but worth a lint rule or router-level wrapper as the app grows, precisely because "remember to check `status`" doesn't scale as a convention.

---

## 10. Secrets and environment variables audit

Grepped the entire repository (excluding `node_modules`, `.venv`, `__pycache__`) for service-role key shapes, JWT secrets, API keys, and JWT-looking strings.

- **Frontend `.env`** (`frontend/.env`): `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (a `sb_publishable_...` key — Supabase's new-style publishable key, safe client-side by design), `VITE_API_BASE_URL`. **No service-role key, no JWT secret, nothing sensitive.** Correct.
- **Backend `.env`** (`backend/.env`): holds `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `DATABASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` — all present, all real-looking values, all appropriately **backend-only**.
- **Cross-contamination check**: grepped `frontend/src` for `service_role`, `SUPABASE_SERVICE_ROLE_KEY`, `sk-`, and JWT-secret-shaped strings — **zero matches**. The service-role key never reaches frontend code or the browser bundle.
- **Automated regression coverage already exists for this**: `backend/tests/test_recommendations_api.py:211-212` explicitly asserts `"service_role" not in response.text.lower()` and `"supabase_service_role_key" not in response.text.lower()` on API responses — a real, if narrow, safety net against this exact leak. Worth extending to every response-returning test, not just recommendations.
- **`.gitignore`**: correctly excludes `.env` and `.env.*`, with an explicit `!.env.example` carve-out — so as long as this convention is honored going forward, secrets won't land in git. (There's no `.git` repository present in this checkout to audit *history* for a prior accidental commit — worth a one-time `git log -p -- '*.env'`-style check on whatever remote actually hosts this repo, which this session can't reach.)
- **Production secret handling**: not verifiable from the repo — `Dockerfile`/deploy config should inject `backend/.env`'s values via the hosting platform's secret manager rather than baking a `.env` file into an image; that's a deployment-process question outside this codebase.
- **Immediate operational note, not a code defect**: earlier in this session, `https://umjcctflwjirwqwpihez.supabase.co` (the exact URL in `frontend/.env`) returned `DNS_PROBE_FINISHED_NXDOMAIN` in the user's real browser — the project this app points at does not currently resolve, which blocks **all** authentication (Google and email/password both) until the Supabase project is confirmed live and `frontend/.env`/`backend/.env` point at its real, current URL and keys. This is a configuration/deployment issue, not a design flaw, but it means auth is not currently functional end-to-end regardless of any code-level finding above.

---

## 11. Session security audit

- **Access-token lifetime**: a Supabase project setting (JWT expiry, default 1 hour), not app-controlled — verify it in the dashboard.
- **Refresh-token lifetime/rotation**: Supabase-managed; refresh tokens rotate automatically on use, with reuse-detection on the platform side. No app code involved, none needed.
- **Behavior after inactivity**: access token silently refreshes in the background as long as the tab/app is open and the refresh token hasn't expired; once the refresh token itself expires (inactivity beyond its lifetime), the next `getSession()`/API call fails and `onAuthStateChange('SIGNED_OUT')` fires, dropping the UI to signed-out — correct.
- **After logout**: `signOut()` both clears local storage and revokes the refresh token server-side (SDK behavior) — a captured old token can't be replayed to mint new access tokens after logout.
- **After password change**: no reset/change flow exists yet (see §4), so untestable; Supabase's default does *not* auto-revoke other active sessions on a password change unless the app explicitly requests a global sign-out — worth deciding deliberately once a reset flow is built, not left as a default.
- **Across multiple tabs**: `@supabase/auth-js` uses a `BroadcastChannel` keyed on `storageKey` (confirmed in `GoTrueClient.js:256-258`) to sync auth state across tabs of the same origin — logging out in one tab correctly signs out the others.
- **After token expiration / refresh failure**: same `SIGNED_OUT` path as above.
- **Stale sessions**: none found staying active past what Supabase itself considers valid — no app-side "remember me forever" override exists.
- **Unnecessary token exposure to app code**: the app never reads `session.access_token` and does anything unusual with it (logs it, puts it in a URL) except the one legitimate case — forwarding it as `Authorization: Bearer` to the FastAPI backend (`services/api/client.js`) and passing it through to `AccessToken`-typed backend dependencies so RLS applies as that user. That's correct, necessary use, not exposure.

**Is this appropriate for production?** Yes, for a standard consumer-facing SPA. If this app ever needs a materially higher security bar (e.g., handling regulated financial data), the next step up would be moving token storage off `localStorage` entirely via a custom `storage` adapter or a BFF-proxied httpOnly-cookie session — but that's a substantial architecture change, not something this audit found a concrete need for today.

---

## 12. Authentication error-handling audit

`friendlyAuthMessage()` in `auth.js:16-34` maps Supabase's raw errors to user-facing text:

| Supabase's raw message | This app shows | Leaks info? |
|---|---|---|
| "Invalid login credentials" | "Incorrect email or password." | **No** — correctly doesn't reveal which is wrong |
| "Email not confirmed" | "Please confirm your email before logging in…" | **Yes, mildly** — confirms the email is a real, registered (if unconfirmed) account. Standard trade-off most products accept for UX; flagging so it's a deliberate choice, not an oversight |
| "User already registered" (signup) | "An account with this email already exists. Try logging in instead." | **Yes, by design** — this is the app *overriding* Supabase's own anti-enumeration behavior (which returns success + empty `identities` specifically to avoid this disclosure) in favor of a clearer signup UX. Worth a conscious call: if user enumeration is a concern for this product (e.g., a sensitive user base), consider always showing "check your email to continue" instead, matching Supabase's own anti-enumeration intent |
| Rate-limit errors | "Too many attempts. Please wait a moment and try again." | No |
| Password too short | "Password must be at least 6 characters." | No |

None of the examples you flagged as bad ("Email exists in our database", "This account belongs to Google") appear anywhere in the code — the messages found are reasonable, just with the one deliberate enumeration trade-off on signup noted above.

**Backend error handling** (`middleware/error_handler.py`): unhandled exceptions return a fixed `{"code":"internal_error","detail":"Something went wrong."}` with a `request_id` for support correlation — no stack trace, no internal detail, ever, regardless of what actually broke. `UnauthorizedError` messages (`security.py`) are similarly generic ("Invalid authentication token.", "Session expired. Please sign in again.") — none leak whether a token failed due to bad signature vs. wrong audience vs. expiry, which is correct (an attacker probing for which check failed learns nothing).

---

## 13–14. Password reset and email verification

**Password reset**: confirmed absent (see §4) — for a product offering email/password login, this is a real production gap. Users *will* forget passwords; without this, the only recovery path is a manual support request against the Supabase dashboard, which doesn't scale and isn't self-service. **This is the single highest-priority functional gap in this audit** (see remediation plan).

**Email verification ("Confirm email")**: a Supabase dashboard toggle, not app code — the app correctly handles both states, but which one is *live* couldn't be confirmed from this repo (and couldn't be checked live this session either, since the Supabase project URL is currently unreachable — see §10). Trade-off, for the record:
- **ON**: stronger identity assurance (reduces spam/throwaway accounts, ensures password-reset emails are deliverable), at the cost of one extra step before a new user reaches onboarding, and it's what makes the "already registered" disclosure in §12 meaningful (an unconfirmed duplicate signup is otherwise indistinguishable from a fresh one).
- **OFF**: frictionless signup, but an unverified email address means password-reset (once built) and any transactional email are unreliable, and it's easier to mass-create throwaway accounts.
- **What happens to an unverified user today**: with confirmation ON, `signUp()` succeeds but returns no session (`needsEmailConfirmation: true`, `AuthDialog.jsx`), so they simply can't do anything until they click the email link — there's no "half-authenticated" state that leaks access.

---

## 15. Account lifecycle audit

- **Signup → email verification → login → logout**: all traced above, all real.
- **Password reset, email change, account deletion**: all absent (§4, §13).
- **OAuth linking**: Supabase-config-dependent, unverified from this repo (§4).
- **Disabled/deleted `auth.users` rows**: `public.profiles.id` references `auth.users(id) on delete cascade` (`schema/001_profiles.sql`) — deleting a Supabase auth user automatically deletes their `profiles` row (and, transitively, their `experiences` via the same cascade pattern). **No orphaned profile rows from that direction.**
- **The other direction — profiles are *not* auto-created by a trigger**, and you specifically flagged this as worth scrutinizing. Confirmed: no `on_auth_user_created`/`handle_new_user` trigger exists anywhere in `supabase/schema/`. A `profiles` row is only written when `saveOnboardingProfile()` (`profiles.js:135`) runs, at the end of onboarding. **Is this a security problem? No** — RLS is keyed off `auth.uid()`, not off whether a `profiles` row exists, so a user with an `auth.users` row but no `profiles` row yet simply can't read/write anything in `profiles`/`experiences` beyond their own (currently nonexistent) row; there's no privilege gap. **Is it a data-integrity/product problem? Mildly** — it does mean "signed up but never finished onboarding" is an unbounded, silent state: those `auth.users` rows exist indefinitely with no corresponding profile, no way to query "how many people signed up but never finished," and no automatic cleanup. Not a security finding, but worth a lightweight follow-up (either a trigger that stamps a bare `profiles` row on signup, so "signed up" and "has a profile row" become the same event, or a periodic report on the gap) if abandoned-signup tracking ever matters for the product.

---

## 16. Production-readiness classification

| Area | Status | Severity | Problem | Required Fix |
|---|---|---|---|---|
| Supabase Auth (delegation) | ✅ Correct | — | None — correctly the sole identity authority | None — do not build custom auth |
| Password handling | ✅ Correct | — | App never touches passwords; Supabase hashes/stores them | None |
| JWT verification | ⚠️ Minor hardening | Medium | Algorithm chosen from the token's own header rather than a fixed allow-list (not exploitable today against installed PyJWT, empirically verified) | Pin `algorithms=[...]` to server config; explicitly reject `alg: none` — `backend/app/core/security.py` |
| Refresh tokens | ✅ Correct | — | Fully Supabase-managed | None |
| Session storage | ⚠️ Standard SPA trade-off | Low | `localStorage`, readable by any same-origin JS (no current XSS vector, but a standing requirement to stay that way) | Keep the app XSS-free (§6); no code change required today |
| Google OAuth | ⚠️ Minor hardening | Medium | Implicit flow instead of PKCE (library default, unconfigured) | `auth: { flowType: 'pkce' }` in `client.js` |
| RLS | ✅ Correct (one minor gap) | Low | `profiles` UPDATE policy allows a user to write server-computed columns (`profile_score`, `ai_profile_summary`) on their own row via raw PostgREST | Add a trigger/column-level check restricting those columns to service-role writes only, if they're ever shown to other users |
| FastAPI JWT verification | ✅ Correct, empirically tested | — | Genuinely verifies signature/exp/aud/sub; not a bare decode | None required; see algorithm-pinning hardening above |
| Authorization (IDOR) | ✅ Correct | — | Every ID-parameterized route double-checks ownership (app layer + RLS) | None found |
| Password reset | ❌ Missing | **High** | No self-service recovery exists at all | Implement `resetPasswordForEmail` + a `/auth/recovery` callback screen + `updateUser({password})` |
| Email verification | ⚠️ Config-dependent | — | Handled correctly in code either way; live setting unverified | Confirm the Supabase dashboard setting matches intent |
| Secrets | ✅ Correct | — | No leakage found; service-role key correctly backend-only | Extend the existing leak-detection test pattern to more endpoints |
| Route protection | ✅ Correct (UX-only, as intended) | — | Real enforcement is RLS, matches the code's own stated intent | None required; consider centralizing the per-screen guard as the app grows |
| Error handling | ✅ Correct (one deliberate trade-off) | Low | Signup's "already registered" message overrides Supabase's own anti-enumeration default | Decide deliberately per your enumeration risk tolerance |
| Rate limiting / abuse | ❌ Missing at app layer | High | `middleware/rate_limit.py` is an explicit no-op TODO; expensive LLM-backed routes have zero app-level throttling | Implement the token-bucket the code's own TODO describes, at minimum on `career-ai/*` routes |
| CAPTCHA | ❌ Missing | Medium | No bot/abuse protection on signup | Wire up `captchaToken` (hCaptcha/Turnstile) via Supabase's built-in support |
| Account deletion | ❌ Missing | Low–Medium | No self-service or admin deletion path | Add before a real public launch, for support load and any right-to-erasure obligation |

---

## 17. On not redesigning the architecture

To directly restate this, since it's the crux of what you asked: **Supabase Auth is correctly and fully implemented as the sole authentication authority in this application, and the correct path forward is to keep delegating to it — not to introduce bcrypt, custom JWT issuance, a refresh-token table, or a session table.** Every piece of evidence gathered in this audit points the same direction: the frontend never touches a password or constructs a token, the backend only *verifies* what Supabase issued (and does so with real, tested, cryptographic verification), RLS makes the database itself the actual enforcement boundary rather than trusting either the frontend or the backend's business logic alone, and the one place a custom table exists (`public.profiles`) deliberately stores *profile data*, not credentials, keyed by (not duplicating) `auth.users.id`. There is no concrete requirement uncovered in this audit that Supabase's own auth system cannot satisfy — the gaps found (password reset, rate limiting, PKCE, CAPTCHA) are all things Supabase either already supports natively (password reset, CAPTCHA integration, PKCE — all are configuration/one-line-of-code away) or that belong in application middleware regardless of the auth provider (rate limiting on expensive routes). None of them are a reason to build a parallel auth system.

---

## 18. Remediation plan

### 1. Implement password reset
- **File(s)**: `frontend/src/services/supabase/auth.js`, `frontend/src/components/auth/AuthDialog.jsx` ("Forgot?" button currently has no handler), a new `frontend/src/pages/ResetPasswordScreen.jsx`, `frontend/src/App.jsx` (route for `/auth/recovery` or similar)
- **Problem**: no self-service password recovery exists; the UI implies one ("Forgot?") but it does nothing
- **Why it matters**: users will lock themselves out; no scalable recovery path exists today
- **Fix**: `supabase.auth.resetPasswordForEmail(email, { redirectTo: `${origin}/auth/recovery` })` on submit; a recovery screen that calls `supabase.auth.updateUser({ password })` once Supabase redirects back with a recovery session
- **Layer**: Frontend
- **Priority**: High
- **Required before production**: Yes, for any user relying on email/password login

### 2. Pin JWT algorithm verification to server config
- **File**: `backend/app/core/security.py`, `decode_token()`
- **Problem**: `algorithms=[header.get("alg")]` trusts the token's own header to select its verification algorithm
- **Why it matters**: classic alg-confusion/`alg:none` anti-pattern; not exploitable today (empirically verified against installed PyJWT), but fragile — safety currently depends on a third-party library's internal guard rather than this code's own logic
- **Fix**: replace the dynamic `algorithms=[algorithm]` with a fixed allow-list from `settings` (e.g. `{"HS256"}` or `{"RS256","ES256"}` depending on which branch), and add `if algorithm == "none": raise UnauthorizedError(...)` explicitly before doing anything else with the header
- **Layer**: Backend
- **Priority**: Medium
- **Required before production**: Recommended, not launch-blocking (no live exploit found)

### 3. Switch OAuth to PKCE flow
- **File**: `frontend/src/services/supabase/client.js`
- **Problem**: `createClient()` has no `auth` options, so it defaults to `flowType: 'implicit'`
- **Fix**: `createClient(supabaseUrl, supabaseAnonKey, { auth: { flowType: 'pkce' } })`
- **Layer**: Frontend
- **Priority**: Medium
- **Required before production**: Recommended

### 4. Implement backend rate limiting on expensive/auth-adjacent routes
- **File**: `backend/app/middleware/rate_limit.py` (currently a documented no-op)
- **Problem**: zero app-level throttling on any route, including the LLM-backed Career AI endpoints
- **Fix**: the token-bucket per `(user_id, route)` the code's own docstring already describes, backed by `settings.REDIS_URL`
- **Layer**: Backend
- **Priority**: High (cost/abuse risk on LLM routes specifically)
- **Required before production**: Yes, before any real user load on `career-ai/*`

### 5. Add CAPTCHA to signup/login
- **File**: `frontend/src/services/supabase/auth.js` (add `captchaToken` to the `signUp`/`signInWithPassword`/`signInWithOAuth` option objects), plus enabling it in the Supabase dashboard
- **Problem**: no bot/abuse protection on account creation
- **Layer**: Frontend + Supabase Dashboard
- **Priority**: Medium
- **Required before production**: Recommended for a public-signup product

### 6. Restrict server-computed profile columns from client writes
- **File**: `supabase/policies/001_rls.sql` (the `profiles` UPDATE policy), or a `BEFORE UPDATE` trigger
- **Problem**: a user can currently set their own `profile_score`/`ai_profile_summary` directly via PostgREST, since RLS is row- not column-scoped
- **Fix**: a trigger that resets those specific columns to their previous value unless the request is running as service-role, or split them into a separate table only the backend can write
- **Layer**: SQL / Supabase Dashboard
- **Priority**: Low–Medium (depends on whether these fields are ever shown to anyone but the user themselves)
- **Required before production**: Only if these fields become externally visible/consequential

### 7. Add frontend defense-in-depth on `apply_url`
- **File**: `frontend/src/pages/AppShell.jsx:561,593`
- **Problem**: renders DB-sourced `applyUrl` as an `href`/`window.open` target with no client-side scheme check; the ingestion pipeline already rejects non-http(s) URLs server-side (`backend/app/ingestion/utils/validation.py`), but the frontend has no independent backstop
- **Fix**: `const safeUrl = /^https?:\/\//i.test(item.applyUrl) ? item.applyUrl : '#'` before using it as a link target
- **Layer**: Frontend
- **Priority**: Low (already mitigated server-side; this is belt-and-braces)
- **Required before production**: No, recommended

### 8. Implement account deletion
- **File**: new backend route + frontend settings UI
- **Problem**: no self-service or admin path to delete an account
- **Layer**: Backend (using `get_admin_supabase().auth.admin.delete_user()`) + Frontend
- **Priority**: Low–Medium
- **Required before production**: Recommended, not strictly blocking for an initial launch

### 9. Confirm Supabase dashboard settings this repo cannot verify
- **Not a code file** — a checklist to run directly in the Supabase dashboard: (a) the live Supabase project resolves and matches `frontend/.env`/`backend/.env` (currently broken — see the DNS finding in §10); (b) "Confirm email" is set to the intended value; (c) the password minimum-length policy is ≥ what the frontend implies (6); (d) Google OAuth redirect URLs are exactly your dev + prod origins, no wildcards; (e) OAuth account-linking behavior matches your intent for same-email, different-provider signups
- **Layer**: Supabase Dashboard
- **Priority**: High
- **Required before production**: Yes

---

## Direct answer to your closing question

**Are we handling authentication and login correctly for a production-level application, and do we need to implement bcrypt, our own JWT generation, or our own session management?**

Yes, you're handling it correctly at the architectural level, and no, you do not need bcrypt, custom JWT generation, or custom session management — building any of those would be a step backward, not forward. Supabase Auth genuinely owns password storage/hashing, token issuance, refresh-token rotation, and session persistence; the FastAPI backend genuinely (verified empirically, not assumed) re-verifies every token's cryptographic signature rather than trusting the frontend; and PostgreSQL RLS — checked table by table, all sixteen of them — is the real, correctly-configured enforcement boundary underneath both. What stands between this and a fully production-hardened launch is a short, concrete list, not an architecture change: build password reset (the one missing feature users will actually hit), turn on the rate-limiting the code already has a placeholder for, flip OAuth to PKCE, and add CAPTCHA — plus fixing the current Supabase project connectivity issue so any of this works at all right now.
