import { supabase } from './client';
import { loadOnboardingProfile } from './profiles';

// Thin wrapper so callers can distinguish "Supabase rejected this" from any
// other kind of failure, and so AuthDialog never has to parse raw Supabase
// error strings itself.
export class AuthError extends Error {
  constructor(message) {
    super(message);
    this.name = 'AuthError';
  }
}

// Supabase's own error messages are accurate but not written for end users
// (or are ambiguous by design, e.g. anti-enumeration wording on signup).
// Map the common ones to something a person reads on a login form.
function friendlyAuthMessage(error) {
  const message = error?.message || '';

  if (/invalid login credentials/i.test(message)) {
    return 'Incorrect email or password.';
  }
  if (/email not confirmed/i.test(message)) {
    return 'Please confirm your email before logging in — check your inbox for the confirmation link.';
  }
  if (/user already registered/i.test(message)) {
    return 'An account with this email already exists. Try logging in instead.';
  }
  if (/rate limit/i.test(message)) {
    return 'Too many attempts. Please wait a moment and try again.';
  }
  if (/password/i.test(message) && /(least|short|6)/i.test(message)) {
    return 'Password must be at least 6 characters.';
  }

  return message || 'Something went wrong. Please try again.';
}

// Google goes through Supabase Auth so the resulting session lines up with
// `auth.uid()` used by the profiles/experiences RLS policies.
export async function startGoogleSupabaseAuth() {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${window.location.origin}/auth/callback`,
    },
  });

  return !error;
}

// Real email/password sign-up. Supabase's anti-enumeration behavior on
// projects with "Confirm email" enabled returns success (no `error`) for an
// email that's already registered, but with an empty `identities` array —
// that's the only reliable client-side signal, so it's checked explicitly
// rather than trusting the absence of an error.
export async function signUpWithEmail({ email, password, fullName }) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: `${window.location.origin}/auth/callback`,
      data: fullName ? { full_name: fullName } : undefined,
    },
  });

  if (error) {
    throw new AuthError(friendlyAuthMessage(error));
  }

  if (Array.isArray(data.user?.identities) && data.user.identities.length === 0) {
    throw new AuthError('An account with this email already exists. Try logging in instead.');
  }

  // If email confirmation is enabled for this project, signUp succeeds but
  // returns no session until the user clicks the confirmation link.
  return { session: data.session, needsEmailConfirmation: !data.session };
}

export async function signInWithEmail({ email, password }) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    throw new AuthError(friendlyAuthMessage(error));
  }

  return { session: data.session };
}

// Same destination logic Google OAuth already uses via AuthCallbackScreen:
// an explicit pre-login destination wins, otherwise returning users go
// straight to Discover and first-timers go to onboarding. Shared here so
// email/password sign-in lands users in exactly the same place OAuth would.
export async function resolvePostAuthRedirect() {
  const redirect = localStorage.getItem('postLoginRedirect');
  if (redirect) {
    localStorage.removeItem('postLoginRedirect');
    return redirect;
  }

  const profile = await loadOnboardingProfile();
  return profile ? '/discover' : '/onboarding';
}
