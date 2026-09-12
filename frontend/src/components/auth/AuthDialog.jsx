import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  startGoogleSupabaseAuth,
  signUpWithEmail,
  signInWithEmail,
  sendPasswordResetEmail,
  resolvePostAuthRedirect,
} from '../../services/supabase/auth';
import { getSmoothScroll } from '../../utils/smoothScroll';
import AuthBackgroundLogos from './AuthBackgroundLogos';

const MotionDiv = motion.div;

function GoogleIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5">
      <path fill="#4285F4" d="M22.6 12.23c0-.79-.07-1.54-.2-2.27H12v4.29h5.94a5.08 5.08 0 0 1-2.2 3.34v2.77h3.57c2.09-1.93 3.29-4.77 3.29-8.13Z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.65l-3.57-2.77c-.99.66-2.25 1.05-3.71 1.05-2.86 0-5.29-1.93-6.16-4.53H2.18v2.86A11 11 0 0 0 12 23Z" />
      <path fill="#FBBC05" d="M5.84 14.1a6.61 6.61 0 0 1 0-4.2V7.04H2.18a11 11 0 0 0 0 9.92l3.66-2.86Z" />
      <path fill="#EA4335" d="M12 5.37c1.61 0 3.06.55 4.2 1.64l3.16-3.16A10.59 10.59 0 0 0 12 1 11 11 0 0 0 2.18 7.04L5.84 9.9C6.71 7.3 9.14 5.37 12 5.37Z" />
    </svg>
  );
}

function EyeSlashIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5">
      <path fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="m3 3 18 18M10.58 10.58A2 2 0 0 0 12 14a2 2 0 0 0 1.42-.58M9.88 4.24A10.55 10.55 0 0 1 12 4c5 0 8.27 4 9.5 6a11.9 11.9 0 0 1-2.1 2.7M6.1 6.1A12.2 12.2 0 0 0 2.5 10c1.23 2 4.5 6 9.5 6 1.08 0 2.1-.19 3.03-.52" />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5">
      <path fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.5 12S5.77 6 12 6s9.5 6 9.5 6-3.27 6-9.5 6-9.5-6-9.5-6Z" />
      <circle cx="12" cy="12" r="2.5" fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

// Google's own setup steps — the only provider left, so there's no need for
// a per-provider lookup table anymore. Only ever shown if
// startGoogleSupabaseAuth() reports failure (e.g. Google OAuth isn't
// enabled yet in this Supabase project's Auth settings).
const GOOGLE_SETUP_STEPS = [
  'In the Supabase dashboard, go to Authentication -> Providers and enable Google.',
  'Add your Google OAuth Client ID and Client Secret there.',
  'Add this app\'s origin and /auth/callback path to the provider\'s allowed redirect URLs.',
];

