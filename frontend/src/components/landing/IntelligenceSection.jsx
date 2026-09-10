import React, { useEffect, useRef, useState } from 'react';

// Small monochrome glyphs for the macOS-style menu bar — inline SVG rather
// than the private-use Apple logo character () or system icon fonts, since
// those only render on real macOS and would show as empty boxes for most
// visitors to this landing page.
function AppleGlyph({ className = '' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor">
      <path d="M16.365 1.43c0 1.14-.415 2.15-1.246 3.03-.995 1.05-2.19 1.66-3.51 1.55-.06-1.11.44-2.24 1.2-3.02.86-.9 2.28-1.55 3.44-1.6.04.02.07.03.11.04zM20.6 17.11c-.55 1.28-.81 1.86-1.52 2.99-.99 1.58-2.39 3.54-4.12 3.56-1.53.02-1.93-.99-4-1-2.08-.01-2.52 1.02-4.05 1-1.73-.02-3.06-1.79-4.05-3.36C.28 16.83-.72 11.28 1.7 7.68c1.15-1.72 3.14-2.81 5.02-2.84 1.63-.03 2.86 1.11 4.05 1.11 1.14 0 2.79-1.37 4.9-1.17 3.1.24 4.65 2.31 5.55 4.15-1.96 1.19-3.03 3.36-2.6 5.98.29 1.77 1.44 3.03 2.62 3.33-.05.17-.4.87-.64 1.87z" />
    </svg>
  );
}

function SearchGlyph({ className = '' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
      <circle cx="10.5" cy="10.5" r="6.5" />
      <line x1="20" y1="20" x2="15.3" y2="15.3" />
    </svg>
  );
}

