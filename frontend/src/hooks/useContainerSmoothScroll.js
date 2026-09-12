import { useEffect } from 'react';
import Lenis from 'lenis';

// Gives ONE scrollable container its own Lenis-driven smooth/inertial
// scroll, independent of the site-wide window-level instance created in
// utils/smoothScroll.js.
//
// Why this exists: that window-level instance uses `allowNestedScroll:
// true` so it doesn't hijack wheel/touch events over nested scrollable
// panels (Discover's opportunity grid, Career AI's dashboards, Saved,
// Profile) -- without it those panels couldn't scroll at all, since a
// single Lenis instance otherwise claims every scroll event site-wide.
// But `allowNestedScroll`'s own documented tradeoff is that it lets those
// panels fall back to plain native scrolling, with none of Lenis's easing.
// This hook plugs that gap: it creates a second, small Lenis instance
// scoped to just one element (`wrapper: node, content: node` -- verified
// against Lenis's own source that a non-window wrapper reads
// `wrapper.scrollHeight` directly, so pointing `content` at the same node
// is correct) so that panel gets its own smooth/inertial feel back,
// without re-hijacking anything above it.
//
// `active` lets a caller skip creating an instance for a panel that isn't
// currently visible/mounted-relevant (avoids wasted rAF loops for panes
// kept mounted-but-hidden). `depKey` is for the rarer case where the same
// ref object gets reassigned to a different DOM node across renders (e.g.
// a single ref conditionally attached to whichever of several sibling
// panels is currently active) -- passing the value that identifies "which
// node this points to right now" forces the instance to be torn down and
// recreated against the new node.
export function useContainerSmoothScroll(ref, { active = true, depKey } = {}) {
  useEffect(() => {
    const node = ref.current;
    if (!node || !active) return undefined;

    const instance = new Lenis({
      wrapper: node,
      content: node,
      autoRaf: true,
      syncTouch: false,
      // Cards inside these panels (e.g. an opportunity card's own
      // "Description" pop-out, itself a small `overflow-y-auto` box) can
      // be scrollable in their own right. Without this, this panel's own
      // Lenis instance claims every wheel/touch event anywhere inside it,
      // so scrolling inside a further-nested box like that pop-out just
      // scrolls the whole panel behind it instead. Same fix, same reason,
      // as the site-wide instance in utils/smoothScroll.js.
      allowNestedScroll: true,
    });

    return () => instance.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ref, active, depKey]);
}
