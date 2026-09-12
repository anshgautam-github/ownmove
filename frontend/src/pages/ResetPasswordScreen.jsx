import React, { useEffect, useState } from 'react';
import { supabase } from '../services/supabase/client';
import { AuthError, updatePassword } from '../services/supabase/auth';

// Landed on from the link Supabase emails after sendPasswordResetEmail()
// (see services/supabase/auth.js) is called from AuthDialog's "forgot
// password" mode. Supabase's client is configured with the default
// implicit flow + detectSessionInUrl, so it parses the `#access_token=...
// &type=recovery` fragment on this page automatically and establishes a
// short-lived "recovery" session — either just before this component
// mounts (in which case getSession() below already sees it) or shortly
// after (in which case the PASSWORD_RECOVERY / SIGNED_IN auth event below
// catches it). Either path unlocks the "set a new password" form; nothing
// else on this page requires the user to already be signed in.
//
// A stale or already-used link comes back from Supabase as
// `#error=access_denied&error_code=otp_expired&error_description=...`
// instead of a token, which is handled explicitly below.
const LINK_STATE = {
  CHECKING: 'checking',
  READY: 'ready',
  INVALID: 'invalid',
};

function readHashError() {
  if (!window.location.hash) return null;
  const params = new URLSearchParams(window.location.hash.slice(1));
  const description = params.get('error_description');
  if (!description && !params.get('error')) return null;
  return description ? description.replace(/\+/g, ' ') : 'That link is invalid.';
}

function ResetPasswordScreen() {
  // Read once: this is a one-shot landing page and the URL fragment
  // Supabase appends (tokens on success, `error`/`error_description` on a
  // stale/used link) doesn't change during its lifetime, so this is plain
  // derived initial state rather than something an effect needs to sync.
  const [hashError] = useState(() => readHashError());
  const [linkState, setLinkState] = useState(() => (hashError ? LINK_STATE.INVALID : LINK_STATE.CHECKING));
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (hashError) return undefined;

    let active = true;

    // Covers the case where Supabase already finished parsing the URL
    // (and already fired PASSWORD_RECOVERY) before this listener attached.
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (active && session) setLinkState(LINK_STATE.READY);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange((event, session) => {
      if (!active) return;
      if ((event === 'PASSWORD_RECOVERY' || event === 'SIGNED_IN') && session) {
        setLinkState(LINK_STATE.READY);
      }
    });

    // If nothing establishes a session within a few seconds, the link was
    // most likely opened stale/cold (e.g. a link opened in a different
    // browser than it was requested in, or the tokens were stripped by an
    // email client's link scanner).
    const timeout = window.setTimeout(() => {
      if (!active) return;
      setLinkState((current) => (current === LINK_STATE.CHECKING ? LINK_STATE.INVALID : current));
    }, 6000);

    return () => {
      active = false;
      subscription?.subscription?.unsubscribe();
      window.clearTimeout(timeout);
    };
  }, [hashError]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError('');

    if (password.length < 6) {
      setFormError('Password must be at least 6 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setFormError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await updatePassword(password);
      setDone(true);
      window.setTimeout(() => {
        window.location.assign('/discover');
      }, 1800);
    } catch (error) {
      setFormError(error instanceof AuthError ? error.message : 'Something went wrong. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#fffdf9_0%,#fff8f2_42%,#f8f6ff_100%)] px-4 py-10 text-[#131114]">
      <div className="w-full max-w-[440px]">
        <div className="relative overflow-hidden rounded-[28px] border border-[#111827]/10 bg-white/58 px-5 py-6 shadow-[0_24px_70px_rgba(96,86,176,0.1)] backdrop-blur-md sm:px-9 sm:py-7">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_0%,rgba(255,224,187,0.28),transparent_32%),radial-gradient(circle_at_86%_8%,rgba(154,127,255,0.11),transparent_28%)]" />
          <div className="relative z-10">
            <div className="text-center">
              <div className="mx-auto mb-5 inline-flex items-center rounded-full border border-[#111827]/12 bg-white/60 px-4 py-2 text-sm font-medium text-black">
                OwnMove
              </div>
              <h1 className="text-[2rem] font-medium leading-none tracking-tight text-black">Set a new password</h1>
            </div>

            {linkState === LINK_STATE.CHECKING && (
              <p className="mt-6 text-center text-sm leading-6 text-[#4B5563]">Checking your link…</p>
            )}

            {linkState === LINK_STATE.INVALID && (
              <div className="mt-6 space-y-4">
                <p className="rounded-[14px] border border-[#e2a4a4]/60 bg-[#fdf2f2] px-4 py-3 text-sm font-medium text-[#a03a3a]">
                  {hashError || 'This reset link is invalid or has expired.'}
                </p>
                <p className="text-center text-sm text-[#4B5563]">
                  Request a new link from the{' '}
                  <a href="/" className="text-black underline underline-offset-2">
                    log in screen
                  </a>
                  .
                </p>
              </div>
            )}

            {linkState === LINK_STATE.READY && !done && (
              <form className="mt-7 space-y-4" onSubmit={handleSubmit}>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-[#6B7280]">New password</span>
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    minLength={6}
                    disabled={isSubmitting}
                    className="h-12 w-full rounded-full border border-[#111827]/10 bg-white/82 px-5 text-sm text-black outline-none transition placeholder:text-[#9aa0aa] focus:border-black/35 focus:bg-white focus:shadow-[0_0_0_3px_rgba(17,24,39,0.05)] disabled:opacity-60"
                    placeholder="Enter new password"
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-[#6B7280]">Confirm password</span>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    required
                    minLength={6}
                    disabled={isSubmitting}
                    className="h-12 w-full rounded-full border border-[#111827]/10 bg-white/82 px-5 text-sm text-black outline-none transition placeholder:text-[#9aa0aa] focus:border-black/35 focus:bg-white focus:shadow-[0_0_0_3px_rgba(17,24,39,0.05)] disabled:opacity-60"
                    placeholder="Re-enter new password"
                  />
                </label>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="h-12 w-full cursor-pointer rounded-full bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-sm font-semibold text-white shadow-[0_8px_20px_rgba(101,89,227,0.18)] transition hover:-translate-y-0.5 hover:shadow-[0_12px_28px_rgba(101,89,227,0.28)] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0"
                >
                  {isSubmitting ? 'Updating…' : 'Update password'}
                </button>

                {formError && (
                  <p className="rounded-[14px] border border-[#e2a4a4]/60 bg-[#fdf2f2] px-4 py-3 text-xs font-medium text-[#a03a3a]" role="alert">
                    {formError}
                  </p>
                )}
              </form>
            )}

            {done && (
              <p className="mt-7 rounded-[14px] border border-[#111827]/10 bg-white/65 px-4 py-3 text-center text-sm font-medium text-[#6B7280]">
                Password updated. Taking you to the app…
              </p>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

export default ResetPasswordScreen;
