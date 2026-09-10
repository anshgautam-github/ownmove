import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import learningJourney from '../../data/learningJourney';

// Capitalized aliases rather than `<MotionDiv>`/`<MotionButton>`/etc.
// directly as JSX tags: this repo's eslint config has no `eslint-plugin-react`
// (only the hooks/refresh plugins), so core no-unused-vars never sees
// `motion` referenced by a dotted JSX tag name (a JSXMemberExpression) the
// way it sees a plain `<AnimatePresence>` (a JSXIdentifier) — it would flag
// `motion` as unused despite being used all over this file. Framer Motion's
// `motion` export is a proxy that caches `motion.div`/`motion.button`/etc.
// per key, so grabbing each once at module scope is exactly how the library
// expects it to be used — not a new component identity per render.
const MotionDiv = motion.div;
const MotionButton = motion.button;

// Simple Icons' "google" glyph is the plain monochrome wordmark-style "G"
// outline, not Google's actual four-color "G" — so the same tint-with-
// accent-color treatment that correctly reproduces every other single-
// color brand mark here (Microsoft, AWS, Oracle, ...) was flattening
// Google's own logo into a solid blue shape nobody would recognize as it.
// Google is the one company on this list whose real mark isn't a single
// color, so it gets its own inline SVG (the standard four-color "G",
// unmodified — the same mark Google's own developer docs distribute for
// products to identify a Google-run platform) instead of going through
// the tinted-CDN pipeline at all.
function GoogleMark({ className = '' }) {
  return (
    <svg viewBox="0 0 48 48" className={className} aria-hidden="true">
      <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z" />
      <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z" />
      <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z" />
      <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z" />
    </svg>
  );
}

// Three-tier fallback chain rather than a single external source, since a
// single logo API (Clearbit, tried previously) can go down or start
// blocking hotlinked requests wholesale and silently take every logo on
// the page down with it:
//   1. Simple Icons (`iconSlug`) — a static SVG CDN of real brand marks,
//      tinted with the company's own `accent` color. Vector, so it's crisp
//      at any size (fixes the blurriness) and it's the actual brand shape
//      (fixes Salesforce showing a generic cloud instead of its logo).
//   2. Google's favicon service (`domain`) — a live per-site icon, lower
//      resolution but a reasonable second try if a slug is ever wrong.
//   3. The colored monogram (`fallbackLabel`) — always renders.
// `id === 'google'` skips straight to the real inline mark above instead
// of entering that chain at all.
function CheckpointLogo({ id, iconSlug, domain, alt, fallbackLabel, accent }) {
  const [stage, setStage] = useState(0);

  if (id === 'google') {
    return <GoogleMark className="h-full w-full object-contain p-1.5" />;
  }

  if (stage >= 2) {
    return (
      <div
        className="flex h-full w-full items-center justify-center rounded-full text-[11px] font-black leading-none text-white"
        style={{ backgroundColor: accent }}
      >
        {fallbackLabel}
      </div>
    );
  }

  const src = stage === 0
    ? `https://cdn.simpleicons.org/${iconSlug}/${accent.replace('#', '')}`
    : `https://www.google.com/s2/favicons?domain=${domain}&sz=128`;

  return (
    <img
      key={stage}
      src={src}
      alt={alt}
      className="h-full w-full rounded-full object-contain p-1.5"
      onError={() => setStage((s) => s + 1)}
    />
  );
}

