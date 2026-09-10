import React from 'react';
import useClientNavigation from './hooks/useClientNavigation';
import LandingPage from './pages/LandingPage';
import OnboardingScreen from './pages/OnboardingScreen';
import AppShell from './pages/AppShell';
import AuthCallbackScreen from './pages/AuthCallbackScreen';

// Every authenticated shell route renders the SAME <AppShell /> call site so
// React keeps the instance mounted across switches — only the `view` prop
// changes, so the shared header/ambient chrome never unmounts and only the
// content pane underneath re-renders. No reload, no flash.
const SHELL_ROUTES = {
  '/discover': 'discover',
  '/career-ai': 'career-ai',
  '/profile': 'profile',
  '/saved': 'saved',
};

function App() {
  const pathname = useClientNavigation();

  if (SHELL_ROUTES[pathname]) {
    return <AppShell view={SHELL_ROUTES[pathname]} />;
  }

  if (pathname === '/auth/callback') {
    return <AuthCallbackScreen />;
  }

  const isOnboardingRoute = pathname === '/onboarding' || pathname.startsWith('/auth/');

  if (isOnboardingRoute) {
    return <OnboardingScreen />;
  }

  return <LandingPage />;
}

export default App;
