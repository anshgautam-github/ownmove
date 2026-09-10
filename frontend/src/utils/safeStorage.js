/**
 * localStorage that can't crash the caller.
 *
 * `postLoginRedirect` (see services/supabase/auth.js and the landing page's
 * "Explore More" / "Build my profile" style CTA buttons) is written and read
 * around the login flow, on the very click that also has to open the auth
 * dialog. Plain `localStorage.setItem`/`getItem`/`removeItem` throw
 * synchronously in environments that disable persistent storage instead of
 * just silently no-op'ing -- most notably Safari Private Browsing, where
 * `setItem` throws `QuotaExceededError` rather than doing nothing. An
 * uncaught throw there happens BEFORE the `open-auth` event fires, so the
 * whole click handler aborts right there and the login dialog never opens --
 * from the user's perspective the button just does nothing, or the page
 * appears to break, with no indication why.
 *
 * These wrappers make that failure mode impossible: storage becomes
 * best-effort (skip the stashed redirect, still let the user log in)
 * instead of a hard failure that blocks login entirely. Never throws.
 */

export function safeGetItem(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function safeSetItem(key, value) {
  try {
    window.localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

export function safeRemoveItem(key) {
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Best-effort cleanup only -- nothing meaningful to do if this fails.
  }
}