function AuthDialog({ onClose, initialMode = 'login' }) {
  const [authMode, setAuthMode] = useState(initialMode);
  const [showGoogleSetup, setShowGoogleSetup] = useState(false);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [formMessage, setFormMessage] = useState('');
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [needsEmailConfirmation, setNeedsEmailConfirmation] = useState(false);
  const [resetEmailSent, setResetEmailSent] = useState(false);

  useEffect(() => {
    const scrollY = window.scrollY;
    const bodyStyle = document.body.style;
    const htmlStyle = document.documentElement.style;
    const previousBodyStyles = {
      overflow: bodyStyle.overflow,
      position: bodyStyle.position,
      top: bodyStyle.top,
      width: bodyStyle.width,
    };
    const previousHtmlOverflow = htmlStyle.overflow;

    // Lenis still listens for wheel/touch input on the window while the
    // body is pinned via `position: fixed` below, and would otherwise keep
    // animating toward a scroll target the user can't see move -- so when
    // the dialog finally closes and the real scroll position snaps back,
    // Lenis's own tracked position is out of sync with it, which shows up
    // as a visible jump/glitch right as the modal closes. Pausing it for
    // the lifetime of the lock avoids that.
    const lenis = getSmoothScroll();
    lenis?.stop();

    htmlStyle.overflow = 'hidden';
    bodyStyle.overflow = 'hidden';
    bodyStyle.position = 'fixed';
    bodyStyle.top = `-${scrollY}px`;
    bodyStyle.width = '100%';

    return () => {
      htmlStyle.overflow = previousHtmlOverflow;
      bodyStyle.overflow = previousBodyStyles.overflow;
      bodyStyle.position = previousBodyStyles.position;
      bodyStyle.top = previousBodyStyles.top;
      bodyStyle.width = previousBodyStyles.width;
      window.scrollTo(0, scrollY);
      // Restart only after the real scroll position is restored above, so
      // Lenis picks back up from the correct spot rather than wherever it
      // last thought it was before being paused.
      lenis?.start();
    };
  }, []);

  const handleGoogleClick = async () => {
    setFormError('');
    const started = await startGoogleSupabaseAuth();
    if (!started) setShowGoogleSetup(true);
  };

  const switchAuthMode = (mode) => {
    setAuthMode(mode);
    setShowGoogleSetup(false);
    setFormMessage('');
    setFormError('');
    setNeedsEmailConfirmation(false);
    setResetEmailSent(false);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError('');
    setFormMessage('');

    if (authMode === 'forgot') {
      setIsSubmitting(true);
      try {
        await sendPasswordResetEmail(email);
        setResetEmailSent(true);
        setFormMessage("If an account exists for that email, we've sent a link to reset the password. Check your inbox (and spam folder).");
      } catch (error) {
        setFormError(error.message || 'Something went wrong. Please try again.');
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    if (!acceptedTerms) {
      setFormError('Please accept the terms before continuing.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (authMode === 'signup') {
        const { needsEmailConfirmation: pendingConfirmation } = await signUpWithEmail({
          email,
          password,
          fullName,
        });

        if (pendingConfirmation) {
          setNeedsEmailConfirmation(true);
          setFormMessage('Account created. Check your email to confirm it before logging in.');
          setIsSubmitting(false);
          return;
        }

        setFormMessage('Account created. Opening onboarding...');
      } else {
        await signInWithEmail({ email, password });
        setFormMessage('Signed in. Opening app...');
      }

      // Redirect exactly where Google OAuth would send this user —
      // resolvePostAuthRedirect is the same helper AuthCallbackScreen uses.
      const destination = await resolvePostAuthRedirect();
      window.location.assign(destination);
    } catch (error) {
      setFormError(error.message || 'Something went wrong. Please try again.');
      setIsSubmitting(false);
    }
  };

  const heading =
    authMode === 'login' ? 'Log in to OwnMove' : authMode === 'signup' ? 'Create your account' : 'Reset your password';
  const subtitle =
    authMode === 'login'
      ? 'Continue to your profile and career dashboard.'
      : authMode === 'signup'
      ? 'Create your profile and start your onboarding.'
      : "Enter your email and we'll send you a link to reset your password.";

  // Rendered via a portal straight onto <body>, not in normal JSX-parent
  // position: AuthDialog is opened from HeroSection, which on desktop lives
  // inside HeroWorkTransition's crossfade wrapper (LandingPage.jsx) --  an
  // ancestor with an inline `transform` (translate3d/scale) for the
  // Hero/WorkAi pin animation. Any transformed ancestor becomes the
  // containing block for a `position: fixed` descendant, so without the
  // portal this dialog's "fixed inset-0" was resolving against that
  // (often scrolled-mostly-off-screen) wrapper instead of the real
  // viewport -- it rendered squashed into a sliver, or invisible, whenever
  // someone opened it after scrolling past the hero (e.g. the "Build my
  // profile" CTA further down the page). Portalling to document.body
  // sidesteps the whole ancestor chain, so this is always positioned
  // against the true viewport no matter where in the tree it's triggered
  // from or how far the page has scrolled.
  return createPortal(
    <MotionDiv
      className="fixed inset-0 z-50 overflow-y-auto overscroll-contain bg-[linear-gradient(180deg,#fffdf9_0%,#fff8f2_42%,#f8f6ff_100%)] text-[#131114]"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      <AuthBackgroundLogos />

      {/* Fixed (not sticky-in-flow) to the viewport itself, so it stays in
          the same spot regardless of how far the form inside has scrolled --
          simpler and more robust than the old sticky-header-bar approach,
          and doesn't compete visually with the centered brand mark below. */}
      <button
        type="button"
        onClick={onClose}
        aria-label="Close auth dialog"
        className="fixed right-4 top-4 z-30 inline-flex h-11 w-11 items-center justify-center rounded-full border border-[#111827]/10 bg-white/80 text-2xl font-light leading-none text-black shadow-[0_10px_24px_rgba(17,24,39,0.08)] backdrop-blur-md transition hover:bg-white sm:right-6 sm:top-6"
      >
        ×
      </button>

      <div className="flex min-h-full flex-col items-center justify-center px-4 py-6 sm:px-6 sm:py-8">
        {/* Real brand asset (public/logo.svg), same one used in the site
            header (HeroSection.jsx) and app shell -- previously this was a
            plain "OwnMove" text label standing in for it. */}
        <a href="/" className="mb-4 inline-flex sm:mb-5">
          <img src="/logo.svg" alt="OwnMove" className="h-8 w-auto sm:h-9" />
        </a>

        <div className="w-full max-w-[420px]">
          <MotionDiv
            className="relative overflow-hidden rounded-[28px] border border-[#111827]/10 bg-white/60 px-5 py-5 shadow-[0_24px_70px_rgba(96,86,176,0.1)] backdrop-blur-md sm:px-9 sm:py-6"
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.97 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_0%,rgba(255,224,187,0.28),transparent_32%),radial-gradient(circle_at_86%_8%,rgba(154,127,255,0.11),transparent_28%)]" />
            {/* Keyed by authMode and cross-faded with AnimatePresence so
                switching between log in / sign up / reset password slides
                the new form in rather than snapping straight to it --
                `initial={false}` skips this same animation on the dialog's
                very first paint, since the card-level entrance above
                already covers that moment. */}
            <AnimatePresence mode="wait" initial={false}>
              <MotionDiv
                key={authMode}
                className="relative z-10"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.18, ease: 'easeOut' }}
              >
              <div className="text-center">
                <h1 className="text-[1.35rem] font-semibold leading-tight tracking-tight text-black sm:text-[1.5rem]">{heading}</h1>
                <p className="mt-1 text-sm leading-6 text-[#4B5563] sm:mt-1">{subtitle}</p>
              </div>

              <form className="mt-4 space-y-3 sm:mt-5 sm:space-y-3" onSubmit={handleSubmit}>
                {authMode === 'signup' && (
                  <label className="block">
                    <span className="mb-1 block text-sm font-medium text-[#6B7280] sm:mb-1">Full name</span>
                    <input
                      type="text"
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      required
                      disabled={isSubmitting || needsEmailConfirmation}
                      className="h-11 w-full rounded-full border border-[#111827]/10 bg-white/82 px-5 text-sm text-black outline-none transition placeholder:text-[#9aa0aa] focus:border-black/35 focus:bg-white focus:shadow-[0_0_0_3px_rgba(17,24,39,0.05)] disabled:opacity-60 sm:h-11"
                      placeholder="Your name"
                    />
                  </label>
                )}

                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-[#6B7280] sm:mb-1">Email</span>
                  <input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                    disabled={isSubmitting || needsEmailConfirmation || resetEmailSent}
                    className="h-11 w-full rounded-full border border-[#111827]/10 bg-white/82 px-5 text-sm text-black outline-none transition placeholder:text-[#9aa0aa] focus:border-black/35 focus:bg-white focus:shadow-[0_0_0_3px_rgba(17,24,39,0.05)] disabled:opacity-60 sm:h-11"
                    placeholder="you@example.com"
                  />
                </label>

                {authMode !== 'forgot' && (
                  <label className="block">
                    <div className="mb-1 flex items-center justify-between sm:mb-1">
                      <span className="text-sm font-medium text-[#6B7280]">Password</span>
                      {authMode === 'login' && (
                        <button
                          type="button"
                          onClick={() => switchAuthMode('forgot')}
                          className="text-xs font-medium text-black underline underline-offset-2"
                        >
                          Forgot password?
                        </button>
                      )}
                    </div>
                    <span className="relative block">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        required
                        minLength={6}
                        disabled={isSubmitting || needsEmailConfirmation}
                        className="h-11 w-full rounded-full border border-[#111827]/10 bg-white/82 px-5 pr-12 text-sm text-black outline-none transition placeholder:text-[#9aa0aa] focus:border-black/35 focus:bg-white focus:shadow-[0_0_0_3px_rgba(17,24,39,0.05)] disabled:opacity-60 sm:h-11"
                        placeholder="Enter password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((shown) => !shown)}
                        disabled={isSubmitting || needsEmailConfirmation}
                        title={showPassword ? 'Hide password' : 'Show password'}
                        className="absolute right-4 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full text-[#6B7280] transition hover:text-black disabled:opacity-60"
                      >
                        {showPassword ? <EyeIcon /> : <EyeSlashIcon />}
                      </button>
                    </span>
                  </label>
                )}

                {authMode !== 'forgot' && (
                  <label className="flex items-start gap-2 pt-0 sm:pt-1">
                    <input
                      type="checkbox"
                      checked={acceptedTerms}
                      onChange={(event) => setAcceptedTerms(event.target.checked)}
                      disabled={isSubmitting || needsEmailConfirmation}
                      className="mt-0.5 h-4 w-4 shrink-0 rounded border-[#111827]/18 accent-[#7b62e8]"
                    />
                    <span className="text-xs leading-5 text-[#6B7280]">
                      I agree to the{' '}
                      <a
                        href="/terms"
                        className="font-medium text-black underline underline-offset-2"
                      >
                        Terms & Conditions
                      </a>
                    </span>
                  </label>
                )}

                <button
                  type="submit"
                  disabled={isSubmitting || needsEmailConfirmation || resetEmailSent}
                  className="h-11 w-full cursor-pointer rounded-full bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-sm font-semibold text-white shadow-[0_8px_20px_rgba(101,89,227,0.18)] transition hover:-translate-y-0.5 hover:shadow-[0_12px_28px_rgba(101,89,227,0.28)] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 sm:h-11"
                >
                  {authMode === 'forgot'
                    ? (isSubmitting ? 'Sending…' : resetEmailSent ? 'Link sent' : 'Send reset link')
                    : isSubmitting
                    ? (authMode === 'login' ? 'Logging in…' : 'Creating account…')
                    : (authMode === 'login' ? 'Log in' : 'Create account')}
                </button>

                {formError && (
                  <p className="rounded-[14px] border border-[#e2a4a4]/60 bg-[#fdf2f2] px-4 py-3 text-xs font-medium text-[#a03a3a]" role="alert">
                    {formError}
                  </p>
                )}
                {formMessage && (
                  <p className="rounded-[14px] border border-[#111827]/10 bg-white/65 px-4 py-3 text-xs font-medium text-[#6B7280]">
                    {formMessage}
                  </p>
                )}
              </form>

              {!needsEmailConfirmation && authMode !== 'forgot' && (
                <>
                  <div className="my-4 grid grid-cols-[1fr_auto_1fr] items-center gap-3 sm:my-4">
                    <span className="h-px bg-[#111827]/12" />
                    <span className="text-xs font-medium text-[#8b929d]">or continue with</span>
                    <span className="h-px bg-[#111827]/12" />
                  </div>

                  <button
                    type="button"
                    onClick={handleGoogleClick}
                    className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-full border border-[#111827]/18 bg-white/50 px-4 text-sm font-medium text-black transition hover:bg-white hover:shadow-[0_10px_24px_rgba(17,24,39,0.05)] sm:h-10"
                  >
                    <GoogleIcon />
                    Google
                  </button>

                  {showGoogleSetup && (
                    <div className="mt-4 rounded-[18px] border border-[#111827]/10 bg-white/70 p-4 shadow-[0_10px_24px_rgba(17,24,39,0.04)]">
                      <p className="text-xs font-semibold text-black">Google sign-in setup needed</p>
                      <ol className="mt-2 list-decimal space-y-1 pl-4 text-xs leading-4 text-[#6B7280]">
                        {GOOGLE_SETUP_STEPS.map((step) => (
                          <li key={step}>{step}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                </>
              )}

              {/* Single mode-toggle line, centered inside the card just like
                  the rest of the form -- previously this (and a second,
                  redundant Terms & Conditions link) lived outside the card
                  in a two-column row that read as misaligned/disconnected
                  from the form above it. */}
              <p className="mt-4 text-center text-sm text-[#6B7280] sm:mt-4">
                {authMode === 'forgot'
                  ? 'Remembered your password?'
                  : authMode === 'login'
                  ? "Don't have an account?"
                  : 'Already have an account?'}{' '}
                <button
                  type="button"
                  onClick={() =>
                    switchAuthMode(authMode === 'forgot' ? 'login' : authMode === 'login' ? 'signup' : 'login')
                  }
                  className="font-medium text-black underline underline-offset-2"
                >
                  {authMode === 'forgot' ? 'Log in' : authMode === 'login' ? 'Sign up' : 'Log in'}
                </button>
              </p>
              </MotionDiv>
            </AnimatePresence>
          </MotionDiv>
        </div>
      </div>
    </MotionDiv>,
    document.body
  );
}

export default AuthDialog;
