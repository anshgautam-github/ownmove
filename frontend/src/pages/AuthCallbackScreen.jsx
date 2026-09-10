import React, { useEffect } from 'react';
import { supabase } from '../services/supabase/client';
import { resolvePostAuthRedirect } from '../services/supabase/auth';

// Lands here right after Supabase finishes the Google OAuth redirect.
// Decides whether this is a returning user (has a profile row already)
// or a first-time user who still needs to go through onboarding — the same
// resolvePostAuthRedirect logic email/password sign-in uses in AuthDialog,
// so both auth paths land users in exactly the same place.
function AuthCallbackScreen() {
  useEffect(() => {
    let active = true;

    (async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!active) return;

      if (!session) {
        window.location.replace('/');
        return;
      }

      const destination = await resolvePostAuthRedirect();
      if (!active) return;
      window.location.replace(destination);
    })();

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#050711] text-white">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-white/50">Signing you in…</p>
    </main>
  );
}

export default AuthCallbackScreen;
