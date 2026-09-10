import React, { useEffect, useRef, useState } from 'react';

const LaurelBranch = ({ flip }) => (
  <svg width="40" height="96" viewBox="0 0 60 140" className={flip ? 'scale-x-[-1]' : ''} fill="currentColor">
    <path d="M 40,130 Q 10,80 25,10" fill="none" stroke="currentColor" strokeWidth="2.5" />
    <path d="M 33,105 Q 55,95 45,75 Q 25,95 33,105 Z" />
    <path d="M 24,75 Q 45,65 35,45 Q 15,65 24,75 Z" />
    <path d="M 21,45 Q 40,35 30,15 Q 10,35 21,45 Z" />
    <path d="M 24,18 Q 38,5 25,-5 Q 5,10 24,18 Z" />
    <path d="M 37,118 Q 15,115 15,135 Q 30,140 37,118 Z" />
    <path d="M 27,88 Q 5,85 5,105 Q 20,110 27,88 Z" />
    <path d="M 22,58 Q 0,55 0,75 Q 15,80 22,58 Z" />
    <path d="M 22,28 Q 0,25 0,45 Q 15,50 22,28 Z" />
  </svg>
)

// Replaces the previous Apple/Play Store badges — those only make sense
// for a mobile app listing. A star (top rating) and a medal (top ranking)
// keep the same "award" visual language but read correctly for a website.
const StarBadgeIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" className="w-[34px] h-[34px] mb-2">
    <path d="M12 2.5l2.9 5.9 6.5.95-4.7 4.6 1.1 6.5L12 16.9l-5.8 3.05 1.1-6.5-4.7-4.6 6.5-.95L12 2.5Z" />
  </svg>
)

const MedalBadgeIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className="w-[34px] h-[34px] mb-2">
    <circle cx="12" cy="14.5" r="6" />
    <path d="M9.5 9.5 6.5 2.5M14.5 9.5l3-7" />
    <path d="M10.3 14.2 11.6 16.8 14.1 12.4" />
  </svg>
)

const blendColor = (from, to, amount) =>
  `rgb(${from.map((channel, index) => Math.round(channel + (to[index] - channel) * amount)).join(', ')})`

function ScrollChars({ text, progress, className, fromColor, toColor, gradient = false }) {
  const chars = Array.from(text)
  const revealSpan = 0.08

  return (
    <span className={className}>
      {chars.map((char, index) => {
        // Every character (including spaces) used to render as its own
        // `inline-block` span, and adjacent inline-block boxes with no real
        // whitespace text node between them in the DOM give the browser no
        // line-break opportunity — so this heading couldn't wrap at all and
        // would overflow horizontally on any narrow phone. Rendering the
        // space itself as a plain text node (not a styled inline-block)
        // restores a normal wrap point there while leaving the per-letter
        // reveal animation on every other character untouched.
        if (char === ' ') return ' '

        const charStart = index / Math.max(chars.length, 1)
        const charProgress = Math.min(Math.max((progress - charStart) / revealSpan, 0), 1)

        return (
          <span
            key={`${char}-${index}`}
            className="inline-block whitespace-pre transition-[color,transform] duration-200 ease-out"
            style={{
              color: gradient ? 'transparent' : blendColor(fromColor, toColor, charProgress),
              backgroundImage: gradient
                ? `linear-gradient(135deg, ${blendColor(fromColor, [36, 28, 84], charProgress)} 0%, ${blendColor(fromColor, [64, 46, 168], charProgress)} 44%, ${blendColor(fromColor, toColor, charProgress)} 100%)`
                : undefined,
              backgroundClip: gradient ? 'text' : undefined,
              WebkitBackgroundClip: gradient ? 'text' : undefined,
              transform: `translateY(${(1 - charProgress) * 1.5}px)`,
            }}
          >
            {char}
          </span>
        )
      })}
    </span>
  )
}

