# Client-side state

Currently empty by design — no global state library is warranted yet.

State today lives where it is used:
- `pages/AppShell.jsx` owns view/profile/saved state for the authenticated app.
- Server data is fetched per-pane and cached in component state.

Add a store here (Zustand or Context + reducer) only when state is genuinely
shared across unrelated routes. Prefer TanStack Query for *server* state —
caching, refetching and optimistic updates are its job, not a global store's.

Do not put API calls here; those belong in `services/`.