// A tidy, evenly-spaced grid tile rather than a loose floating bubble —
// each platform gets equal weight (icon + name, same size, same alignment),
// which is what actually reads as "professional" for a set of unrelated
// items, as opposed to a scattered cluster.
function CheckpointTile({ checkpoint, isActive, onToggle }) {
  return (
    <MotionButton
      type="button"
      onClick={onToggle}
      // The old hover (border-white/70 -> white/90, bg-white/60 -> white/80)
      // was a ~20% opacity nudge — barely showed up against this panel's own
      // near-white background, same issue as the Categories sidebar and top
      // nav had. A stronger lift plus a real shadow makes hovering a tile
      // actually register. This used to also add a soft ring in the
      // company's own accent color, but that ring was visually near-
      // identical to the *selected* tile's ring below (just a few points
      // lower alpha) — so simply moving the mouse over a different tile
      // made it look like two platforms were selected at once, with no
      // real way to tell "hovering" apart from "selected". Hover now only
      // lifts the tile; the colored ring is reserved for the one tile that
      // is actually active, so exactly one boundary is ever highlighted.
      whileHover={!isActive ? { y: -4, boxShadow: '0 18px 34px -16px rgba(40,50,30,0.4)' } : undefined}
      whileTap={{ scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 320, damping: 24 }}
      className={`group flex flex-col items-center gap-2.5 rounded-2xl border p-4 text-center backdrop-blur-md transition-colors duration-200 ${
        isActive
          ? 'border-transparent bg-white/95 shadow-[0_16px_32px_-16px_rgba(40,50,30,0.4)]'
          : 'border-white/70 bg-white/60 hover:border-white hover:bg-white'
      }`}
      style={isActive ? { boxShadow: `0 0 0 2px ${checkpoint.accent}55, 0 16px 32px -16px rgba(40,50,30,0.4)` } : undefined}
    >
      <span
        className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/70 bg-white/90 transition-transform duration-200 group-hover:scale-110"
        style={{ boxShadow: isActive ? `0 0 0 3px ${checkpoint.accent}22` : 'none' }}
      >
        <CheckpointLogo id={checkpoint.id} iconSlug={checkpoint.iconSlug} domain={checkpoint.domain} alt={checkpoint.company} fallbackLabel={checkpoint.fallbackLabel} accent={checkpoint.accent} />
      </span>
      {/* block + w-full, not just min-w-0 on an inline <span>: block
          establishes a definite width for the text below to wrap against,
          which an inline element doesn't do on its own. Platform names
          wrap to up to 2 lines (line-clamp-2) instead of being cut off
          with an ellipsis — the company name is short enough everywhere to
          stay on one line, but names like "Google Cloud Skills Boost"
          genuinely need the second line to read in full. The fixed
          min-height keeps every tile in a row the same height regardless
          of whether its neighbor wrapped to 1 or 2 lines. */}
      <span className="block w-full min-w-0">
        <p className="truncate text-[12px] font-black leading-tight text-[#1a1a1a]">{checkpoint.company}</p>
        <p className="mt-1 line-clamp-2 min-h-[2.4em] text-[10px] font-semibold leading-tight text-[#8a8a86]">{checkpoint.tileLabel || checkpoint.platform}</p>
      </span>
    </MotionButton>
  );
}

