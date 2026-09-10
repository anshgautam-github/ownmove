import React from 'react';
import founderPhoto from '../../assets/founder.jpeg';

// Real line icons (same 24x24, 1.8-2px stroke language used across the rest
// of the app) instead of raw unicode glyphs (⟲ ◎ ⌲) — those symbols were the
// biggest tell that this panel was thrown together rather than designed;
// swapping in purpose-built SVGs makes each card read as an intentional
// step rather than generic placeholder art.
const graphIcon = (
  <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="6" cy="6" r="2.4" /><circle cx="18" cy="6" r="2.4" /><circle cx="12" cy="18" r="2.4" />
    <path d="M7.9 7.4 10.4 16.3M16.1 7.4 13.6 16.3M8.4 6h7.2" />
  </svg>
);
const scanIcon = (
  <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16" />
    <circle cx="12" cy="12" r="3.2" />
  </svg>
);
const routeIcon = (
  <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="5.5" cy="18.5" r="2" /><circle cx="18.5" cy="5.5" r="2" />
    <path d="M7.2 17.3 13 9.8a3 3 0 0 1 4.7-.2l.3.3" />
  </svg>
);
const checkIcon = (
  <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 13l4 4L19 7" />
  </svg>
);

function WorkAiSection() {
  return (
    <section className="relative overflow-hidden bg-[linear-gradient(180deg,#ffffff_0%,#fbfbff_100%)] text-[#141231]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_90%,rgba(124,122,255,0.14),transparent_28%),radial-gradient(circle_at_86%_8%,rgba(118,129,255,0.22),transparent_24%),linear-gradient(90deg,rgba(255,255,255,0.82),rgba(242,242,255,0.56)_60%,rgba(255,255,255,0.84))]" />

      <div className="relative mx-auto max-w-[1380px] px-6 py-18 sm:px-10 lg:px-12">
        <div className="grid items-center gap-10 lg:grid-cols-[minmax(520px,1fr)_minmax(430px,0.82fr)]">
          <div className="workai-visual relative min-h-[480px] sm:min-h-[440px] lg:min-h-[560px]">
            {/* The old orbit ring was a bare decorative circle with nothing
                tying it to the content — it read as leftover "AI network"
                clip art rather than something intentional, and it also left
                the space below the card stack (right of Career Snapshot)
                empty. This curve replaces it with an actual connective
                line — profile in, through the steps, down into the
                snapshot — which is literally what the paragraph on the
                right says ("we connect the dots"). */}
            <svg
              className="pointer-events-none absolute inset-0 h-full w-full"
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <defs>
                <linearGradient id="workaiConnectLine" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#7b62e8" />
                  <stop offset="100%" stopColor="#4651ff" />
                </linearGradient>
              </defs>
              <path
                d="M16 15 C46 4, 60 24, 47 37 C36 49, 56 54, 50 67"
                fill="none"
                stroke="url(#workaiConnectLine)"
                strokeWidth="0.5"
                strokeDasharray="0.5 2.6"
                strokeLinecap="round"
                opacity="0.4"
                vectorEffect="non-scaling-stroke"
              />
              <circle cx="16" cy="15" r="1" fill="#7b62e8" opacity="0.55" />
              <circle cx="50" cy="67" r="1" fill="#4651ff" opacity="0.55" />
            </svg>

            {/* The top-left quadrant sat empty — just the bare orbit ring
                with nothing to anchor it. This chip gives the graph a
                starting point ("your profile" feeds the steps stacked to
                its right) instead of leaving that corner as dead air. */}
            <div className="workai-chip absolute left-[2%] top-[4%] flex items-center rounded-full px-5 py-2.5 text-[clamp(0.82rem,0.92vw,0.96rem)] font-semibold text-[#1d1d2f] z-40 transition-transform duration-300 hover:-translate-y-1">
              <img
                src={founderPhoto}
                alt=""
                className="mr-2.5 h-6 w-6 shrink-0 rounded-full object-cover ring-2 ring-white/80"
              />
              Your Profile
            </div>

            {/* Badge — trimmed from three down to just one, softer lift on
                hover (matches the rest of the site's button hover language)
                instead of a scale-pop. */}
            <div className="workai-chip absolute bottom-[9%] right-[1%] flex items-center rounded-full px-6 py-3 text-[clamp(0.9rem,1vw,1.08rem)] font-semibold text-[#1d1d2f] z-40 transition-transform duration-300 hover:-translate-y-1">
              <svg viewBox="0 0 24 24" width="16" height="16" className="mr-2.5 text-[#4651ff]" stroke="currentColor" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="6.5" /><path d="M20 20l-3.5-3.5" />
              </svg>
              Finding Best Matches
            </div>

            {/* Stacked Cards — 58% of this container's width worked at the
                desktop widths this was designed at (~650-700px column), but
                on a narrow phone (this container can be ~300px wide) that
                same 58% left barely 150px of usable text width, forcing
                captions like "Building your career graph" onto a second
                line the stacked z-index/scale/translate offsets weren't
                built to absorb. Widening these on mobile (back down to the
                original 58%/68% from sm up, where it's already verified to
                look right) keeps captions on one line at narrow widths. */}
            <div className="absolute right-[0%] top-[19%] w-[84%] sm:w-[58%] rotate-[0.6deg] rounded-[22px] border border-[#6771ff]/35 bg-[linear-gradient(180deg,rgba(255,255,255,0.98)_0%,rgba(246,245,255,0.94)_100%)] backdrop-blur-md px-6 py-5 shadow-[0_16px_32px_rgba(75,87,255,0.16)] z-30">
              <div className="flex items-center gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#eef0ff] text-[#4651ff]">
                  {graphIcon}
                </div>
                <div className="text-[clamp(1.05rem,1.2vw,1.35rem)] font-semibold text-[#3340cf]">
                  Building your career graph
                </div>
              </div>
            </div>

            <div className="absolute right-[0%] top-[32%] w-[84%] sm:w-[58%] rounded-[22px] border border-white/80 bg-[linear-gradient(90deg,rgba(255,255,255,0.72),rgba(250,250,255,0.92))] px-6 py-4 shadow-[0_14px_26px_rgba(117,112,214,0.08)] z-20 scale-[0.96] origin-top translate-y-[-6px] backdrop-blur-sm">
              <div className="flex items-center gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#eef0ff]/85 text-[#4651ff]">{scanIcon}</div>
                <div className="text-[14.5px] font-semibold text-[#5157a8]">Matching signals to real roles</div>
              </div>
            </div>

            <div className="absolute right-[0%] top-[44%] w-[84%] sm:w-[58%] rounded-[22px] border border-white/50 bg-[linear-gradient(90deg,rgba(255,255,255,0.42),rgba(250,250,255,0.62))] px-6 py-4 shadow-[0_14px_26px_rgba(117,112,214,0.04)] z-10 scale-[0.92] origin-top translate-y-[-12px] backdrop-blur-[2px]">
              <div className="flex items-center gap-4 opacity-70">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#eef0ff]/55 text-[#7880ff]">{routeIcon}</div>
                <div className="text-[13.5px] font-semibold text-[#8288c2]">Charting the path ahead</div>
              </div>
            </div>

            {/* Bottom 360 Card */}
            <div className="absolute bottom-[2%] left-[4%] w-[88%] sm:w-[68%] rotate-[-0.4deg] rounded-[28px] border border-[#d6d9ff]/80 bg-white/95 backdrop-blur-xl px-7 py-7 shadow-[0_24px_48px_rgba(40,46,160,0.11)] z-30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <img
                    src={founderPhoto}
                    alt=""
                    className="h-7 w-7 shrink-0 rounded-full object-cover ring-2 ring-white"
                  />
                  <div className="text-[clamp(1.15rem,1.25vw,1.35rem)] font-semibold tracking-tight text-[#171a27]">
                    Career Snapshot
                  </div>
                </div>
                <div className="text-[11px] font-medium text-[#9a9fb8]">Updated today</div>
              </div>
              <div className="mt-5 space-y-4 text-[clamp(0.9rem,0.95vw,1rem)] text-[#4b5163] font-medium">
                <div className="flex items-center gap-3">
                  <div className="flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full bg-[#ecefff] text-[#4651ff]">{checkIcon}</div>
                  Google STEP
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full bg-[#ecefff] text-[#4651ff]">{checkIcon}</div>
                  Microsoft Explore
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full bg-[#ecefff] text-[#4651ff]">{checkIcon}</div>
                  MLH Fellowship
                </div>
              </div>
              <div className="mt-7 space-y-2.5">
                <div className="h-3 rounded-full bg-[#f1f2fa]" />
                <div className="h-3 w-[85%] rounded-full bg-[#f5f6fc]" />
              </div>
            </div>
          </div>

          {/* justify-self-end and whitespace-nowrap were both unconditional
              — fine at the lg+ two-column layout this was designed for, but
              below lg the grid collapses to one column and "end" shrinks
              this box to fit its content instead of filling the row, which
              on a narrow phone could shove the whole heading/paragraph over
              against the right edge instead of using the full width. Both
              are now gated to lg so mobile gets a normal, full-width, left
              read column, and the header only forces a single line once the
              two-column layout guarantees there's room for it. */}
          <div className="max-w-[560px] lg:justify-self-end lg:text-left">
            <h2 className="max-w-none text-[clamp(2rem,3.1vw,3.05rem)] font-medium leading-[1.15] tracking-[-0.05em] text-[#110d32] lg:whitespace-nowrap">
              <span className="block">Know where you stand.</span>
              <span className="block text-[#4651ff]">See where you could go.</span>
            </h2>

            <p className="mt-8 max-w-[540px] text-[clamp(1.08rem,1.22vw,1.45rem)] leading-[1.55] text-[#3d4152]">
             Every experience, project, and skill tells part of your story. We connect the dots, highlight what sets you apart, and guide you toward opportunities where you're most likely to succeed.
            </p>

            {/* <div className="mt-12 flex flex-wrap items-center gap-8">
              <button className="rounded-full bg-[#3f4bff] px-9 py-4 text-[clamp(1.05rem,1.15vw,1.18rem)] font-medium text-white shadow-[0_18px_36px_rgba(63,75,255,0.2)] transition hover:translate-y-[-1px]">
                Get a demo
              </button>
              <button className="inline-flex items-center gap-4 text-[clamp(1.02rem,1.15vw,1.15rem)] font-medium text-[#4250ff] transition hover:text-[#3f4bff]">
                Watch video
                <span className="text-[#d6d8ff] text-xl leading-none">›</span>
              </button>
            </div> */}
          </div>
        </div>
      </div>
    </section>
  )
}

export default WorkAiSection;