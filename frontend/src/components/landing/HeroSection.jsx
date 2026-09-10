import React, { useEffect, useState } from 'react';
import AuthDialog from '../auth/AuthDialog';
import { supabase } from '../../services/supabase/client';

// What OwnMove actually surfaces — not a company-logo wall, since the
// company logos already live in the orbit visual to the right. This
// reinforces the breadth of opportunity types instead of repeating brands.
const discoveryCategories = [
  'Fellowships',
  'Open Source',
  'Student Programs',
  'Hackathons',
  'Research',
  'Scholarships',
  'Ambassador Programs',
  'Competitions',
  'Communities',
  'Events',
  'Conferences',
  'Certifications',
]

// Small line icons for the "Discover / Understand / Decide" strip below the
// headline — same three-step framing already used for the capabilities
// section further down the page, just echoed here in miniature so the left
// column isn't just a headline floating over empty space.
const heroDiscoverIcon = (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.8-3.8" />
  </svg>
);
const heroUnderstandIcon = (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 12h4l2.2-6.5 3.6 13 2.2-6.5H21" />
  </svg>
);
const heroDecideIcon = (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="8.5" /><path d="M14.8 9.2 12.6 12.6 9.2 14.8l2.2-3.4z" />
  </svg>
);

// Ring radii as a percentage of the (square) orbit stage — must match the
// three ring divs' h/w percentages in OrbitVisual (43% / 63% / 83% diameter
// -> 21.5 / 31.5 / 41.5 radius) so anything placed "on" a ring actually sits
// on that ring's circumference, not just near it.
const RING_RADIUS = { inner: 21.5, mid: 31.5, outer: 41.5 };

// Places an item's *center* exactly on a ring's circumference at the given
// angle (degrees, clockwise from 12 o'clock) — trig instead of eyeballed
// top/left percentages, so the orbit is a true circle of satellites rather
// than photos scattered near-but-not-on the ring lines.
function pointOnRing(ring, angleDeg) {
  const r = RING_RADIUS[ring];
  const rad = (angleDeg * Math.PI) / 180;
  return {
    top: `${50 - r * Math.cos(rad)}%`,
    left: `${50 + r * Math.sin(rad)}%`,
  };
}

// Four of the eight CDN logo requests came back broken last render (visible
// in the screenshot as broken-image icons with fallback alt text). Rather
// than keep guessing at simpleicons.org slugs blind — the sandbox has no
// route to that host to verify against, and a shared free icon CDN can also
// just be rate-limiting concurrent requests — those four are drawn locally
// instead: a real (tiny, exact) SVG for Microsoft's four-square mark, and
// styled wordmarks for IBM/Adobe/Amazon, none of which depend on a network
// request succeeding. Apple, Meta, and NVIDIA render correctly as CDN
// images. Google is also drawn locally (the same
// four-color "G" mark already used in AuthDialog.jsx's sign-in button) since
// the CDN version renders as a flat single-color "G" instead of the real
// brand mark.
function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="h-full w-full">
      <path fill="#4285F4" d="M22.6 12.23c0-.79-.07-1.54-.2-2.27H12v4.29h5.94a5.08 5.08 0 0 1-2.2 3.34v2.77h3.57c2.09-1.93 3.29-4.77 3.29-8.13Z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.65l-3.57-2.77c-.99.66-2.25 1.05-3.71 1.05-2.86 0-5.29-1.93-6.16-4.53H2.18v2.86A11 11 0 0 0 12 23Z" />
      <path fill="#FBBC05" d="M5.84 14.1a6.61 6.61 0 0 1 0-4.2V7.04H2.18a11 11 0 0 0 0 9.92l3.66-2.86Z" />
      <path fill="#EA4335" d="M12 5.37c1.61 0 3.06.55 4.2 1.64l3.16-3.16A10.59 10.59 0 0 0 12 1 11 11 0 0 0 2.18 7.04L5.84 9.9C6.71 7.3 9.14 5.37 12 5.37Z" />
    </svg>
  );
}

function MicrosoftMark() {
  return (
    <svg viewBox="0 0 24 24" className="h-full w-full">
      <rect x="1" y="1" width="10" height="10" fill="#F25022" />
      <rect x="13" y="1" width="10" height="10" fill="#7FBA00" />
      <rect x="1" y="13" width="10" height="10" fill="#00A4EF" />
      <rect x="13" y="13" width="10" height="10" fill="#FFB900" />
    </svg>
  );
}

