# OwnMove Frontend — Production Readiness Audit

**Scope:** `frontend/` (92 files, ~13,800 lines). Read-only inspection — no fixes applied, per instruction.
**Not verifiable from this sandbox** (disclosed up front, not assumed away): git history of `frontend/.env` (no git repo in this mount), actual Supabase RLS policy definitions and storage bucket policies (only inferable from client-side query patterns), a real production `vite build` output (this sandbox's Rolldown binary doesn't match its CPU arch), and whether `framer-motion` actually installed cleanly on your machine.

---

## 1. Security Audit

**No exposed secrets.** Grepped for service-role keys, private keys, API secret patterns (`sk-`, `AIza`, `ghp_`, `xox`, etc.) — none found. The only key checked into `.env` is the Supabase **anon/publishable** key (`sb_publishable_...`), which is safe to ship client-side by design; `.gitignore` correctly excludes `.env`/`.env.*`.

**Critical — the email/password login form is fake.** `AuthDialog.jsx`'s `handleDummyLogin` never calls Supabase. It just shows "Demo login accepted," waits 650ms, and redirects — no account is created, no session exists. Google is the only real auth path (`startGoogleSupabaseAuth` → `supabase.auth.signInWithOAuth`). Consequence: anyone who "signs up" with email/password lands on `/discover` or `/onboarding` with **no session**, and every Supabase write those screens make (`saveOnboardingProfile`, `uploadResume`, `saveOpportunity`, etc.) will throw "You need to be signed in" or be silently blocked by RLS. This is the single biggest reason not to launch today.

**GitHub / LinkedIn buttons are non-functional in production.** They resolve through `startProviderAuth` → `buildConfiguredAuthUrl`, which reads `VITE_GITHUB_AUTH_URL` / `VITE_LINKEDIN_AUTH_URL`. Neither is set in `.env`, so clicking them shows a "sign-in setup needed" panel with internal setup steps — meant for developers, not end users.

**No open-redirect.** `postLoginRedirect` (localStorage) is only ever set to hardcoded internal paths (`/profile`, `/discover#programs`, etc.) from three call sites — never derived from a URL query param or other attacker input. `useClientNavigation` also correctly rejects `//`-prefixed hrefs and external links. Verified clean.

**No XSS/injection surface.** Zero `dangerouslySetInnerHTML`, `eval`, or `new Function` anywhere in `src`. No unsanitized markdown rendering.

**Supabase usage is anon-key-only.** One `createClient()` call, using the anon key; no service-role key anywhere in frontend code (correct — that belongs only on the backend). All user-scoped queries (`saved_opportunities`, `profiles`, `experiences`, `opportunity_applications`) rely on `auth.uid()` via RLS rather than passing user IDs manually — good pattern, but I could not confirm from the frontend alone that RLS is actually turned on for every one of these tables and the `resumes` storage bucket. Confirm this directly in the Supabase dashboard before launch.

**`.env` has a stray line.** Line 3 is a bare, unassigned value (`Iv23liKSAnamoamVb8PW`) — not `KEY=value`, not read anywhere via `import.meta.env`. It matches the shape of a GitHub App client ID. It's inert (nothing consumes it), but it's leftover clutter from an abandoned setup step. `.env.example` is also out of sync — it doesn't list `VITE_GOOGLE_CLIENT_ID`/`VITE_GOOGLE_REDIRECT_URI` at all, so a teammate bootstrapping from the example wouldn't know Google needs them (in practice, unused today since Google goes through Supabase, not these vars — see below).

**Dead OAuth vars.** `VITE_GOOGLE_CLIENT_ID` and `VITE_GOOGLE_REDIRECT_URI` are set in `.env` but never read by any file — the real Google flow goes through Supabase's `signInWithOAuth`, not a hand-rolled client-id/redirect flow. Harmless, but dead configuration.

