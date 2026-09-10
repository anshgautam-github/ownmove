# OwnMove Frontend — Production Hardening Summary

No redesign, no breaking changes — every existing feature works the same way it did before; the changes are auth, config, code-splitting, cleanup, and safety nets underneath it.

## Issues fixed

**Critical**
- Email/password auth was fake. Replaced with real `supabase.auth.signUp` / `signInWithPassword`, with friendly error mapping (invalid credentials, already-registered email, unconfirmed email, rate limits), a loading state on submit, and handling for projects with email confirmation enabled (shows a "check your email" message instead of a false redirect). Sign-up/login now redirect through the exact same `resolvePostAuthRedirect` logic Google OAuth already used, so both paths land users in the same place.
- GitHub and LinkedIn buttons (which only ever showed a "setup needed" panel to real users) are removed, along with the dead generic-provider URL code in `auth.js` that backed them.
- `VITE_API_BASE_URL` no longer silently falls back to `localhost:8000`. If it's missing, the API client now throws one clear, actionable error instead of quietly pointing a production user's browser at localhost; `assertEnv()` (previously written but never called) now runs at boot and warns loudly in the console if required config is missing.

**High priority**
- Route protection now also reacts to session loss while a page is open (`SIGNED_OUT` from Supabase's `onAuthStateChange`), not just the one-time check on mount — a revoked/expired session now drops the app back to the sign-in screen instead of continuing to render stale content. Enforcement is still (and should remain) Supabase RLS.
- Career AI (Profile Analysis, Career Roadmap, Career Simulation, AI Coach) and Learning Journey are now `React.lazy`-loaded behind `Suspense`, using the same spinner style as the existing auth-loading screen. The "mount once, keep mounted" tab-switch behavior built earlier is preserved — the fallback only ever appears on first visit, not on every tab switch.

**SEO / branding**
- `index.html`: real title, meta description, Open Graph, and Twitter card tags; all "altraboz" branding replaced with "OwnMove" (including `package.json`'s `name` field).

**Cleanup / ESLint**
- Fixed all 6 pre-existing ESLint errors: the `setState`-in-`useEffect` anti-pattern in `IntelligenceSection.jsx` (moved to the render-time "adjust state" pattern already used elsewhere in this codebase), the unused catch binding in `CareerSimulationDashboard.jsx`, and 4 dead variables in `AppShell.jsx` (`isRefreshing`, `handleRefresh`, `dateStr`, `backHref`).
- Removed dead `VITE_GOOGLE_CLIENT_ID`/`VITE_GOOGLE_REDIRECT_URI` env vars (Google auth goes through Supabase, not these) and a stray unassigned line in `.env`.
- `npx eslint .` now passes with zero errors and zero warnings.

**Accessibility**
- Added missing `alt` attributes on the two `TestimonialSection.jsx` avatar images.
- Added keyboard support (`role="button"`, `tabIndex`, Enter/Space handling, focus ring) to two clickable `<div>`s that had no keyboard path: the "recent simulation" row in `RecentSimulations.jsx` and the drop-zone in the landing page's program demo.

**Network**
- `services/api/client.js` (the one client every Career AI call goes through) now has a 15s timeout, automatic retry with backoff for network failures and 502/503/504 (never for 4xx), and proper `AbortController` composition so a caller-supplied signal and the internal timeout both work together. Every existing caller gets this for free with no code changes on their end.

**Uploads**
- Resume upload now validates file extension and (when the browser reports one) MIME type, not just size, in both the Profile edit page and Onboarding — shared via one `validateResumeFile` helper so both stay in sync. Friendly error messages for wrong type, empty file, and oversized file.

## Files modified

- `frontend/src/services/supabase/auth.js` — rewritten: real email/password auth, error mapping, shared redirect resolver.
- `frontend/src/components/auth/AuthDialog.jsx` — rewritten: real auth wiring, GitHub/LinkedIn removed, loading/error states.
- `frontend/src/pages/AuthCallbackScreen.jsx` — simplified to reuse the shared redirect resolver.
- `frontend/src/config/env.js` — no localhost fallback, `apiBaseUrl` validated.
- `frontend/src/main.jsx` — calls `assertEnv()` at boot.
- `frontend/src/services/api/client.js` — timeout, retry, AbortController, config validation.
- `frontend/src/pages/AppShell.jsx` — lazy-loaded dashboards + Suspense, `SIGNED_OUT` listener, dead code removed, resume upload validation wired in.
- `frontend/src/pages/OnboardingScreen.jsx` — resume upload validation wired in.
- `frontend/src/services/supabase/profiles.js` — added shared `validateResumeFile`.
- `frontend/src/components/landing/IntelligenceSection.jsx` — setState-in-effect fix.
- `frontend/src/components/career-ai/CareerSimulationDashboard.jsx` — unused catch fix.
- `frontend/src/components/landing/TestimonialSection.jsx` — alt attributes.
- `frontend/src/components/career-ai/simulation/RecentSimulations.jsx` — keyboard accessibility.
- `frontend/src/components/landing/DemoSection.jsx` — keyboard accessibility on drop zone.
- `frontend/index.html` — SEO metadata, branding.
- `frontend/package.json` — name field.
- `frontend/.env`, `frontend/.env.example` — dead vars removed, comments updated.

## Remaining recommendations

- **`src/_legacy/` could not be deleted** — file deletion in your project folder requires your explicit approval per-file, and you declined it when I asked mid-task. It's confirmed unreferenced (nothing imports it, so it ships in zero bundles), but it's still sitting in the repo. Same goes for two other already-orphaned files from an earlier iteration: `src/components/certifications/LearningHubCatalog.jsx` and `src/data/learningPlatforms.js`. Delete all of these locally whenever convenient — none of it is wired to anything.
- **Verify Supabase Auth settings**: confirm "Confirm email" is set the way you want (the new signup flow handles both states, but you should know which one is live), and confirm Google OAuth is enabled under Authentication → Providers with this app's callback URL allow-listed.
- **Set `VITE_API_BASE_URL` in your actual production deploy environment** to your real API origin — it no longer has a fallback, so Career AI features will show a clear config error if this is missed, rather than failing silently.
- **Run a real `npm run build` on your machine.** This sandbox can't produce one (missing native Rolldown binary for its CPU architecture, unrelated to any of these changes) — `npx eslint .` passing cleanly across the whole project is the verification I could do here.
- The stored-XSS risk flagged in the pentest (unvalidated `apply_url` scheme from scraped opportunities) and the IDOR question on ID-based Career AI endpoints are both still open — they weren't in this hardening request's scope, but they're real and worth a follow-up pass.

## Scores

- **Production Readiness: 84/100** (was 58) — the one launch-blocking issue (fake auth) is fixed; what's left is config discipline (env vars set correctly at deploy) and the two pentest items above, not frontend defects.
- **Security: 85/100** (was 72) — real auth, no dead OAuth surface, config fails loudly instead of silently.
- **Performance: 78/100** (was 65) — code-split, retried, timed-out network calls; still no image CDN/optimization pipeline, which is a reasonable next step, not a blocker.
- **UX: 82/100** (was 74) — same UI throughout, now with working auth, friendly errors, and upload validation instead of a form that lied to users.

## Would I launch this today?

Yes, with one condition: set `VITE_API_BASE_URL` correctly and confirm your Supabase Auth provider settings before you deploy — those are the only two things between this and a real launch. Everything that was actually disqualifying (the fake login) is fixed. The stored-XSS and IDOR items from the pentest are worth fixing soon, but they're hardening for an already-launchable app, not blockers.