function StatsBannerSection() {
  const sectionRef = useRef(null)
  const [textProgress, setTextProgress] = useState(0)

  useEffect(() => {
    const updateProgress = () => {
      const node = sectionRef.current
      if (!node) return

      const rect = node.getBoundingClientRect()
      const viewportHeight = window.innerHeight || 1
      const start = viewportHeight * 0.52
      const end = viewportHeight * 0.18
      const raw = (start - rect.top) / (start - end)
      const delayed = (Math.min(Math.max(raw, 0), 1) - 0.08) / 0.92
      const clamped = Math.min(Math.max(delayed, 0), 1)
      setTextProgress(clamped)
    }

    updateProgress()
    window.addEventListener('scroll', updateProgress, { passive: true })
    window.addEventListener('resize', updateProgress)

    return () => {
      window.removeEventListener('scroll', updateProgress)
      window.removeEventListener('resize', updateProgress)
    }
  }, [])

  return (
    <div ref={sectionRef} className="flex w-full max-w-[1160px] flex-col items-center">
      <div className="w-full rounded-[24px] border border-[#e8ecfb] bg-[linear-gradient(135deg,#eef2fc_0%,#f6f2ff_48%,#edf6ff_100%)] py-12 px-6 sm:px-14 flex flex-col md:flex-row items-center justify-between text-[#0B1536] gap-8 shadow-[0_20px_50px_rgba(148,156,208,0.08)] mb-16">

        {/* Left Side: rating badge */}
        <div className="flex items-center gap-4">
           <LaurelBranch />
           <div className="flex flex-col items-center justify-center p-2">
             <StarBadgeIcon />
             <div className="text-[1.05rem] font-bold tracking-tight leading-tight">TOP RATED</div>
             <div className="text-[0.8rem] opacity-75 mt-0.5">Career Platform</div>
           </div>
           <LaurelBranch flip />
        </div>

        {/* Middle Stats — the big numerals were a flat 3.2rem regardless of
            viewport, and "15,000+" alone at that size is wider than most
            phone screens once you also account for the gap and divider on
            either side of it; clamp lets both numbers shrink to fit a narrow
            row instead of forcing horizontal overflow. */}
        <div className="flex items-center gap-6 sm:gap-10 md:gap-14">
           {/* Built for Students, by Design — a positioning statement
               rather than a number, so it doesn't use the big-numeral
               treatment the other two stats use (a phrase at that size
               would either overflow the row on a phone or force an ugly
               wrap); a smaller bold line + the same opacity-80 subtitle
               style the other stats use for their label keeps it visually
               part of the same row without pretending to be a number. */}
           <div className="flex flex-col items-center text-center">
             <div className="text-[1.3rem] sm:text-[1.5rem] font-semibold leading-snug tracking-tight mb-2">Built for Students</div>
             <div className="text-[1.05rem] opacity-80">by Design</div>
           </div>

           {/* Divider */}
           <div className="w-[1.5px] h-20 bg-[#0B1536]/20" />

           {/* Programs listed */}
           <div className="flex flex-col items-center">
             <div className="text-[clamp(2.1rem,7vw,3.2rem)] font-medium leading-none tracking-tight mb-2">1,000+</div>
             <div className="text-[1.05rem] opacity-80">Programs Listed</div>
           </div>
        </div>

        {/* Right Side: ranking badge */}
        <div className="flex items-center gap-4">
           <LaurelBranch />
           <div className="flex flex-col items-center justify-center p-2">
             <MedalBadgeIcon />
             <div className="text-[1.05rem] font-bold tracking-tight leading-tight">#1 CHOICE</div>
             <div className="text-[0.8rem] opacity-75 mt-0.5">For Students</div>
           </div>
           <LaurelBranch flip />
        </div>

      </div>

      <div className="flex flex-col items-center text-center mt-2">
        <h2 className="max-w-[90vw] text-[clamp(1.9rem,6vw,2.8rem)] font-light tracking-[-0.02em]">
          <ScrollChars
            text="Trusted By Students And Employers"
            progress={textProgress}
            className="inline-block"
            fromColor={[167, 174, 197]}
            toColor={[21, 18, 64]}
            gradient
          />
        </h2>
        <p className="mt-4 text-[0.95rem] font-medium text-[#7f879d]">
          OwnMove pairs real opportunities with an AI Coach that actually knows your profile — not just another job board.
        </p>
      </div>

    </div>
  )
}

export default StatsBannerSection;
