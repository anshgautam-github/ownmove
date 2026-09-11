import React from 'react';
import { Analytics } from '@vercel/analytics/react';

import useClientNavigation from './hooks/useClientNavigation';
import LandingPage from './pages/LandingPage';
import OnboardingScreen from './pages/OnboardingScreen';
import AppShell from './pages/AppShell';
import AuthCallbackScreen from './pages/AuthCallbackScreen';

const SHELL_ROUTES = {
  '/discover': 'discover',
  '/career-ai': 'career-ai',
  '/profile': 'profile',
  '/saved': 'saved',
};

function App() {
  const pathname = useClientNavigation();

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
    </>
  );
}

export default App;