**No CSRF/clickjacking/CORS issues found in frontend code** — these are primarily backend/server-header concerns (`X-Frame-Options`, CORS allow-list) outside this frontend's control; `vite.config.js` shows awareness of the backend's CORS allow-list (`strictPort: true` specifically to avoid silently drifting off port 5173, which the backend's CORS config expects).

## 2. Frontend Review

- **Dead code:** `src/_legacy/DashboardScreen.jsx`, `DiscoverScreen.jsx`, `googleAuth.js` (~48KB) — confirmed via a full-codebase import grep to be completely unreferenced. Delete before launch.
- **Lint is not clean.** `npx eslint .` reports 6 real errors on the current tree:
  - `AppShell.jsx`: unused `isRefreshing`, `handleRefresh`, `dateStr`, `backHref` — half-finished/dead logic.
  - `CareerSimulationDashboard.jsx`: caught `error` never used.
  - `IntelligenceSection.jsx`: `setState` called synchronously inside a `useEffect` body (line 251, the typewriter-reset effect) — the exact cascading-render anti-pattern `react-hooks` flags. Worth fixing; low risk in practice since it's a self-contained animation reset, but it's a real anti-pattern, not a style nit.
- **No code-splitting anywhere.** Zero `React.lazy`, `Suspense`, or dynamic `import()` in the whole codebase — Career AI, Certifications, Learning Journey, and the entire landing page all ship in one bundle on first load.
- **Images:** all `<img>` tags have `alt` text except two avatar images in `TestimonialSection.jsx` (lines 96, 114) — minor accessibility gap.
- **`request()`'s AbortSignal plumbing is unused.** `services/api/client.js` accepts a `signal` option, but nothing in the app ever passes one — no request cancellation exists anywhere, including in Discover's category-switch fetches.
- No `console.log`/`debugger`/`TODO`/`FIXME` found anywhere (verified by grep) — this part of the codebase is genuinely clean.

## 3. User Experience

- The fake-login issue above is the biggest UX risk: a new user filling out the signup form will believe they have an account, then hit confusing "sign in to continue" or silent failures the first time a feature needs a real session.
- GitHub/LinkedIn buttons showing a developer setup checklist to end users is a real, visible rough edge — hide these or label them "coming soon" instead.
- Elsewhere, loading/empty/error states for Discover and the Career AI dashboards were built out deliberately across many prior iterations in this project and are in reasonable shape; I did not find missing loaders or broken transitions in the files reviewed.

## 4. Authentication

- Real session state comes only from Supabase (Google OAuth). `AuthCallbackScreen.jsx` correctly waits for `getSession()`, checks for an existing profile to route returning vs. new users, and handles the no-session case by bouncing to `/`.
- Route "protection" is not enforced at the router level (`App.jsx` has no guard) — it's enforced inside `AppShell` via a `status` state (`loading` / `signed-out` / ready) that renders a sign-in prompt instead of app content. Functionally this works today, but it's easy to regress: a new screen added later could forget to check `status`. The real backstop is (and must remain) Supabase RLS on every table/bucket.
- No session-expiry/refresh handling was found beyond what Supabase's client does automatically — acceptable, since `supabase-js` handles token refresh internally.

## 5. Supabase

- Client init (`services/supabase/client.js`) is correct and warns loudly in dev if env vars are missing, rather than failing silently.
- Every user-scoped table read/write goes through `auth.uid()`-implicit RLS (session-derived), never a manually-passed user ID — the right pattern, assuming RLS is actually enabled server-side (unverifiable from here).
- `uploadResume` has no client-side file-size or file-type validation before uploading to the private `resumes` bucket — not an XSS/security risk (bucket is private, access is via time-limited signed URL), but an availability/cost gap (a user could upload an arbitrarily large or arbitrary-type file).
- No direct evidence of anonymous/public read access being granted anywhere in frontend code — all reads go through the same authenticated Supabase client.

## 6. Network

- All backend calls funnel through one `request()` function with consistent error typing (`ApiError`) and sensible network-failure handling.
- **No retries, no timeouts, no request cancellation** anywhere in the app (frontend or Supabase calls) — a slow/flaky connection produces a hard error rather than a retry.
- `VITE_API_BASE_URL` **defaults to `http://localhost:8000`** and is genuinely called by 4 live features (Profile Analysis, Career Roadmap, Career Simulation, AI Coach — confirmed via caller grep). If this isn't set to the real production API origin at deploy time, all four Career AI dashboards will try to reach `localhost:8000` from users' own browsers and fail outright. This is a deploy-config risk, not a code bug, but it will silently break a quarter of the product if missed.
- The `services/api/client.js` header comment ("Nothing in the app calls this yet") is stale/incorrect — it's actively called by 4 dashboards. Minor, but a sign docs have drifted from code.

## 7. Production Checklist

| Item | Status |
|---|---|
| console.logs | Clean — only 2 legitimate `console.warn`s for missing env vars |
| debugger statements | None |
| TODO/FIXME/HACK | None |
| Mock/fake data presented as real | **Yes — the entire email/password auth flow is mocked** (Critical, see §1) |
| Placeholder/broken images | None found; all logo/avatar sources resolve to real URLs or documented fallbacks |
| Favicon | Present (`public/favicon.svg`, correctly linked) |
| Page `<title>` | **"altraboz"** — internal/codename branding, not "OwnMove" |
| Meta description / Open Graph tags | **Missing entirely** — no `<meta name="description">`, no `og:*` tags in `index.html` |
| Dead code | `src/_legacy/*` (~48KB, confirmed unreferenced) |
| Lint warnings/errors | 6 errors (see §2) |

## 8. Performance

- **Zero code-splitting** — no lazy-loaded routes/components anywhere; everything (including the newly added Framer Motion–driven Learning Journey animation) ships in the initial bundle.
- **No image optimization strategy** — logos are fetched live from Google's favicon service / company domains at render time rather than being bundled or served from a CDN with sizing hints; acceptable for now but worth revisiting if it affects LCP.
- Framer Motion was added to `package.json` (`^11.18.2`) but this sandbox cannot reach the npm registry to install it — **confirm `npm install` was run locally and the app actually builds** before shipping; this was already disclosed when the dependency was added.
- `npm run build` could not be exercised in this sandbox (missing Rolldown native binary for this sandbox's architecture — an environment limitation, not a code issue). Run a real production build yourself and check the bundle-size report before launch.

## 9. Findings Summary

**Critical**
1. Email/password signup and login are entirely fake — no real account or session is ever created (`AuthDialog.jsx`).
2. GitHub and LinkedIn auth buttons expose internal developer setup instructions to real users instead of working sign-in flows.

**High**
3. `VITE_API_BASE_URL` defaults to `localhost:8000` and is live-used by 4 Career AI features — must be set to the production API URL at deploy time or those features break for every user.
4. Route access control is enforced ad hoc per-screen (`status` state in `AppShell`), not at the router level — currently works, but fragile against future regressions; real enforcement must be confirmed at the Supabase RLS layer, which isn't verifiable from the frontend alone.
5. No code-splitting anywhere in a 92-file, ~14K-line app — everything loads on first paint.

**Medium**
6. Page `<title>` is "altraboz" and there's no meta description or Open Graph tags — a real gap for a public launch (link previews, SEO).
7. `_legacy/` dead code (~48KB, confirmed unreferenced) should be deleted, not left in the tree.
8. 6 outstanding ESLint errors, including a real `setState`-in-`useEffect` anti-pattern in `IntelligenceSection.jsx` and 4 unused/half-finished variables in `AppShell.jsx`.
9. `uploadResume` has no client-side file type/size validation.
10. Stray unassigned value in `.env` (line 3) and `.env`/`.env.example` drift.

**Low**
11. Two `<img>` tags missing `alt` text (`TestimonialSection.jsx`).
12. `request()`'s `AbortSignal` support is unused — no request cancellation exists anywhere.
13. No retry/backoff on any network call.
14. Stale/incorrect comment in `services/api/client.js`.
15. Dead `VITE_GOOGLE_CLIENT_ID`/`VITE_GOOGLE_REDIRECT_URI` env vars (Google actually goes through Supabase OAuth, not these).

**Suggested improvements**
- Hide or clearly label GitHub/LinkedIn as "coming soon" until real OAuth apps are wired up.
- Add basic retry/backoff and request cancellation (the plumbing for cancellation already exists, just unused).
- Add real `<meta>` description + Open Graph tags, and fix the page title.
- Consider `React.lazy` for the Career AI dashboards and Learning Journey (both animation- and data-heavy) to shrink initial bundle size.
- Run a real `npm run build` locally and check the bundle report before launch — this sandbox couldn't verify it.
- Verify directly in Supabase dashboard that RLS is enabled on every user-scoped table and the `resumes` bucket — the frontend code assumes it, but assumption isn't verification.

### Scores

- **Security: 72/100** — no leaked secrets, no XSS/injection surface, correct RLS-reliant query patterns, clean anon-key usage; docked heavily for the fake-auth flow (a real trust/security issue, not just a stub) and for RLS enforcement being unverifiable from this codebase alone.
- **Performance: 65/100** — clean of console spam and obvious bloat, but zero code-splitting, zero request cancellation/retry, and an unverified production bundle.
- **UX: 74/100** — genuinely polished in the areas iterated on over many prior rounds (Discover, Career AI, responsive passes), but undercut by the fake login and dead-looking OAuth buttons, which are the exact things a first-time user hits first.
- **Production Readiness: 58/100** — a public launch has to assume login actually works; right now it doesn't for anyone who isn't using Google.

### Personal verdict

No — I would not launch this today. Everything else in this app (Career AI suite, Discover, onboarding, Supabase data layer, RLS-reliant query patterns, styling/responsiveness) is in solid shape. But the primary email/password auth path is mocked, not real, and that's disqualifying for a public launch: it will actively mislead the first users who try it and then break every feature downstream that expects a real session. Fix items #1–#3 (real email/password auth or hide the option, set `VITE_API_BASE_URL` for production, decide on GitHub/LinkedIn) and this becomes a same-week launch candidate — the rest of the list is real but not launch-blocking.
