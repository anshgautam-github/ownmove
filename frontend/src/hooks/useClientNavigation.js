import { useEffect, useState } from 'react';
import { getSmoothScroll } from '../utils/smoothScroll';

/**
 * Minimal client-side router.
 *
 * Intercepts same-origin anchor clicks, updates history via pushState, and
 * returns the current pathname so <App /> can pick a screen. Extracted from
 * App.jsx so routing behaviour lives with the other hooks rather than being
 * tangled up with the route table itself.
 *
 * Behaviour is intentionally unchanged from the original implementation.
 */
export function useClientNavigation() {
  const [pathname, setPathname] = useState(() => window.location.pathname);

  useEffect(() => {
    const onPopState = () => setPathname(window.location.pathname);
    window.addEventListener('popstate', onPopState);

    const onClick = (event) => {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      const anchor = event.target.closest('a');
      if (!anchor) return;

      const href = anchor.getAttribute('href');
      if (!href || !href.startsWith('/') || href.startsWith('//')) return;
      if (anchor.target === '_blank' || anchor.hasAttribute('download')) return;

      const url = new URL(href, window.location.origin);
      const samePath = url.pathname === window.location.pathname;

      event.preventDefault();

      if (!samePath) {
        window.history.pushState({}, '', url.pathname + url.search + url.hash);
        setPathname(url.pathname);
      }

      if (url.hash) {
        // wait a tick for the new screen to mount before scrolling to the anchor
        requestAnimationFrame(() => {
          const target = document.querySelector(url.hash);
          if (!target) return;
          // Route through Lenis (site-wide smooth scroll) when it's up, so
          // its own tracked scroll position stays correct instead of
          // drifting out of sync with a scroll it didn't know happened.
          // Falls back to the plain native smooth scroll for the brief
          // window before Lenis has initialized.
          const lenis = getSmoothScroll();
          if (lenis) {
            lenis.scrollTo(target, { offset: 0 });
          } else {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        });
      } else if (!samePath) {
        const lenis = getSmoothScroll();
        if (lenis) {
          lenis.scrollTo(0, { immediate: true });
        } else {
          window.scrollTo(0, 0);
        }
      }
    };
    document.addEventListener('click', onClick);

    return () => {
      window.removeEventListener('popstate', onPopState);
      document.removeEventListener('click', onClick);
    };
  }, []);

  return pathname;
}

export default useClientNavigation;