function IbmMark() {
  return <span className="text-[15px] font-black tracking-tight text-[#052FAD]">IBM</span>;
}

function AdobeMark() {
  return <span className="text-[15px] font-black italic tracking-tight text-[#FA0F00]">Adobe</span>;
}

function AmazonMark() {
  return (
    <div className="flex flex-col items-center">
      <span className="text-[13px] font-bold leading-none tracking-tight text-[#161616]">amazon</span>
      <svg viewBox="0 0 32 10" className="mt-0.5 h-2 w-7">
        <path d="M1 2c6 5 24 5 30 0" fill="none" stroke="#FF9900" strokeWidth="2" strokeLinecap="round" />
        <path d="M27 1.5 31 2l-1.5 3.5" fill="none" stroke="#FF9900" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

// Companies whose programs show up in the product. Split across the middle
// and outer rings, replacing the people photos entirely.
//
// Angles are laid out on a single shared 45°-apart grid (0/45/90/.../315)
// rather than independently even-spacing the mid-ring trio and outer-ring
// quintet. Those two spacings (120° and 72°) drift in and out of phase with
// each other, so some rotation of the outer set always lands within ~12° of
// a mid-ring item, close enough for the two badges to visually overlap even
// though they sit on different ring radii (IBM/Meta did exactly this at
// mid:240 vs outer:234). A single shared 45° grid guarantees every badge is
// at least 45° from every other badge, which — combined with the 10-point
// gap between the mid (31.5) and outer (41.5) ring radii — keeps every pair
// comfortably clear of each other.
const orbitLogos = [
  // Google sits at the very top (angle 0) — same as Microsoft (45°) and
  // NVIDIA (315°) either side of it, so all three need very different
  // radii or they land at nearly the same height and read as a flat row
  // instead of an arc. Moving Google out to the outer ring (same radius as
  // its two neighbors) instead of the mid ring makes it the clear apex —
  // ~68px higher than the other two — so the top of the orbit actually
  // curves.
  { id: 'google', name: 'Google', Mark: GoogleMark, ring: 'outer', angle: 0 },
  { id: 'microsoft', name: 'Microsoft', Mark: MicrosoftMark, ring: 'outer', angle: 45 },
  // IBM and Amazon moved onto the innermost ring (same angles as before, so
  // no new angular collisions) — the inner ring previously had zero badges
  // on it, which made the orbit read as two rings, not three. Placed at
  // 90°/180°, directly across from each other, so they don't crowd either
  // side of the center "1k+ Programs" text.
  { id: 'adobe', name: 'Adobe', Mark: AdobeMark, ring: 'inner', angle: 90 },
  { id: 'ibm', name: 'IBM', Mark: IbmMark, ring: 'outer', angle: 135 },
  { id: 'amazon', name: 'Amazon', Mark: AmazonMark, ring: 'inner', angle: 180 },
  // Meta and Apple swapped rings (angles unchanged). Before, the outer ring
  // — the biggest, most visible circle — had badges at 0/45/135/270/315 and
  // nothing at all from 135° to 270°, a full 135° dead arc through the
  // bottom-left. Moving Meta from mid to outer at 225° fills that gap;
  // moving Apple from outer to mid at 270° keeps the outer ring's angular
  // spacing even (now every ~45-90° apart, never more).
  // Mercedes-Benz isn't in the simpleicons set (confirmed while wiring up
  // the Opportunities section below — that brand's logo request there was
  // silently falling back until it got switched to this same source), so
  // this uses Google's favicon service keyed to the real domain instead of
  // a slug that would just 404 in this orbit (which has no onError
  // fallback of its own like the LogoMark component does).
  { id: 'mercedes-benz', name: 'Mercedes-Benz', src: 'https://www.google.com/s2/favicons?domain=mercedes-benz.com&sz=128', ring: 'outer', angle: 225 },
  { id: 'apple', name: 'Apple', src: 'https://cdn.simpleicons.org/apple', ring: 'mid', angle: 270 },
  { id: 'nvidia', name: 'NVIDIA', src: 'https://cdn.simpleicons.org/nvidia', ring: 'outer', angle: 315 },
];

const LOGO_BADGE = 'clamp(38px, 12.14cqw, 68px)';

// Counts up from 0 to `target` on mount (eased, not linear) instead of
// just appearing — this runs once when OrbitVisual first mounts, which is
// immediately on page load since it sits above the fold in the hero.
function useCountUp(target, duration = 1600) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    let frame;
    const startTime = performance.now();

    const tick = (now) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  return value;
}

// Mirrors how the final "1k+" reads while it's still counting up — plain
// numbers below 1000 (so the climb feels like counting), then "k+" once it
// crosses the thousand mark.
function formatCompactCount(value) {
  return value >= 1000 ? `${Math.floor(value / 1000)}k+` : `${value}`;
}

function OrbitVisual() {
  const programsCount = useCountUp(1000);

  return (
    <div className="relative mx-auto aspect-square w-full max-w-[560px] @container">
      <div className="absolute left-1/2 top-1/2 h-[43%] w-[43%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#171321]/12" />
      <div className="absolute left-1/2 top-1/2 h-[63%] w-[63%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#171321]/12" />
      <div className="absolute left-1/2 top-1/2 h-[83%] w-[83%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#171321]/10" />

      {/* The center stat used to be bare text floating with no container at
          all, while every single logo around it sits in a proper glass
          badge — backwards, since "1k+ Programs" is the actual headline
          number this whole visual exists to show off, not just another node
          on the ring. Giving it the same glass treatment (just bigger) makes
          it read as the anchor the logos orbit around instead of an
          afterthought in the middle.
          Sizing math: Adobe/Amazon sit on the innermost ring at 21.5% radius
          (120px in a 560px visual) and the badges are 68px wide, so their
          inner edge is ~86px from center. At 29% diameter this circle's
          radius was ~81px — only ~5px of clearance, which is why it read as
          crowding both badges. 24% diameter keeps the radius at ~67px,
          leaving a real ~19px gap on every side instead. */}
      <div className="hero-stat-orbit absolute left-1/2 top-1/2 flex h-[24%] w-[24%] -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-full border border-white/60 bg-white/55 shadow-[0_20px_44px_rgba(23,19,33,0.14)] backdrop-blur-xl">
        <span className="relative z-10 text-[clamp(1.5rem,7.86cqw,2.75rem)] font-semibold leading-none tracking-tight text-[#171321] tabular-nums">{formatCompactCount(programsCount)}</span>
        <span className="relative z-10 mt-2 text-[clamp(0.75rem,2.5cqw,0.875rem)] text-[#171321]/55">Programs</span>
      </div>

      {orbitLogos.map((logo) => {
        const pos = pointOnRing(logo.ring, logo.angle);
        return (
          <div
            key={logo.id}
            title={logo.name}
            className="absolute flex -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-2xl border border-white/60 bg-white/45 p-[clamp(6px,2.5cqw,14px)] shadow-[0_10px_24px_rgba(23,19,33,0.1)] backdrop-blur-xl"
            style={{ top: pos.top, left: pos.left, height: LOGO_BADGE, width: LOGO_BADGE }}
          >
            {logo.Mark ? <logo.Mark /> : <img src={logo.src} alt={logo.name} className="h-full w-full object-contain" />}
          </div>
        );
      })}
    </div>
  );
}

function HeroSection() {
  const [authMode, setAuthMode] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  // The nav links were `hidden md:flex` with no fallback at all below that
  // breakpoint — on any phone or small tablet, "Opportunities / How It
  // Works / About / Contact / FAQ" simply didn't exist anywhere on the
  // page. This adds the standard hamburger-toggle pattern instead, so
  // mobile visitors still have a way to jump to every section.
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    let active = true;

    supabase.auth.getSession().then(({ data }) => {
      if (active) setCurrentUser(data.session?.user || null);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      if (active) setCurrentUser(session?.user || null);
    });

    return () => {
      active = false;
      subscription.subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    const handleOpenAuth = (e) => {
      setAuthMode(e.detail || 'login');
    };
    window.addEventListener('open-auth', handleOpenAuth);
    return () => window.removeEventListener('open-auth', handleOpenAuth);
  }, []);

  // There's no standalone "/dashboard" route in the app anymore (only
  // /discover, /career-ai, /profile, /saved exist — see App.jsx's
  // SHELL_ROUTES) — that URL just silently falls through to the landing
  // page again. Discover is the real logged-in home.
  const goToDiscover = () => window.location.assign('/discover');

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setCurrentUser(null);
  };

  return (
    <section className="relative min-h-screen overflow-hidden bg-white text-[#171321]">
      {/* Same diagonal wash, just re-keyed light: cream corner easing through
          soft lavender/purple and out to a pale, near-white edge instead of
          dropping down to violet-black. */}
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(128deg,#fdf3e0_0%,#f6e6d6_9%,#f0ddf0_20%,#ddc8f2_36%,#cdbdf0_52%,#dfe1f5_72%,#f5f6fb_88%,#ffffff_100%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_60%_at_78%_38%,rgba(123,98,232,0.08),transparent_60%)]" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1380px] flex-col px-6 pb-6 pt-6 sm:px-10 lg:px-12">
        <header className="flex items-end justify-between gap-6">
          <div className="flex items-end gap-10">
            <div className="flex items-end">
              {/* Real brand asset (public/logo.svg), shown as-is with no
                  badge/tile wrapper. The flower sits above the "wn Move"
                  text and its lower petals dip below the text's own
                  baseline, so the image's bounding box doesn't coincide
                  with where the wordmark's baseline actually is. items-end
                  on the row + a calibrated nudge down on the image pulls
                  its actual text baseline level with the nav links'
                  baseline. Left side confirmed correct — do not change. */}
              <img src="/logo.svg" alt="OwnMove" className="h-14 w-auto translate-y-[7px] sm:h-16 sm:translate-y-[9px]" />
            </div>

            {/* Discover already lives as its own button on the right, and
                Career AI is a tab inside the app rather than its own
                marketing destination — repeating both here was redundant.
                "Why OwnMove" as a nav label was also too long — standard
                SaaS nav items are single short words (About, Contact, FAQ),
                not full sentences. Both still point at real sections: About
                goes to the founder/trust section, Contact goes to the FAQ
                section's own "Contact Support" card rather than a page that
                doesn't exist. */}
            <nav className="hidden items-center gap-8 text-[17px] text-[#171321]/70 md:flex">
              <a href="#demo-section" className="transition hover:text-[#171321]">Opportunities</a>
              <a href="#how-it-works" className="transition hover:text-[#171321]">How It Works</a>
              <a href="#why-ownmove" className="transition hover:text-[#171321]">About</a>
              <a href="#faq" className="transition hover:text-[#171321]">Contact</a>
            </nav>
          </div>

          <div className="flex items-center gap-3 translate-y-[9px]">
            {/* This group (mobile toggle, Log out, Discover) sat higher
                than the left-side nav links once the header switched to
                items-end for the logo fix: items-end puts this whole
                block's bottom edge at the row bottom, but the Discover
                pill's own text sits well above its box's bottom edge
                (button padding), unlike plain nav text. Nudge the block
                down so Discover/Log out's text baseline meets the nav
                links' baseline, without changing how Log out and Discover
                sit relative to each other (still items-center). */}
            <button
              type="button"
              onClick={() => setMobileNavOpen((open) => !open)}
              aria-expanded={mobileNavOpen}
              aria-label={mobileNavOpen ? 'Close menu' : 'Open menu'}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/70 bg-white/70 text-[#171321] backdrop-blur-md transition hover:bg-white md:hidden"
            >
              {mobileNavOpen ? (
                <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
              ) : (
                <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
              )}
            </button>

            {currentUser ? (
              <>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="hidden text-sm font-medium text-[#171321]/60 transition hover:text-[#171321] sm:inline"
                >
                  Log out
                </button>
                <button
                  type="button"
                  onClick={goToDiscover}
                  className="premium-glass-cta items-center rounded-full px-6 py-3 text-sm font-semibold"
                >
                  <span className="relative z-10">Discover</span>
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setAuthMode('signup')}
                className="premium-glass-cta items-center rounded-full px-6 py-3 text-sm font-semibold"
              >
                <span className="relative z-10">Join Now</span>
              </button>
            )}
          </div>
        </header>

        {mobileNavOpen && (
          <div className="mt-3 flex flex-col gap-1 rounded-2xl border border-white/60 bg-white/90 p-2.5 text-[15px] font-medium text-[#171321]/75 shadow-[0_20px_44px_rgba(23,19,33,0.12)] backdrop-blur-xl md:hidden">
            <a href="#demo-section" onClick={() => setMobileNavOpen(false)} className="rounded-xl px-3.5 py-2.5 transition hover:bg-white hover:text-[#171321]">Opportunities</a>
            <a href="#how-it-works" onClick={() => setMobileNavOpen(false)} className="rounded-xl px-3.5 py-2.5 transition hover:bg-white hover:text-[#171321]">How It Works</a>
            <a href="#why-ownmove" onClick={() => setMobileNavOpen(false)} className="rounded-xl px-3.5 py-2.5 transition hover:bg-white hover:text-[#171321]">About</a>
            <a href="#faq" onClick={() => setMobileNavOpen(false)} className="rounded-xl px-3.5 py-2.5 transition hover:bg-white hover:text-[#171321]">Contact</a>
            <a href="#faq" onClick={() => setMobileNavOpen(false)} className="rounded-xl px-3.5 py-2.5 transition hover:bg-white hover:text-[#171321]">FAQ</a>
            {currentUser && (
              <button type="button" onClick={() => { setMobileNavOpen(false); handleLogout(); }} className="rounded-xl px-3.5 py-2.5 text-left transition hover:bg-white hover:text-[#171321] sm:hidden">
                Log out
              </button>
            )}
          </div>
        )}

        <div className="grid flex-1 grid-cols-1 items-center gap-10 py-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-6 lg:py-2">
          <div className="relative z-10 mx-auto max-w-[720px] text-center lg:mx-0 lg:pt-0 lg:text-left">
            <h1 className="mx-auto max-w-[680px] text-[clamp(2.6rem,4.6vw,4.7rem)] font-semibold leading-[0.96] tracking-[-0.06em] lg:mx-0">
              <span className="block text-[#171321]">Find opportunities</span>
              <span className="block text-[#171321]">that actually fit you</span>
              <span className="block pt-4 text-[0.88em] leading-[0.98] tracking-[-0.05em] text-[#7b4fd9]">
                and know what
              </span>
              <span className="block text-[0.88em] leading-[0.98] tracking-[-0.05em] text-[#7b4fd9]">
                to do next.
              </span>
            </h1>

            {/* Was `text-[#171321]/60` — translucent black blending into the
                cream/lavender wash behind it read as washed-out and slightly
                muddy rather than intentional. A solid plum-gray (no opacity
                trick) that sits between the headline's near-black and its
                purple accent reads as a deliberate color choice instead of
                "black, but faded." */}
            <p className="mx-auto mt-6 max-w-[540px] text-[clamp(1.05rem,1.2vw,1.2rem)] font-medium leading-[1.65] tracking-[-0.01em] text-[#59516c] lg:mx-0">
              We surface exclusive opportunities you haven&apos;t heard of and won&apos;t find on a typical job board, including programs, fellowships, events, communities, and more, then help you understand where you stand and what to try next.
            </p>

            <div className="mx-auto mt-8 flex max-w-[540px] flex-wrap items-center justify-center gap-x-3 gap-y-2 text-[0.98rem] font-medium text-[#171321]/75 lg:mx-0 lg:justify-start">
              <span className="inline-flex items-center gap-2">
                <span className="text-[#7b4fd9]">{heroDiscoverIcon}</span>
                Discover
              </span>
              <span aria-hidden="true" className="text-[#171321]/25">→</span>
              <span className="inline-flex items-center gap-2">
                <span className="text-[#7b4fd9]">{heroUnderstandIcon}</span>
                Understand
              </span>
              <span aria-hidden="true" className="text-[#171321]/25">→</span>
              <span className="inline-flex items-center gap-2">
                <span className="text-[#7b4fd9]">{heroDecideIcon}</span>
                Decide
              </span>
            </div>
          </div>

          <div className="mx-auto w-full max-w-[420px] lg:mx-0 lg:max-w-none">
            <OrbitVisual />
          </div>
        </div>

        <footer className="marquee-mask relative z-10 mt-auto overflow-hidden pt-3">
          <div className="marquee-lane">
            <div className="marquee-rail">
              {[0, 1, 2, 3].map((group) => (
                <div key={group} className="marquee-group flex items-center" aria-hidden={group !== 0}>
                  {discoveryCategories.map((category) => (
                    <React.Fragment key={`${group}-${category}`}>
                      <button type="button"
                        className="marquee-item shrink-0 text-[clamp(1rem,1.45vw,1.7rem)] font-semibold tracking-tight text-[#171321]/35">
                        {category}
                      </button>
                      {/* Dot renders after every item, including the last one in
                          each group — the group's own padding-right (below)
                          matches this same gap value, so the seam where one
                          group wraps into the next reads identically to every
                          other word-to-word gap instead of looking tighter. */}
                      <span aria-hidden="true" className="shrink-0 text-[clamp(1rem,1.45vw,1.7rem)] text-[#171321]/20">
                        ·
                      </span>
                    </React.Fragment>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </footer>
      </div>
      {authMode && (
        <AuthDialog initialMode={authMode} onClose={() => setAuthMode(null)} />
      )}
    </section>
  )
}

export default HeroSection;