function InfoCard({ checkpoint }) {
  return (
    <MotionDiv
      key={checkpoint.id}
      initial={{ opacity: 0, y: 18, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 18, scale: 0.97 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="relative overflow-hidden rounded-[24px] border border-white/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.88)_0%,rgba(255,255,255,0.62)_100%)] p-5 shadow-[inset_0_1.5px_0_rgba(255,255,255,0.95),0_24px_48px_-24px_rgba(40,50,30,0.4)] backdrop-blur-2xl sm:p-6"
    >
      <div
        className="pointer-events-none absolute -right-16 -top-16 h-52 w-52 rounded-full opacity-40 blur-[80px]"
        style={{ background: checkpoint.accent }}
      />
      <div className="relative flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <span className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-white/70 bg-white/80 p-2 shadow-[0_10px_24px_-12px_rgba(40,50,30,0.35)]">
            <CheckpointLogo id={checkpoint.id} iconSlug={checkpoint.iconSlug} domain={checkpoint.domain} alt={checkpoint.company} fallbackLabel={checkpoint.fallbackLabel} accent={checkpoint.accent} />
          </span>
          <div className="min-w-0">
            <p className="text-[12px] font-black uppercase tracking-wide" style={{ color: checkpoint.accent }}>{checkpoint.company}</p>
            <h3 className="text-[18px] font-black leading-tight tracking-tight text-[#1a1a1a] sm:text-[19px]">{checkpoint.platform}</h3>
            <p className="mt-1 max-w-md text-[13px] font-medium leading-relaxed text-[#5a5a58]">{checkpoint.description}</p>
          </div>
        </div>
        <a
          href={checkpoint.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex shrink-0 items-center gap-1.5 self-start rounded-full px-5 py-2.5 text-[13px] font-bold text-white shadow-[0_14px_28px_-12px_rgba(40,50,30,0.5)] transition-transform duration-200 hover:-translate-y-0.5"
          style={{ background: `linear-gradient(135deg, ${checkpoint.accent} 0%, #1a1a1a 145%)` }}
        >
          Visit Platform
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M7 17 17 7M9 7h8v8" /></svg>
        </a>
      </div>

      <div className="relative mt-5 flex flex-wrap items-center gap-x-8 gap-y-3 border-t border-white/60 pt-4">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="mr-1 text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Topics</span>
          {checkpoint.topics.map((topic) => (
            <span key={topic} className="rounded-full border border-white/70 bg-white/70 px-2.5 py-1 text-[11px] font-bold text-[#4a4a48]">{topic}</span>
          ))}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10.5px] font-black uppercase tracking-wide text-[#9a9a97]">Difficulty</span>
          <span className="text-[12px] font-bold text-[#4a4a48]">{checkpoint.difficulty}</span>
        </div>
        <span className="inline-flex items-center gap-1 text-[11.5px] font-bold text-[#2f8f4e]">
          Official Platform
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M5 13l4 4L19 7" /></svg>
        </span>
      </div>
    </MotionDiv>
  );
}

export default function LearningJourney() {
  const [activeId, setActiveId] = useState(null);

  const activeIndex = learningJourney.findIndex((c) => c.id === activeId);
  const active = activeIndex >= 0 ? learningJourney[activeIndex] : null;

  const toggle = (id) => setActiveId((prev) => (prev === id ? null : id));

  return (
    <div className="custom-scroll mt-3 flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto overflow-x-hidden pb-1">
      {/* One evenly-spaced grid — same tile size, same alignment, for every
          platform — reads as a clean, deliberate shelf of options rather
          than a scattered pile. No connecting lines between tiles, since
          these are independent platforms with no real relationship.
          Below `sm`, picking one used to leave all ~14 tiles in place
          above the info card, so seeing the info meant scrolling past the
          entire shelf first — this now collapses the grid to just the
          compact "selected platform" row underneath once something's
          active, so the info card sits right below it instead. sm+ always
          shows the full grid (there's room for both there, and the active
          tile's own ring already marks the selection). */}
      <div className={`grid-cols-2 gap-3 rounded-[24px] border border-white/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.55)_0%,rgba(255,255,255,0.3)_100%)] p-4 shadow-[inset_0_1.5px_0_rgba(255,255,255,0.9)] backdrop-blur-xl sm:grid sm:grid-cols-4 sm:gap-4 sm:p-5 lg:grid-cols-7 ${active ? 'hidden' : 'grid'}`}>
        {learningJourney.map((checkpoint) => (
          <CheckpointTile
            key={checkpoint.id}
            checkpoint={checkpoint}
            isActive={checkpoint.id === activeId}
            onToggle={() => toggle(checkpoint.id)}
          />
        ))}
      </div>

      {/* Compact "selected platform" row — only shown below `sm`, and only
          once a platform is active (sm+ relies on the full grid above
          instead, which never collapses there). Tapping it clears the
          selection so the full grid comes back and a different platform
          can be picked, without needing to scroll back up past the info
          card first. */}
      {active && (
        <button
          type="button"
          onClick={() => setActiveId(null)}
          className="flex shrink-0 items-center gap-3 rounded-2xl border border-white/70 bg-white/70 p-3 text-left backdrop-blur-xl sm:hidden"
          style={{ boxShadow: `0 0 0 2px ${active.accent}55, inset 0 1px 0 rgba(255,255,255,0.9)` }}
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/70 bg-white/90">
            <CheckpointLogo id={active.id} iconSlug={active.iconSlug} domain={active.domain} alt={active.company} fallbackLabel={active.fallbackLabel} accent={active.accent} />
          </span>
          <span className="min-w-0 flex-1">
            <p className="truncate text-[12.5px] font-black leading-tight text-[#1a1a1a]">{active.company}</p>
            <p className="text-[10.5px] font-semibold text-[#8a8a86]">Tap to choose a different platform</p>
          </span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 shrink-0 text-[#9a9a97]"><path d="M6 9l6 6 6-6" /></svg>
        </button>
      )}

      {/* Floating info card */}
      <AnimatePresence mode="wait">
        {active ? (
          <InfoCard checkpoint={active} />
        ) : (
          <MotionDiv
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center gap-1.5 rounded-[24px] border border-dashed border-white/70 bg-white/40 px-6 py-8 text-center"
          >
            <span className="rounded-full bg-white/80 px-3 py-1 text-[10px] font-black uppercase tracking-wide text-[#7a7a76]">Tap a platform</span>
            <p className="max-w-sm text-[12.5px] font-semibold text-[#7a7a76]">Select any company to see what they teach.</p>
          </MotionDiv>
        )}
      </AnimatePresence>
    </div>
  );
}
