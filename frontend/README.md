# Frontend

React 19 + Vite + Tailwind v4. **UI only** — no business logic lives here.

```bash
npm install
cp .env.example .env
npm run dev     # http://localhost:5173
npm run lint
npm run build
```

## Structure

```
src/
├── main.jsx                 Entry point
├── App.jsx                  Route table only
│
├── pages/                   Route-level screens
│   ├── LandingPage.jsx        "/"  marketing site + scroll transitions
│   ├── AppShell.jsx           "/dashboard" "/discover" "/career-ai" "/profile" "/saved"
│   ├── OnboardingScreen.jsx   "/onboarding"
│   └── AuthCallbackScreen.jsx "/auth/callback"
│
├── components/              Presentational building blocks
│   ├── landing/               Marketing sections (Hero, Faq, Footer, …)
│   └── auth/                  AuthDialog
│
├── hooks/                   Reusable behaviour
│   └── useClientNavigation.js Hand-rolled router (pushState + click capture)
│
├── services/                ALL I/O lives here — components never fetch
│   ├── supabase/              Direct Supabase access (current data path)
│   │   ├── client.js            Browser Supabase client (anon key)
│   │   ├── auth.js              Google OAuth entry points
│   │   ├── profiles.js          profiles + experiences
│   │   ├── opportunities.js     opportunity catalogue
│   │   └── savedOpportunities.js bookmarks
│   └── api/                   FastAPI client (future data path)
│       ├── client.js            fetch wrapper, injects the Supabase JWT
│       └── endpoints.js         every backend route path, in one place
│
├── config/env.js            Single place `import.meta.env` is read
├── store/                   Client-side state (see store/README.md)
├── styles/                  Global CSS
├── assets/
└── _legacy/                 Superseded, unreferenced — safe to delete
```

### Conventions

**Components never talk to the network.** They call something in `services/`.
This is what makes the Supabase → FastAPI migration a per-file change rather
than a rewrite.

**`pages/` vs `components/`** — a page owns a route and composes; a component
renders a piece of UI and is route-agnostic.

**Env vars** go through `config/env.js`, never `import.meta.env` inline.

### Migrating an endpoint to FastAPI

When a backend endpoint is ready, change only the service module:

```js
// before — services/supabase/opportunities.js
const { data } = await supabase.from('opportunities').select('*')

// after — services/api/opportunities.js
import { api } from './client'
import { endpoints } from './endpoints'
const data = await api.get(endpoints.opportunities.list)
```

Pages and components stay untouched.

## Environment

Copy `.env.example` to `.env`:

```bash
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_BASE_URL=http://localhost:8000
```

Restart the dev server after changing env vars — Vite reads them at boot.

## Auth

Google sign-in goes through **Supabase OAuth**
(`services/supabase/auth.js` → `signInWithOAuth`), redirecting to
`/auth/callback`. The resulting session's `auth.uid()` is what the Row Level
Security policies match on, so Supabase must be the identity provider — do not
swap in a bespoke OAuth flow.

Redirect URLs are configured in the Supabase dashboard under
**Authentication → URL Configuration**, and in the Google Cloud Console OAuth
client. For local development, allow `http://localhost:5173/auth/callback`.

The GitHub and LinkedIn buttons are UI-only; `services/supabase/auth.js` reads
`VITE_GITHUB_AUTH_URL` / `VITE_LINKEDIN_AUTH_URL` and does nothing if unset.

## Notes

- **`_legacy/`** holds `DashboardScreen.jsx` and `DiscoverScreen.jsx` (both
  superseded by `pages/AppShell.jsx`) and `googleAuth.js` (a re-export shim).
  Nothing imports them. Kept only so nothing is lost; safe to delete.
- **`scripts/legacy-refactor.cjs`** is a one-off script from an early refactor.
  It **overwrites `src/App.jsx`** — do not run it.
