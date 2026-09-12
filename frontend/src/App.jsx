import React, { useEffect } from 'react';
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/react';

import useClientNavigation from './hooks/useClientNavigation';
import LandingPage from './pages/LandingPage';
import OnboardingScreen from './pages/OnboardingScreen';
import AppShell from './pages/AppShell';
import AuthCallbackScreen from './pages/AuthCallbackScreen';
import { initSmoothScroll, destroySmoothScroll } from './utils/smoothScroll';
import 'lenis/dist/lenis.css';

const SHELL_ROUTES = {
  '/discover': 'discover',
  '/career-ai': 'career-ai',
  '/profile': 'profile',
  '/saved': 'saved',
};

function App() {
  const pathname = useClientNavigation();

  // Site-wide smooth/inertial scrolling. One instance for the whole app's
  // lifetime (mounted here at the root so it covers every route), rather
  // than per-page, since it wraps native window scroll globally regardless
  // of which screen is showing.
  useEffect(() => {
    initSmoothScroll();
    return () => destroySmoothScroll();
  }, []);

  // Site-wide "disable image download" guard. Scoped to `e.target.tagName
  // === 'IMG'` only, so it never touches right-click/drag anywhere else on
  // the page (text selection, card interactions, form fields, etc.) — it
  // only blocks the browser's own "Save image as…" / "Copy image" context
  // menu and the drag-image-out-to-desktop gesture. Runs once at the root
  // so it covers every image on every route (landing, onboarding, the app
  // shell) without needing per-image props. As noted in index.css, this —
  // like any client-side measure — can't stop devtools, "View Page
  // Source", or a screenshot; it only removes the two casual, one-click
  // ways to save an image.
  useEffect(() => {
    const blockImageContextMenu = (e) => {
      if (e.target instanceof Element && e.target.closest('img')) {
        e.preventDefault();
      }
    };
    const blockImageDrag = (e) => {
      if (e.target instanceof Element && e.target.closest('img')) {
        e.preventDefault();
      }
    };
    document.addEventListener('contextmenu', blockImageContextMenu);
    document.addEventListener('dragstart', blockImageDrag);
    return () => {
      document.removeEventListener('contextmenu', blockImageContextMenu);
      document.removeEventListener('dragstart', blockImageDrag);
    };
  }, []);

  let content;

  if (SHELL_ROUTES[pathname]) {
    content = <AppShell view={SHELL_ROUTES[pathname]} />;
  } else if (pathname === '/auth/callback') {
    content = <AuthCallbackScreen />;
  } else {
    const isOnboardingRoute =
      pathname === '/onboarding' || pathname.startsWith('/auth/');

    if (isOnboardingRoute) {
      content = <OnboardingScreen />;
    } else {
      content = <LandingPage />;
    }
  }

  return (
    <>
      {content}
      <Analytics />
      <SpeedInsights />
    </>
  );
}

export default App;