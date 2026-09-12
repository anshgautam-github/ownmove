import Lenis from 'lenis';

// Site-wide smooth/inertial scrolling, added on top of the plain native
// scroll every page already used. Kept as a single module-level singleton
// (rather than a React context) so any component -- not just the ones
// inside the tree that created it -- can reach the same instance via
// getSmoothScroll(), which matters for the two places elsewhere in the app
// that need to coordinate with it directly: useClientNavigation (routing
// hash-link and route-change jumps through Lenis instead of a raw
// window.scrollTo, so Lenis's own tracked scroll position never drifts out
// of sync with the real one) and AuthDialog's scroll-locking modal (which
// must pause Lenis while the background is pinned via `position: fixed`,
// otherwise Lenis keeps animating toward a wheel-driven target the user
// can't actually see move, producing a visible jump/glitch the moment the
// modal closes and the lock lifts).
//
// `autoRaf: true` is Lenis's own documented simplest setup -- it runs its
// own requestAnimationFrame loop internally, so nothing here needs to.
// `respectReducedMotion` (default true) is left alone: users who've asked
// their OS to minimize motion get instant, non-eased scrolling automatically,
// no extra check needed on our end.
//
// Deliberately NOT setting `anchors: true` -- useClientNavigation already
// has its own, more specific interception of anchor clicks (same-page vs.
// cross-page, pushState, etc.); letting Lenis independently intercept the
// same clicks would double-handle them. That hook calls lenis.scrollTo()
// directly instead.
let lenis = null;

export function initSmoothScroll() {
  if (typeof window === 'undefined') return null;
  if (lenis) return lenis;

  lenis = new Lenis({
    autoRaf: true,
    // Native touch scrolling already feels right on phones; layering
    // Lenis's own inertia on top of the OS's tends to feel laggy rather
    // than smooth, so touch is left as plain native scroll.
    syncTouch: false,
    // The app shell (Discover, Career AI, Profile, Saved) is full of its
    // own internally-scrolling panels (`overflow-y-auto` / `custom-scroll`
    // containers) that are independent of the page's own scroll -- without
    // this, Lenis's default behavior is to treat EVERY wheel/touch event
    // site-wide as input for the one top-level (window) scroll, which
    // silently ate scrolling inside all of those panels entirely. This
    // tells Lenis to detect a scrollable ancestor under the cursor and let
    // it scroll natively instead of hijacking the event. (The Lenis docs
    // note a minor perf cost -- it walks the DOM on each scroll event --
    // but breaking scroll inside every dashboard panel is far worse than
    // that cost; `data-lenis-prevent` on a specific hot-path panel is the
    // documented escape hatch if a real perf issue ever shows up.)
    allowNestedScroll: true,
  });

  return lenis;
}

export function getSmoothScroll() {
  return lenis;
}

export function destroySmoothScroll() {
  if (lenis) {
    lenis.destroy();
    lenis = null;
  }
}
