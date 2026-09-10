/**
 * Lightweight session-scoped read cache for the Career AI dashboards.
 *
 * Why this exists: each dashboard (Profile Analysis, Career Roadmap, Career
 * Simulation, AI Coach) used to re-fetch its data every time it mounted.
 * Keeping all four permanently mounted (see AppShell.jsx's Career AI
 * content-pane stack) already means a plain tab switch never re-fetches —
 * but a full page reload, or navigating away to a route outside the shell
 * (e.g. /onboarding) and back, still remounts everything from scratch. This
 * cache closes that gap: once a resource has been fetched, it's kept here
 * and reused on the next mount with zero network calls, until a mutation
 * (generate roadmap, re-analyze, run simulation, send a coach message, ...)
 * explicitly writes the new value back — never from a silent background
 * refetch.
 *
 * Backed by both an in-memory Map (fast, always available) and
 * sessionStorage (survives a full page reload, cleared when the tab
 * closes — appropriate for per-login-session data). sessionStorage writes
 * are best-effort: private browsing / quota errors silently fall back to
 * memory-only, which still satisfies "no refetch within this SPA session."
 *
 * Scoped by user id (see setCacheScope): sessionStorage is NOT cleared by
 * `window.location.assign()` on logout — only by closing the tab — so
 * without this, signing out of one account and into a different one in the
 * same tab would read the first account's cached Profile Analysis/Career
 * Roadmap/Career Simulation/AI Coach data straight out of storage, and the
 * "already hydrated, skip the fetch" checks in those dashboards would never
 * correct it. Every key is namespaced by whichever user is current when
 * get/set/clear is called, so two different accounts never share a slot —
 * this was a real cross-account data leak on shared devices, not a cosmetic
 * bug, so every call site must go through this scoping rather than working
 * around it locally.
 */

const PREFIX = 'career-ai-cache:v1:';
const memory = new Map();
let scope = 'anon';

/** Call this whenever the signed-in user becomes known (or becomes
 * unknown, e.g. on sign-out) — see AppShell.jsx's session effect. */
export function setCacheScope(userId) {
  scope = userId || 'anon';
}

function scopedKey(key) {
  return `${PREFIX}${scope}:${key}`;
}

function safeParse(raw) {
  try {
    return JSON.parse(raw);
  } catch {
    return undefined;
  }
}

/** Returns the cached value for `key`, or `undefined` if nothing is cached
 * yet (a cached `null`/`[]` is a valid, meaningful value — e.g. "no roadmap
 * exists yet" — and is returned as-is, not treated as a miss). */
export function getCache(key) {
  const fullKey = scopedKey(key);
  if (memory.has(fullKey)) return memory.get(fullKey);
  if (typeof window === 'undefined') return undefined;
  try {
    const raw = window.sessionStorage.getItem(fullKey);
    if (raw === null) return undefined;
    const value = safeParse(raw);
    if (value !== undefined) memory.set(fullKey, value);
    return value;
  } catch {
    return undefined;
  }
}

export function setCache(key, value) {
  const fullKey = scopedKey(key);
  memory.set(fullKey, value);
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(fullKey, JSON.stringify(value));
  } catch {
    // Quota exceeded or storage disabled — the in-memory copy still holds
    // for the rest of this page session, which is the part that matters.
  }
}

export function clearCache(key) {
  const fullKey = scopedKey(key);
  memory.delete(fullKey);
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.removeItem(fullKey);
  } catch {
    // ignore
  }
}