function WifiGlyph({ className = '' }) {
  return (
    <svg viewBox="0 0 24 18" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M2 6c5.5-5.5 14.5-5.5 20 0" />
      <path d="M5.8 10c3.4-3.4 9-3.4 12.4 0" />
      <path d="M9.6 14c1.3-1.3 3.5-1.3 4.8 0" />
      <circle cx="12" cy="17" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

function BatteryGlyph({ className = '' }) {
  return (
    <svg viewBox="0 0 26 14" className={className} fill="none" stroke="currentColor" strokeWidth="1.4">
      <rect x="1" y="1.5" width="21" height="11" rx="2.5" />
      <rect x="3" y="3.3" width="15.5" height="7.4" rx="1.2" fill="currentColor" stroke="none" opacity="0.85" />
      <path d="M24 5v4" strokeLinecap="round" />
    </svg>
  );
}

function ControlCenterGlyph({ className = '' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <rect x="3" y="4" width="8" height="8" rx="2" />
      <rect x="13" y="4" width="8" height="4" rx="2" />
      <rect x="13" y="10" width="8" height="4" rx="2" />
      <rect x="3" y="16" width="18" height="4" rx="2" />
    </svg>
  );
}

function LockGlyph({ className = '' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="10" width="14" height="10" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

// Menu bar clock — reads the visitor's real system time instead of a
// hardcoded date/time, so the mockup never shows a stale "Thu Jul 30" no
// matter when someone actually loads the page.
const MENU_BAR_WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MENU_BAR_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function formatMenuBarClock(date) {
  const weekday = MENU_BAR_WEEKDAYS[date.getDay()]
  const month = MENU_BAR_MONTHS[date.getMonth()]
  const day = date.getDate()
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const hour24 = date.getHours()
  const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12
  const meridiem = hour24 >= 12 ? 'PM' : 'AM'
  return `${weekday} ${month} ${day} ${hour12}:${minutes} ${meridiem}`
}

function useMenuBarClock() {
  const [label, setLabel] = useState(() => formatMenuBarClock(new Date()))

  useEffect(() => {
    const id = window.setInterval(() => {
      setLabel(formatMenuBarClock(new Date()))
    }, 1000)

    return () => window.clearInterval(id)
  }, [])

  return label
}

// Raw unicode dingbats (⚖ ◈ ◎ ➤ ⇄) rendered at wildly inconsistent visual
// weights next to each other — a filled triangle beside hairline rings
// beside a heavy scale glyph — which is the same "thrown together" tell
// this session already fixed once in WorkAiSection. Real SVGs in the same
// 24x24 / ~1.8px-stroke line-icon language used everywhere else on the site
// fix that, and each one now actually maps to its tab's meaning (scale for
// a decision, a rising line for strengthening a profile, search+check for
// evaluating something, a send-arrow for the next move, a compass for
// exploring a direction) instead of being interchangeable abstract shapes.
const decideIcon = (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3v18M7 21h10M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" />
    <path d="m19 7 3 9c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
    <path d="m5 7 3 9c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
  </svg>
);
const improveIcon = (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 7 13.5 15.5 8.5 10.5 2 17" />
    <path d="M16 7h6v6" />
  </svg>
);
const opportunityIcon = (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="10" cy="10" r="6.5" />
    <path d="M7.2 10 9.4 12.2 13 8" />
    <path d="m19.5 19.5-4.3-4.3" />
  </svg>
);
const prioritizeIcon = (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round">
    <path d="M3 11 22 2 13 21 11 13 3 11Z" />
  </svg>
);
const exploreIcon = (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="9.2" />
    <path d="m15.5 8.5-1.8 5.2-5.2 1.8 1.8-5.2 5.2-1.8Z" />
  </svg>
);
const chevronDownIcon = (
  <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
    <path d="m6 9 6 6 6-6" />
  </svg>
);

// The five tabs used to just re-list AI Coach / Profile Analysis / Career
// Roadmap / Career Simulation / Discover — i.e. the same five features the
// rest of the page already explains. That taught a visitor nothing new.
// Instead, each tab now represents a real situation a student would actually
// bring to the AI Coach (a decision, a profile question, an opportunity to
// vet, a priority call, a direction to think through) — the demo shows what
// the assistant is like to talk to, not a menu of feature names.
const categories = [
  { id: 'decide', title: 'Make a Decision', subtitle: 'Compare my options', icon: decideIcon },
  { id: 'improve', title: 'Strengthen My Profile', subtitle: 'Find my highest-impact move', icon: improveIcon },
  { id: 'opportunity', title: 'Evaluate an Opportunity', subtitle: 'Is this worth pursuing?', icon: opportunityIcon },
  { id: 'prioritize', title: 'Plan My Next Move', subtitle: 'Decide what matters now', icon: prioritizeIcon },
  { id: 'explore', title: 'Explore a Direction', subtitle: 'Think through a new path', icon: exploreIcon },
]

const intelligenceContent = {
  decide: {
    prompt: 'Should I take the startup internship or wait for the larger company’s offer?',
    assistant: 'AI Coach',
    badge: 'Based on your profile',
    consideredLabel: 'Based on your context',
    considered: ['Target role', 'Current experience', 'Profile gaps', 'Timeline'],
    paragraphs: [
      {
        lead: 'The startup offer moves you faster —',
        rest: ' you’d own real analytics work within weeks, which closes the hands-on-experience gap your Profile Analysis flagged. The bigger company gives you a stronger name and mentorship, but a slower ramp.',
      },
      {
        lead: 'Given your timeline, I’d lean',
        rest: ' toward the startup — it closes your biggest gap faster. Want me to update your Career Roadmap to reflect this path?',
      },
    ],
  },
  improve: {
    prompt: 'What’s the single most valuable thing I could add to my profile this month?',
    assistant: 'AI Coach',
    badge: 'Highest-impact move',
    consideredLabel: 'What I considered',
    considered: ['Target: LLM Engineer', 'Current skills', 'Existing projects', 'Profile Analysis'],
    paragraphs: [
      {
        lead: 'Your biggest gap isn’t another course —',
        rest: ' it’s visible proof of applied LLM work.',
      },
      {
        lead: 'Build one substantial project',
        rest: ' that demonstrates retrieval, evaluation, and deployment rather than adding another introductory certification.',
      },
    ],
  },
  opportunity: {
    prompt: 'Is this AI internship actually a good fit for where I’m trying to go?',
    assistant: 'AI Coach',
    badge: 'Opportunity evaluated',
    consideredLabel: 'Compared against',
    considered: ['Target role', 'Skills required', 'Existing experience', 'Current roadmap'],
    paragraphs: [
      {
        lead: 'Strong fit for experience,',
        rest: ' weaker fit for specialization.',
      },
      {
        lead: 'The role gives you real production exposure,',
        rest: ' but it leans generalist — it won’t move you closer to the LLM-specific depth your roadmap is targeting. Worth taking if you need the experience now.',
      },
    ],
  },
  prioritize: {
    prompt: 'I have one month. What should I focus on first?',
    assistant: 'AI Coach',
    badge: '3 priorities ranked',
    consideredLabel: 'Your current priorities',
    considered: ['Ship one role-relevant project', 'Strengthen one missing technical area', 'Apply to high-fit opportunities'],
    paragraphs: [
      {
        lead: 'Why this order?',
        rest: ' Your Profile Analysis shows the project gap is what’s actually blocking recruiter interest right now — the other two compound once that’s in place.',
      },
      {
        lead: 'Once that project is live,',
        rest: ' applying becomes far more effective, since your profile will finally back up what you’re applying for.',
      },
    ],
  },
  explore: {
    prompt: 'I’m interested in AI engineering and research. Which direction currently fits my profile better?',
    assistant: 'AI Coach',
    badge: 'Explore both paths →',
    consideredLabel: 'Signals in your profile',
    considered: ['AI engineering signals', 'Research signals', 'Current projects', 'Profile evidence'],
    paragraphs: [
      {
        lead: 'Your current profile has stronger signals for AI engineering.',
        rest: '',
      },
      {
        lead: 'Research could still be a viable direction,',
        rest: ' but your profile currently lacks research-specific evidence such as publications, research projects, or lab experience.',
      },
    ],
  },
}

function useTypewriterParagraphs(paragraphs, shouldStart, resetKey, speed = 22, pause = 650) {
  const [visibleTexts, setVisibleTexts] = useState(paragraphs.map(() => ''))
  const [activeIndex, setActiveIndex] = useState(0)
  const [charIndex, setCharIndex] = useState(0)

  // Reset during render rather than in an effect (same "adjusting state
  // when a prop changes" pattern used in AppShell.jsx for the profile
  // draft) — avoids the extra render pass an effect-based reset causes,
  // and the cascading-render lint warning that comes with calling setState
  // synchronously inside a useEffect body.
  const [trackedParagraphs, setTrackedParagraphs] = useState(paragraphs)
  const [trackedResetKey, setTrackedResetKey] = useState(resetKey)
  if (paragraphs !== trackedParagraphs || resetKey !== trackedResetKey) {
    setTrackedParagraphs(paragraphs)
    setTrackedResetKey(resetKey)
    setVisibleTexts(paragraphs.map(() => ''))
    setActiveIndex(0)
    setCharIndex(0)
  }

  useEffect(() => {
    if (!shouldStart) return
    if (activeIndex >= paragraphs.length) return

    if (charIndex < paragraphs[activeIndex].rest.length) {
      const timer = window.setTimeout(() => {
        setVisibleTexts((current) =>
          current.map((text, index) =>
            index === activeIndex
              ? paragraphs[index].rest.slice(0, charIndex + 1)
              : text,
          ),
        )
        setCharIndex((current) => current + 1)
      }, speed)

      return () => window.clearTimeout(timer)
    }

    const nextTimer = window.setTimeout(() => {
      setActiveIndex((current) => current + 1)
      setCharIndex(0)
    }, pause)

    return () => window.clearTimeout(nextTimer)
  }, [activeIndex, charIndex, paragraphs, pause, shouldStart, speed])

  return {
    visibleTexts,
    isTyping: shouldStart && activeIndex < paragraphs.length,
    activeParagraph: activeIndex,
  }
}

function IntelligenceSection() {
  const sectionRef = useRef(null)
  const menuBarClock = useMenuBarClock()
  const [hasStartedTyping, setHasStartedTyping] = useState(false)
  const [activeCategory, setActiveCategory] = useState('decide')
  const activeContent = intelligenceContent[activeCategory]
  const { visibleTexts, isTyping, activeParagraph } = useTypewriterParagraphs(
    activeContent.paragraphs,
    hasStartedTyping,
    activeCategory,
  )

  useEffect(() => {
    const node = sectionRef.current
    if (!node || hasStartedTyping) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setHasStartedTyping(true)
          observer.disconnect()
        }
      },
      { threshold: 0.35 },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [hasStartedTyping])

  return (
    <section ref={sectionRef} className="relative overflow-hidden bg-[linear-gradient(180deg,#090b16_0%,#141b36_18%,#1f2550_46%,#171d3d_74%,#090d1b_100%)] text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(146,110,255,0.22),transparent_20%),radial-gradient(circle_at_14%_18%,rgba(255,220,182,0.1),transparent_16%),radial-gradient(circle_at_82%_22%,rgba(130,111,255,0.14),transparent_18%),linear-gradient(180deg,rgba(255,255,255,0.02),rgba(7,9,20,0.14)_24%,rgba(6,8,18,0.42)_100%)]" />

      <div className="relative mx-auto max-w-[1360px] px-6 pb-10 pt-6 sm:px-10 lg:px-12">
        {/* Intro copy so the MacBook mockup doesn't just appear out of
            nowhere — it earns the visual by first explaining what "career
            context, connected" actually means. */}
        <div className="relative z-10 mx-auto max-w-[680px] pb-10 text-center sm:pb-14">
          <h2 className="text-[clamp(2rem,3.6vw,3.2rem)] font-medium leading-[1.05] tracking-[-0.04em] text-white">
            Your journey doesn&apos;t happen in pieces.
          </h2>
          <p className="mx-auto mt-4 max-w-[600px] text-[clamp(0.98rem,1.05vw,1.12rem)] leading-7 text-white/60">
            Your profile shapes your opportunities. Your goals shape your roadmap. And when you&apos;re unsure what to do next, your AI Coach helps you make sense of it all.
          </p>
        </div>

        {/* MacBook mockup — everything below (category tabs + the chat demo)
            renders "on the screen" of a laptop chrome built from CSS (metal
            display casing + black glass bezel + camera notch) rather than an
            SVG wrapping real HTML, since SVG can't reliably host live React
            content (foreignObject is brittle across browsers) — this reads
            as a MacBook display while staying fully responsive and keeping
            every interaction (category switching, typewriter) intact. No
            keyboard deck/base below the screen — just the display itself,
            sitting on its own grounding shadow. */}
        <div className="relative mx-auto w-full max-w-[1220px] pb-4">
          {/* grounding shadow, so the laptop reads as sitting in front of the
              dark backdrop instead of floating flat against it */}
          <div className="pointer-events-none absolute inset-x-[8%] bottom-0 h-8 rounded-full bg-black/40 blur-2xl" />

          {/* thin aluminum display casing — light silver to match a real
              MacBook's finish (and to pop against the light page background) */}
          <div className="relative rounded-[28px] bg-[linear-gradient(175deg,#f6f7f9_0%,#e2e3e8_14%,#c7c9d0_42%,#aeb0b8_70%,#94969f_100%)] p-[3px] shadow-[0_40px_70px_-24px_rgba(20,18,40,0.3)] sm:rounded-[32px] sm:p-[5px]">
            {/* thick black glass bezel */}
            <div className="relative overflow-hidden rounded-[24px] bg-[#0a0a0d] px-4 pb-4 pt-7 sm:rounded-[28px] sm:px-5 sm:pb-5 sm:pt-9">
              {/* camera notch, cut into the very top of the glass */}
              <div className="absolute left-1/2 top-0 z-30 flex h-[15px] w-[100px] -translate-x-1/2 items-center justify-center rounded-b-[11px] bg-[#050506] ring-1 ring-white/[0.06] sm:h-[18px] sm:w-[124px]">
                <span className="h-[4px] w-[4px] rounded-full bg-[#171b26] ring-1 ring-white/10">
                  <span className="block h-[2px] w-[2px] translate-x-[1px] translate-y-[1px] rounded-full bg-white/25" />
                </span>
              </div>

              {/* screen surface */}
              <div className="relative overflow-hidden rounded-[17px] bg-[#06070f] sm:rounded-[21px]">
                {/* faint glass glare across the glass, purely decorative */}
                <div className="pointer-events-none absolute inset-0 z-20 bg-[linear-gradient(115deg,rgba(255,255,255,0.05)_0%,rgba(255,255,255,0)_26%)]" />

                {/* macOS menu bar */}
                <div className="relative z-10 flex items-center justify-between border-b border-white/[0.06] bg-[#131417]/95 px-4 py-1.5 text-[11px] font-medium text-white/72 sm:px-5">
                  <div className="flex items-center gap-3.5 sm:gap-4">
                    <AppleGlyph className="h-3 w-3 text-white/85" />
                    <span className="font-semibold text-white/92">Finder</span>
                    <span className="hidden sm:inline">File</span>
                    <span className="hidden sm:inline">Edit</span>
                    <span className="hidden sm:inline">View</span>
                    <span className="hidden lg:inline">Go</span>
                    <span className="hidden lg:inline">Window</span>
                    <span className="hidden lg:inline">Help</span>
                  </div>
                  <div className="flex items-center gap-3 text-white/65 sm:gap-3.5">
                    <SearchGlyph className="h-3 w-3" />
                    <ControlCenterGlyph className="hidden h-3 w-3 sm:block" />
                    <WifiGlyph className="h-3 w-3" />
                    <BatteryGlyph className="h-3.5 w-6" />
                    <span className="hidden text-[10.5px] tabular-nums text-white/60 sm:inline">{menuBarClock}</span>
                  </div>
                </div>

                {/* Safari-style browser toolbar */}
                <div className="relative z-10 flex items-center gap-3 border-b border-white/[0.06] bg-[#0d0e11] px-4 py-2 sm:px-5">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
                  </div>
                  <div className="hidden items-center gap-2 text-[13px] text-white/25 sm:flex">
                    <span>‹</span>
                    <span>›</span>
                  </div>
                  <div className="mx-auto flex w-full max-w-[300px] items-center justify-center gap-1.5 rounded-md bg-white/[0.06] px-3 py-1 text-[11px] text-white/50">
                    <LockGlyph className="h-2.5 w-2.5" />
                    <span>ownmove.ai</span>
                  </div>
                  <span className="hidden text-[15px] leading-none text-white/25 sm:inline">+</span>
                </div>

                <div className="relative px-4 pb-5 pt-4 sm:px-6 sm:pb-6 lg:px-7">
                <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-5">
                  {categories.map((category) => (
                    <button
                      key={category.id}
                      type="button"
                      onClick={() => setActiveCategory(category.id)}
                      className={`rounded-[18px] border px-3.5 py-3 text-left shadow-[0_18px_34px_rgba(12,12,30,0.22)] transition hover:translate-y-[-1px] ${
                        activeCategory === category.id
                          ? 'border-[#7b82ff]/45 bg-[linear-gradient(180deg,rgba(23,27,52,0.96),rgba(30,35,68,0.92))] shadow-[0_18px_36px_rgba(92,99,255,0.14)]'
                          : 'border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.04))]'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[13px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.12),rgba(255,255,255,0.06))] text-[#ddd5ff] shadow-[0_8px_18px_rgba(18,18,38,0.2)]">
                          {category.icon}
                        </div>
                        <div className="min-w-0">
                          <div className="truncate text-[clamp(0.9rem,0.98vw,1.05rem)] font-medium tracking-[-0.04em] text-white">
                            {category.title}
                          </div>
                          <div className="truncate text-[clamp(0.74rem,0.78vw,0.86rem)] text-white/50">
                            {category.subtitle}
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>

                <div className="intelligence-stage intelligence-stage-glow relative mt-3.5 overflow-hidden rounded-[24px] border border-white/8 bg-[linear-gradient(180deg,rgba(84,84,176,0.24)_0%,rgba(33,38,86,0.42)_100%)] px-3.5 pb-2.5 pt-3.5 shadow-[0_22px_54px_rgba(10,10,28,0.34)] sm:px-5 sm:pb-3 lg:px-6 lg:pb-3.5">
                  <div className="intelligence-grid absolute inset-0 opacity-40" />

                  <div className="relative mx-auto max-w-[1120px]">
                    <div className="intelligence-panel intelligence-panel-accent intelligence-panel-glow relative overflow-hidden rounded-[26px] border border-white/10 bg-[linear-gradient(180deg,rgba(11,14,28,0.98)_0%,rgba(18,22,42,0.96)_100%)] px-5 pb-5 pt-5 shadow-[0_20px_52px_rgba(8,8,20,0.38)] sm:px-7 lg:px-9">
                      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-[linear-gradient(180deg,rgba(11,14,28,0),rgba(10,12,24,0.84))]" />
                      <div className="mx-auto max-w-[680px]">
                        <div className="flex justify-end">
                          <div className="max-w-[500px] rounded-[22px] rounded-br-[9px] border border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.1)_0%,rgba(255,255,255,0.06)_100%)] px-5 py-3 text-left text-[clamp(0.9rem,0.9vw,0.98rem)] text-white/82 shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_10px_24px_rgba(10,10,26,0.14)] backdrop-blur-xl">
                            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/46">
                              You
                            </div>
                            <div>{activeContent.prompt}</div>
                          </div>
                        </div>

                        <div className="mt-4 rounded-[22px] border border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.03))] px-5 py-4 shadow-[0_16px_32px_rgba(10,10,26,0.2)] backdrop-blur-xl">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex items-center gap-3">
                              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[linear-gradient(180deg,#8370ff,#4450ff)] text-xs font-semibold text-white shadow-[0_10px_24px_rgba(68,80,255,0.24)]">
                                AI
                              </div>
                              <div>
                                <div className="text-[clamp(0.92rem,0.94vw,1rem)] font-semibold text-white">
                                  {activeContent.assistant}
                                </div>
                                <div className="text-[11.5px] text-white/42">Reasoned answer with sources</div>
                              </div>
                            </div>

                            <div className="rounded-full border border-white/8 bg-white/6 px-3 py-[5px] text-[11px] font-medium text-white/58">
                              {activeContent.badge}
                            </div>
                          </div>

                          <div className="mt-3 flex items-center gap-2 text-[clamp(0.86rem,0.9vw,0.94rem)] font-medium text-white/54">
                            {chevronDownIcon}
                            <span>Show thinking</span>
                          </div>

                          <div className="mt-3">
                            <div className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-white/40">
                              {activeContent.consideredLabel}
                            </div>
                            {/* Badges used to be positioned with a fixed
                                `top: index * 38px` offset, which assumes every
                                "considered" label is exactly one line. On a
                                narrow phone some of these labels wrap to two
                                lines, and the fixed offset would misalign the
                                next badge against the wrapped text. Each row
                                is now its own positioning context, so the
                                badge always sits at that row's own top edge
                                no matter how tall the row above it grew. */}
                            <div className="border-l border-white/8 pl-[22px]">
                              {activeContent.considered.map((item, index) => (
                                <div key={item} className={`relative ${index === activeContent.considered.length - 1 ? '' : 'mb-2.5'}`}>
                                  <div className="absolute left-[-33px] top-0 flex h-[22px] w-[22px] items-center justify-center rounded-full bg-[linear-gradient(180deg,rgba(255,255,255,0.24),rgba(146,133,255,0.16))] text-[10px] font-semibold text-white shadow-[0_2px_6px_rgba(0,0,0,0.16)]">
                                    {index + 1}
                                  </div>
                                  <div className="text-[clamp(0.88rem,0.92vw,0.96rem)] text-white/84">{item}</div>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="mt-4 min-h-[112px] border-t border-white/8 pt-4 text-[clamp(0.88rem,0.92vw,0.96rem)] leading-[1.6] text-white/74">
                            {activeContent.paragraphs.map((paragraph, index) => (
                              <p key={index} className={index === 1 ? 'mt-3' : ''}>
                                <strong>{paragraph.lead}</strong>
                                {visibleTexts[index]}
                                {isTyping && activeParagraph === index ? (
                                  <span className="ml-0.5 inline-block h-[1.05em] w-[2px] translate-y-[2px] animate-pulse bg-[#b8a4ff]" />
                                ) : null}
                              </p>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    <button className="absolute bottom-4 right-4 flex h-10 w-10 items-center justify-center rounded-full border-[3px] border-[#1e2141] bg-[linear-gradient(180deg,#5864ff,#4450ff)] text-lg text-white shadow-[0_16px_30px_rgba(68,80,255,0.28)] transition hover:translate-y-[-2px]">
                      →
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default IntelligenceSection;
