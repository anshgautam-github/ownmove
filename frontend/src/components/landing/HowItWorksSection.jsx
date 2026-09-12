import React, { useEffect, useRef, useState } from 'react';
import { supabase } from '../../services/supabase/client';
import { safeSetItem } from '../../utils/safeStorage';

// Same pattern DemoSection's "Explore More" button already uses: check for a
// live session, and either go straight to the destination or stash it as
// postLoginRedirect and open the auth dialog first — AuthDialog (and
// AuthCallbackScreen, for real OAuth) both already know to read
// postLoginRedirect and land the user there once they're signed in, instead
// of dumping everyone at the generic /discover or /onboarding default.
const CTA_TARGETS = {
  profile: '/profile',
  discover: '/discover',
  analysis: '/career-ai#profile-analysis',
  roadmap: '/career-ai#career-roadmap',
  simulation: '/career-ai#career-simulation',
};

async function goToDashboard(target) {
  const { data } = await supabase.auth.getSession();
  if (data.session) {
    window.location.assign(target);
  } else {
    safeSetItem('postLoginRedirect', target);
    window.dispatchEvent(new CustomEvent('open-auth', { detail: 'login' }));
  }
}

const howItWorksCards = [
  {
    title: 'Discover opportunities that fit you.',
    body:
      'Explore internships, programs, fellowships, hackathons, open-source opportunities, events, and more based on your interests, skills, and goals.',
    ui: 'discover',
    cta: 'Open Discover',
  },
  {
    title: 'See what your profile is really saying.',
    body:
      'Understand the strengths your profile communicates, spot what’s missing, and see which improvements could make the biggest difference.',
    ui: 'analysis',
    cta: 'Analyze my profile',
  },
  {
    title: 'Turn your goal into a path forward.',
    body:
      'Get a personalized roadmap for your target role, broken into practical phases with skills to learn, projects to build, and resources worth exploring.',
    ui: 'roadmap',
    cta: 'View my roadmap',
  },
  {
    title: 'Compare your options before you choose.',
    body:
      'Put two career moves side by side and understand their trade-offs based on your goals, current profile, and priorities.',
    ui: 'simulation',
    cta: 'Compare my options',
  },
  {
    title: 'Start with where you are.',
    body:
      'Add your goals, interests, skills, education, projects, and experience once. Your profile becomes the context behind everything OwnMove does for you.',
    ui: 'profile',
    cta: 'Build my profile',
  },
]

function HowItWorksVisual({ type, cta }) {
  if (type === 'discover') {
    return (
      <div className="how-card-device">
        <div className="how-card-inner">
          <div className="how-list-title">Matched for you</div>
          <div className="how-list-row">
            <div className="flex flex-1 items-center justify-between gap-3">
              <span className="font-semibold text-[#1c2565]">AI Engineering Internship</span>
              <span className="inline-flex shrink-0 items-center gap-1.5 text-[0.8rem] font-semibold text-[#1f8f5f]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#1f8f5f]" />
                Strong match
              </span>
            </div>
          </div>
          <div className="how-list-row">
            <div className="flex flex-1 items-center justify-between gap-3">
              <span className="font-semibold text-[#1c2565]">Open Source Program</span>
              <span className="inline-flex shrink-0 items-center gap-1.5 text-[0.8rem] font-semibold text-[#5b46c9]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#5b46c9]" />
                Worth exploring
              </span>
            </div>
          </div>
          <div className="how-list-row">
            <div className="flex flex-1 items-center justify-between gap-3">
              <span className="font-semibold text-[#1c2565]">Student Developer Program</span>
              <span className="inline-flex shrink-0 items-center gap-1.5 text-[0.8rem] font-semibold text-[#b25a1f]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#b25a1f]" />
                Closing soon
              </span>
            </div>
          </div>
          <button type="button" onClick={() => goToDashboard(CTA_TARGETS.discover)} className="how-card-button">{cta}</button>
        </div>
      </div>
    )
  }

  if (type === 'analysis') {
    return (
      <div className="how-card-device">
        <div className="how-card-inner">
          <div className="how-list-title">Profile Analysis</div>
          <div className="how-list-row">
            <div className="flex flex-1 flex-col gap-1">
              <span className="inline-flex items-center gap-1.5 self-start text-[0.76rem] font-semibold uppercase tracking-wide text-[#1f8f5f]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#1f8f5f]" />
                Strong signal
              </span>
              <span className="text-[0.95rem] text-[#25306d]">Hands-on Python experience across projects</span>
            </div>
          </div>
          <div className="how-list-row">
            <div className="flex flex-1 flex-col gap-1">
              <span className="inline-flex items-center gap-1.5 self-start text-[0.76rem] font-semibold uppercase tracking-wide text-[#b25a1f]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#b25a1f]" />
                Missing signal
              </span>
              <span className="text-[0.95rem] text-[#25306d]">Limited work aligned with your target role</span>
            </div>
          </div>
          <div className="how-list-row">
            <div className="flex flex-1 flex-col gap-1">
              <span className="inline-flex items-center gap-1.5 self-start text-[0.76rem] font-semibold uppercase tracking-wide text-[#3b4fc4]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#3b4fc4]" />
                Priority move
              </span>
              <span className="text-[0.95rem] text-[#25306d]">Build one substantial role-relevant project</span>
            </div>
          </div>
          <button type="button" onClick={() => goToDashboard(CTA_TARGETS.analysis)} className="how-card-button">{cta}</button>
        </div>
      </div>
    )
  }

  if (type === 'roadmap') {
    return (
      <div className="how-card-device">
        <div className="how-card-inner">
          <div className="how-plan-header">Your roadmap</div>
          <div className="how-plan-item">
            <span className="how-plan-dot mt-1.5 bg-[#4c5cff]" />
            <span className="flex flex-col gap-0.5">
              <span className="text-[0.76rem] font-semibold uppercase tracking-wide text-[#4c5cff]">01 &mdash; Foundations</span>
              <span>Strengthen LLM &amp; retrieval fundamentals</span>
            </span>
          </div>
          <div className="how-plan-item">
            <span className="how-plan-dot mt-1.5 bg-[#1f8f5f]" />
            <span className="flex flex-col gap-0.5">
              <span className="text-[0.76rem] font-semibold uppercase tracking-wide text-[#1f8f5f]">02 &mdash; Build</span>
              <span>Ship a production-ready RAG project</span>
            </span>
          </div>
          <div className="how-plan-item">
            <span className="how-plan-dot mt-1.5 bg-[#b25a1f]" />
            <span className="flex flex-col gap-0.5">
              <span className="text-[0.76rem] font-semibold uppercase tracking-wide text-[#b25a1f]">03 &mdash; Prove</span>
              <span>Build visible technical work</span>
            </span>
          </div>
          <div className="how-plan-item">
            <span className="how-plan-dot mt-1.5 bg-[#7a5fd9]" />
            <span className="flex flex-col gap-0.5">
              <span className="text-[0.76rem] font-semibold uppercase tracking-wide text-[#7a5fd9]">04 &mdash; Prepare</span>
              <span>Get ready for relevant opportunities</span>
            </span>
          </div>
          <div className="how-progress-bar"><span /></div>
          <button type="button" onClick={() => goToDashboard(CTA_TARGETS.roadmap)} className="how-card-button">{cta}</button>
        </div>
      </div>
    )
  }

  if (type === 'simulation') {
    return (
      <div className="how-card-device">
        <div className="how-card-inner">
          <div className="how-list-title">Compare your next move</div>
          <div className="how-goal-grid">
            <div className="how-goal-box flex flex-col gap-2 bg-[#fdf3ec] text-[#5c4632]">
              <span className="text-[0.95rem] font-bold text-[#202b6d]">Startup AI Internship</span>
              <span className="flex items-center gap-1.5 text-[0.82rem] font-medium text-[#1f8f5f]">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#1f8f5f]" />
                Hands-on experience
              </span>
              <span className="flex items-center gap-1.5 text-[0.82rem] font-medium text-[#1f8f5f]">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#1f8f5f]" />
                Faster ownership
              </span>
              <span className="flex items-center gap-1.5 text-[0.82rem] font-medium text-[#b2451f]">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#b2451f]" />
                Less structured mentorship
              </span>
            </div>
            <div className="how-goal-box flex flex-col gap-2 bg-[#eef8f2] text-[#33604c]">
              <span className="text-[0.95rem] font-bold text-[#202b6d]">Research Internship</span>
              <span className="flex items-center gap-1.5 text-[0.82rem] font-medium text-[#1f8f5f]">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#1f8f5f]" />
                Deeper technical exposure
              </span>
              <span className="flex items-center gap-1.5 text-[0.82rem] font-medium text-[#1f8f5f]">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#1f8f5f]" />
                Research experience
              </span>
              <span className="flex items-center gap-1.5 text-[0.82rem] font-medium text-[#b2451f]">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#b2451f]" />
                Less production exposure
              </span>
            </div>
          </div>
          <button type="button" onClick={() => goToDashboard(CTA_TARGETS.simulation)} className="how-card-button">{cta}</button>
        </div>
      </div>
    )
  }

  return (
    <div className="how-card-device">
      <div className="how-card-inner">
        <div className="how-list-title">Which one sounds like you?</div>
        <p className="-mt-2 mb-3 text-center text-[0.8rem] leading-snug text-[#8188ab]">
          Pick a starting point and we&apos;ll shape your profile around it.
        </p>
        <div className="how-goal-grid">
          <div className="how-goal-box flex flex-col gap-2 bg-[#f59a72] text-white">
            <span className="text-[1rem] font-bold">I&apos;m exploring</span>
            <span>I&apos;m still figuring out which path fits me.</span>
          </div>
          <div className="how-goal-box flex flex-col gap-2 bg-[#67c7a0] text-white">
            <span className="text-[1rem] font-bold">I have a target</span>
            <span>I know where I want to go.</span>
          </div>
        </div>
        <button type="button" onClick={() => goToDashboard(CTA_TARGETS.profile)} className="how-card-button">{cta}</button>
      </div>
    </div>
  )
}

function HowItWorksSection() {
  const sectionRef = useRef(null)
  const cardRefs = useRef([])
  const [progress, setProgress] = useState(0)
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth >= 1024 : true
  )
  // Below `lg` the pin/crossfade animation used to be switched off entirely,
  // because the 2-column desktop layout collapses to one stacked column —
  // a card's text block + device mockup no longer fit inside the fixed
  // 560px stage the animation was built around, so the stage's
  // `overflow-hidden` would clip it. Cards just rendered as a plain long
  // stacked list instead, which is correct but means a LOT of scrolling to
  // get through every card on a phone.
  //
  // Rather than drop the animation below `lg`, `mobileStageHeight` measures
  // the tallest card's REAL rendered height while cards are still in
  // normal, unpositioned document flow, and that measured height becomes
  // the stage size instead of the desktop's hardcoded 560px — so the exact
  // same pin/crossfade mechanic works at any width without clipping
  // anything. It starts out `null` (not yet measured); until it's set,
  // cards render in plain stacked flow, which doubles as both a safe
  // first-paint fallback and the very layout the measurement below reads.
  const [mobileStageHeight, setMobileStageHeight] = useState(null)

  // On mobile the sticky pinned frame (`h-[100svh]`) also has to hold the
  // heading text above the card stage, and phones have far less spare
  // height than desktop to begin with -- so the stage can't just use
  // whatever height the tallest card naturally wants (mobileStageHeight
  // above). These refs/state measure how much room is actually left for
  // the stage once the heading and paddings are accounted for, so the
  // stage never claims more height than the pinned frame can show; see
  // stageHeightPx and the how-neon-card overflow-y fallback below for how
  // this is used.
  const stickyRef = useRef(null)
  const headingRef = useRef(null)
  const pinnedContainerRef = useRef(null)
  const [mobileAvailableHeight, setMobileAvailableHeight] = useState(null)

  useEffect(() => {
    const mql = window.matchMedia('(min-width: 1024px)')
    const updateIsDesktop = () => setIsDesktop(mql.matches)
    updateIsDesktop()
    mql.addEventListener('change', updateIsDesktop)
    return () => mql.removeEventListener('change', updateIsDesktop)
  }, [])

  useEffect(() => {
    const measure = () => {
      // Measured on both breakpoints now (previously desktop skipped this
      // and just assumed a hardcoded 560px stage). That assumption is what
      // was causing the unwanted internal scrollbar: whenever a card's real
      // content came out even a few pixels taller than 560 (a longer title
      // wrapping to 3 lines at some window widths, for example), the stage
      // stayed at 560 while the card's own maxHeight+overflow:auto kicked
      // in to "handle" the difference -- so the card looked basically
      // fully visible but still got a scrollbar and a sliver of clipped
      // content. Sizing the stage to the card's actual measured height
      // removes the mismatch instead of papering over it.
      const heights = cardRefs.current.map((node) => node?.offsetHeight ?? 0)
      const tallest = Math.max(0, ...heights)
      if (tallest > 0) setMobileStageHeight(tallest)

      // How much vertical room the pinned frame has left for the stage,
      // after the heading block and the container's own top/bottom padding
      // -- read via getComputedStyle rather than hardcoded so it stays
      // correct if the padding classes above ever change. This now runs on
      // desktop too: a short (or zoomed-out / small-laptop) browser window
      // can leave less height than the hardcoded 560px stage assumes, and
      // without this the pinned sticky frame's own overflow-hidden was
      // silently clipping the bottom of every card -- e.g. the "Discover
      // opportunities" card's list cut off mid-row with no way to scroll
      // and see the rest.
      const stickyNode = stickyRef.current
      const containerNode = pinnedContainerRef.current
      const headingNode = headingRef.current
      if (stickyNode && containerNode && headingNode) {
        const containerStyle = window.getComputedStyle(containerNode)
        const topPad = parseFloat(containerStyle.paddingTop) || 0
        const bottomPad = parseFloat(containerStyle.paddingBottom) || 0
        // Matches the stage wrapper's marginTop above the stage: mt-12
        // (48px) on desktop/before-pin, or the mobile-only 1.25rem (20px)
        // inline override.
        const stageTopGap = isDesktop ? 48 : 20
        const reserved = topPad + headingNode.offsetHeight + stageTopGap + bottomPad
        // No artificial floor here: a floor bigger than the true leftover
        // space would push (reserved + stage) past the sticky frame's own
        // fixed height again -- the exact clipping bug this is fixing. And
        // there's no internal scroll fallback anymore either -- in a
        // genuinely too-short viewport the card can clip rather than gain
        // a scrollbar, which is the tradeoff asked for here.
        const available = Math.max(stickyNode.clientHeight - reserved, 0)
        setMobileAvailableHeight(available)
      }
    }

    // Measure now, and once more a tick later once icons/mockups inside the
    // cards have finished their own layout (fonts/images can still be
    // reflowing on the very first paint) -- then keep it correct across
    // resizes and orientation changes.
    measure()
    const raf = requestAnimationFrame(measure)
    window.addEventListener('resize', measure)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', measure)
    }
  }, [isDesktop])

  // The pin/crossfade only has a stage to animate within once we know how
  // tall it actually needs to be -- on both breakpoints now, once
  // mobileStageHeight has been measured from the cards' real, unpositioned
  // content height (see the measurement effect above).
  const canAnimate = mobileStageHeight !== null
  // Never let the stage claim more height than the pinned frame actually
  // has once the heading above it is accounted for.
  const stageHeightPx = mobileAvailableHeight !== null
    ? Math.min(mobileStageHeight, mobileAvailableHeight)
    : mobileStageHeight

  // No internal scrolling and no clipping, on any breakpoint: when the
  // viewport doesn't have room for a card at its natural size, shrink the
  // whole card uniformly instead so every card -- text, mockup, and the CTA
  // button -- is always fully visible inside stageHeightPx. Same factor for
  // every card (based on the tallest one, which is what mobileStageHeight
  // already measures) so cards don't visibly change size relative to each
  // other as they crossfade in and out; it's 1 (no-op) whenever the stage
  // already has enough room, which is the common case on a normal window.
  const cardFitScale =
    mobileAvailableHeight !== null && mobileStageHeight > mobileAvailableHeight
      ? mobileAvailableHeight / mobileStageHeight
      : 1

  useEffect(() => {
    if (!canAnimate) return undefined

    let rafId = null

    const computeProgress = () => {
      rafId = null
      const node = sectionRef.current
      if (!node) return

      const rect = node.getBoundingClientRect()
      const maxTravel = Math.max(rect.height - window.innerHeight, 1)
      const traveled = Math.min(Math.max(-rect.top, 0), maxTravel)
      const nextProgress = (traveled / maxTravel) * (howItWorksCards.length - 1)
      setProgress(nextProgress)
    }

    // Coalesce every scroll/resize event that lands within the same frame
    // into a single setState -- scroll events can fire far more often than
    // the display can paint (fast trackpad flicks especially), so updating
    // on every single one was doing multiple redundant re-renders per
    // frame and showing up as stutter rather than a smooth crossfade.
    const scheduleUpdate = () => {
      if (rafId !== null) return
      rafId = requestAnimationFrame(computeProgress)
    }

    computeProgress()
    window.addEventListener('scroll', scheduleUpdate, { passive: true })
    window.addEventListener('resize', scheduleUpdate)

    return () => {
      if (rafId !== null) cancelAnimationFrame(rafId)
      window.removeEventListener('scroll', scheduleUpdate)
      window.removeEventListener('resize', scheduleUpdate)
    }
  }, [canAnimate])

  // --- Mobile: a swipeable carousel instead of the scroll-jacked pin/
  // crossfade above. Desktop's version of this section works well as-is,
  // so none of the above (canAnimate, stageHeightPx, cardFitScale, the
  // scroll-progress effect) is touched -- it simply isn't used once we're
  // rendering the mobile branch below. A duplicate of the first card is
  // appended so swiping forward past the last real card can slide onto
  // that duplicate and then snap back to index 0 with the transition
  // switched off for one frame -- the duplicate looks identical to the
  // real first card, so the snap is invisible and swiping forward again
  // after the last card loops back to "show them starting" like a normal
  // infinite carousel, without an actual reverse-direction slide.
  const mobileExtendedCards = [...howItWorksCards, howItWorksCards[0]]
  const [mobileCardIndex, setMobileCardIndex] = useState(0)
  const [mobileTrackAnimated, setMobileTrackAnimated] = useState(true)
  // How far (in px) the track has been dragged from the current card's
  // resting position -- live-updated on every touchmove so the card visibly
  // follows the finger during the gesture, instead of only reacting once
  // the finger lifts.
  const [mobileDragX, setMobileDragX] = useState(0)
  const mobileTouchStartRef = useRef(null)

  const handleMobileTouchStart = (e) => {
    const touch = e.touches[0]
    mobileTouchStartRef.current = { x: touch.clientX, y: touch.clientY }
    // No transition while actively dragging -- the track should track the
    // finger 1:1 with zero lag, not ease toward it.
    setMobileTrackAnimated(false)
    setMobileDragX(0)
  }

  const handleMobileTouchMove = (e) => {
    const start = mobileTouchStartRef.current
    if (!start) return
    const touch = e.touches[0]
    const deltaX = touch.clientX - start.x
    const deltaY = touch.clientY - start.y
    // Only drag the card once the gesture is clearly horizontal -- if it's
    // more vertical than horizontal this is a normal page scroll, and the
    // card should stay put instead of jittering sideways.
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      setMobileDragX(deltaX)
    }
  }

  const handleMobileTouchEnd = (e) => {
    const start = mobileTouchStartRef.current
    mobileTouchStartRef.current = null

    // Whatever happens next (commit to a new card or snap back), it should
    // animate smoothly from wherever the drag left off.
    setMobileTrackAnimated(true)
    setMobileDragX(0)
    if (!start) return

    const touch = e.changedTouches[0]
    const deltaX = touch.clientX - start.x
    const deltaY = touch.clientY - start.y

    // Require a deliberate, mostly-horizontal drag -- otherwise this was
    // just the user scrolling the page vertically, not swiping the card,
    // and it snaps back to where it was (handled above by resetting
    // mobileDragX with the transition back on).
    const SWIPE_THRESHOLD = 45
    if (Math.abs(deltaX) < SWIPE_THRESHOLD || Math.abs(deltaX) < Math.abs(deltaY)) return

    if (deltaX < 0) {
      // Dragged right-to-left -> next card (loops via the appended
      // duplicate, see handleMobileTrackTransitionEnd below).
      setMobileCardIndex((i) => Math.min(i + 1, mobileExtendedCards.length - 1))
    } else {
      // Dragged left-to-right -> previous card. No backward loop -- this
      // just stops at the first card, since only the forward loop was
      // asked for.
      setMobileCardIndex((i) => Math.max(i - 1, 0))
    }
  }

  const handleMobileTrackTransitionEnd = () => {
    if (mobileCardIndex === howItWorksCards.length) {
      setMobileTrackAnimated(false)
      setMobileCardIndex(0)
    }
  }

  // Turns the transition back on one frame after the instant, invisible
  // snap from the duplicate card back to index 0 -- otherwise every swipe
  // after the first lap would also snap instantly instead of sliding.
  useEffect(() => {
    if (!mobileTrackAnimated) {
      const raf = requestAnimationFrame(() => setMobileTrackAnimated(true))
      return () => cancelAnimationFrame(raf)
    }
    return undefined
  }, [mobileTrackAnimated])

  // All 6 panels (5 cards + the looping duplicate) sit side by side in one
  // flex row, and a flex row's default cross-axis behavior stretches every
  // item to match the TALLEST one -- so a short card (like "Start with
  // where you are") was being stretched to match whichever card is
  // tallest overall ("Profile Analysis", with its 3 signal rows), leaving
  // a big block of empty space below the short card's actual content
  // before the dots. Measuring each panel's own natural height and sizing
  // the viewport to just the CURRENTLY shown card's height removes that
  // gap entirely and keeps it consistent card to card.
  const mobileCardRefs = useRef([])
  const [mobileCardHeights, setMobileCardHeights] = useState([])

  useEffect(() => {
    if (isDesktop) return undefined

    const measureCardHeights = () => {
      const heights = mobileCardRefs.current.map((node) => node?.offsetHeight ?? 0)
      if (heights.some((h) => h > 0)) setMobileCardHeights(heights)
    }

    measureCardHeights()
    const raf = requestAnimationFrame(measureCardHeights)
    window.addEventListener('resize', measureCardHeights)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', measureCardHeights)
    }
  }, [isDesktop])

  return (
    <div className="floating-top-edge floating-top-edge-light relative z-20 -mt-12 rounded-t-[38px] shadow-[0_-24px_60px_rgba(82,95,180,0.08)] sm:-mt-16 sm:rounded-t-[52px]">
      <div className="floating-top-edge-cap pointer-events-none absolute inset-x-0 -top-12 z-10 h-24 sm:-top-14 sm:h-28" />
      <div className="floating-top-edge-glow pointer-events-none absolute inset-x-0 top-0 z-10 h-20 sm:h-24" />
      <div className="floating-top-edge-sheen pointer-events-none absolute left-1/2 top-0 z-10 h-24 w-[68%] -translate-x-1/2 sm:h-28" />

      {isDesktop ? (
      <section
        id="how-it-works"
        ref={sectionRef}
        className="relative bg-[linear-gradient(180deg,#ffffff_0%,#f7f7ff_100%)] text-[#1a215a]"
        style={canAnimate ? { minHeight: `${howItWorksCards.length * 100}vh` } : undefined}
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(127,116,255,0.08),transparent_24%),linear-gradient(180deg,rgba(255,255,255,0.96),rgba(246,247,255,0.98))]" />

        <div
          ref={stickyRef}
          className={`flex items-start ${canAnimate ? 'sticky top-0 h-[100svh] overflow-hidden' : ''}`}
        >
          <div
            ref={pinnedContainerRef}
            className="relative mx-auto w-full max-w-[1220px] px-6 pb-14 pt-20 sm:px-10 sm:pb-16 sm:pt-24 lg:px-12"
            style={canAnimate && !isDesktop ? { paddingTop: '1.5rem', paddingBottom: '1.5rem' } : undefined}
          >
            <div ref={headingRef} className="mx-auto max-w-[760px] text-center">
              <div
                className="text-[clamp(3rem,5.2vw,5.1rem)] font-medium leading-[0.94] tracking-[-0.07em] text-[#1c2565]"
                style={canAnimate && !isDesktop ? { fontSize: 'clamp(2rem,8.5vw,2.6rem)' } : undefined}
              >
                <span className="block">Everything you need to</span>
                <span className="block">make your next move.</span>
              </div>
              <p
                className="mx-auto mt-5 max-w-[640px] text-[clamp(1rem,1.15vw,1.18rem)] leading-8 text-[#8a90b5]"
                style={canAnimate && !isDesktop ? { marginTop: '0.5rem', fontSize: '0.92rem', lineHeight: '1.4rem' } : undefined}
              >
                Discover what fits, understand where you stand, and turn your goals into a clear path forward.
              </p>
            </div>

            <div
              className={
                canAnimate
                  ? 'relative mt-12 block overflow-hidden'
                  : 'relative mt-12 flex flex-col gap-8'
              }
              style={
                canAnimate
                  ? { height: `${stageHeightPx}px`, ...(!isDesktop ? { marginTop: '1.25rem' } : {}) }
                  : undefined
              }
            >
              {howItWorksCards.map((card, index) => {
                const localProgress = progress - index
                let translateY = 112
                let scale = 0.985
                let opacity = 0

                if (localProgress < 0) {
                  translateY = Math.min(-localProgress * 100, 100)
                  scale = 1
                  opacity = 1
                } else {
                  translateY = 0
                  scale = 1
                  opacity = 1
                }

                const animatedStyle = {
                  '--card-z': `${50 + index}`,
                  transform: `translate3d(0, ${translateY}%, 0) scale(${scale})`,
                  opacity,
                  willChange: 'transform, opacity',
                  // Was `index === Math.floor(progress + 0.2)` -- only ever
                  // one card interactive at a time, and it handed
                  // interactivity to the *incoming* card a fifth of the way
                  // through the crossfade, before it had covered more than
                  // ~20% of the stage. That left the outgoing card fully
                  // visible (translateY 0, opacity 1) but pointer-events:
                  // none for the rest of the transition -- on mobile this
                  // is exactly the "Build my profile" bug: scroll far
                  // enough into card 1 (as little as ~80% of one screen
                  // height, easy to overshoot with a normal scroll/flick)
                  // and it goes completely inert -- no internal scroll, no
                  // visible change, because touches on it were no longer
                  // being delivered anywhere.
                  //
                  // A card should stay interactive for its entire actual
                  // on-stage lifetime, which `localProgress` (computed
                  // above) already tracks: it's the resting card while
                  // localProgress is in [0, 1), and it's the incoming card
                  // sliding into place while localProgress is in (-1, 0).
                  // Both can legitimately be interactive at once during the
                  // overlap -- normal stacking (the higher z-index card is
                  // painted on top) already routes a touch/click to
                  // whichever one is actually visible at that point, so
                  // there's no need to artificially restrict it to a single
                  // index.
                  pointerEvents: Math.abs(localProgress) < 1 ? 'auto' : 'none',
                }

                return (
                  <article
                    key={card.title}
                    ref={(node) => {
                      cardRefs.current[index] = node
                    }}
                    // Full `inset-0` (not just `top`): an animated
                    // card has to stretch to fill the whole stage so it
                    // fully covers whatever's stacked beneath it -- a
                    // shorter card left free to size to its own content
                    // would leave the taller one underneath peeking out
                    // past its edges. This only runs once `canAnimate` is
                    // true; the measurement effect above reads each card's
                    // natural height earlier, while `canAnimate` is still
                    // false and cards are plain, unpositioned elements
                    // (className is `undefined` in that branch below).
                    className={canAnimate ? 'absolute inset-0 z-[var(--card-z)]' : undefined}
                    style={canAnimate ? animatedStyle : undefined}
                  >
                    <div
                      className="how-neon-card rounded-[40px] bg-white px-5 py-5 shadow-[0_14px_42px_rgba(82,95,180,0.06)] transition-[transform,opacity,filter] duration-500 ease-out will-change-transform sm:px-12 sm:py-10"
                      // No overflow/scroll here on purpose (mobile or
                      // desktop): cardFitScale above already guarantees the
                      // card's natural height, scaled, fits inside
                      // stageHeightPx, so there's nothing left to clip or
                      // scroll -- the whole card, CTA button included, is
                      // always on screen. `top center` keeps the shrink
                      // anchored to where the card actually starts instead
                      // of shrinking symmetrically from its middle.
                      style={
                        cardFitScale !== 1
                          ? { transform: `scale(${cardFitScale})`, transformOrigin: 'top center' }
                          : undefined
                      }
                    >
                      <div className="grid items-center gap-4 lg:grid-cols-[minmax(320px,0.9fr)_minmax(360px,0.76fr)] lg:gap-10">
                        <div className="flex flex-col justify-start gap-2 lg:gap-6 lg:min-h-[320px]">
                          {/* This title/body pair used to be sized purely
                              for the free-scrolling desktop layout (a huge
                              clamp() headline + leading-8/32px body copy)
                              with no smaller mobile step -- fine when the
                              card could be any height, but below `lg` the
                              card has to fit inside a fixed-height pinned
                              stage (see stageHeightPx above), so that
                              desktop-scaled text alone could already blow
                              past the available room before the device
                              mockup even started. Sized down by default and
                              stepping back up to the original desktop
                              clamp()/leading-8 at `lg` keeps the animation
                              working exactly as before there. */}
                          <h3 className="max-w-[440px] text-[1.7rem] font-medium leading-[1.05] tracking-[-0.03em] text-[#202b6d] lg:text-[clamp(2.2rem,4vw,4rem)] lg:leading-[0.94] lg:tracking-[-0.06em]">
                            {card.title}
                          </h3>
                          <p className="max-w-[420px] text-[0.95rem] leading-[1.55] text-[#8b92b5] lg:text-[clamp(1rem,1.08vw,1.1rem)] lg:leading-8">
                            {card.body}
                          </p>
                        </div>

                        <HowItWorksVisual type={card.ui} cta={card.cta} />
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>
          </div>
        </div>
      </section>
      ) : (
      <section
        id="how-it-works"
        className="relative bg-[linear-gradient(180deg,#ffffff_0%,#f7f7ff_100%)] px-6 pb-16 pt-16 text-[#1a215a] sm:px-10"
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(127,116,255,0.08),transparent_24%),linear-gradient(180deg,rgba(255,255,255,0.96),rgba(246,247,255,0.98))]" />

        <div className="relative mx-auto max-w-[760px] text-center">
          <div className="text-[clamp(2rem,8.5vw,2.6rem)] font-medium leading-[0.94] tracking-[-0.07em] text-[#1c2565]">
            <span className="block">Everything you need to</span>
            <span className="block">make your next move.</span>
          </div>
          <p className="mx-auto mt-2 max-w-[640px] text-[0.92rem] leading-[1.4rem] text-[#8a90b5]">
            Discover what fits, understand where you stand, and turn your goals into a clear path forward.
          </p>
        </div>

        {/* Swipe viewport: overflow-hidden window plus the touch handlers
            that read the gesture on release (handleMobileTouchEnd), not
            live during the drag -- simple threshold-based swipe rather
            than a finger-following drag, which is enough for "swipe right
            to advance, loop after the last card" without needing to fight
            the browser's own vertical page-scroll gesture mid-drag. */}
        <div
          className="relative mt-8 touch-pan-y select-none overflow-hidden"
          onTouchStart={handleMobileTouchStart}
          onTouchMove={handleMobileTouchMove}
          onTouchEnd={handleMobileTouchEnd}
          style={{
            height: mobileCardHeights[mobileCardIndex] || undefined,
            transition: mobileTrackAnimated ? 'height 0.35s ease' : 'none',
          }}
        >
          <div
            className="flex"
            style={{
              width: `${mobileExtendedCards.length * 100}%`,
              transform: `translateX(calc(-${(100 / mobileExtendedCards.length) * mobileCardIndex}% + ${mobileDragX}px))`,
              transition: mobileTrackAnimated ? 'transform 0.45s ease' : 'none',
            }}
            onTransitionEnd={handleMobileTrackTransitionEnd}
          >
            {mobileExtendedCards.map((card, i) => (
              <div
                key={i}
                ref={(node) => {
                  mobileCardRefs.current[i] = node
                }}
                className="shrink-0 px-1"
                style={{ width: `${100 / mobileExtendedCards.length}%` }}
              >
                <div className="how-neon-card rounded-[40px] bg-white px-5 py-5 shadow-[0_14px_42px_rgba(82,95,180,0.06)] sm:px-12 sm:py-10">
                  <div className="flex flex-col gap-4">
                    <div className="flex flex-col gap-2">
                      <h3 className="max-w-[440px] text-[1.7rem] font-medium leading-[1.05] tracking-[-0.03em] text-[#202b6d]">
                        {card.title}
                      </h3>
                      <p className="max-w-[420px] text-[0.95rem] leading-[1.55] text-[#8b92b5]">
                        {card.body}
                      </p>
                    </div>

                    <HowItWorksVisual type={card.ui} cta={card.cta} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative mt-2 flex items-center justify-center gap-2">
          {howItWorksCards.map((_, i) => (
            <button
              key={i}
              type="button"
              aria-label={`Show card ${i + 1}`}
              onClick={() => {
                setMobileTrackAnimated(true)
                setMobileCardIndex(i)
              }}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                i === mobileCardIndex % howItWorksCards.length ? 'w-6 bg-[#4c5cff]' : 'w-1.5 bg-[#d8dcfa]'
              }`}
            />
          ))}
        </div>
      </section>
      )}
    </div>
  )
}

export default HowItWorksSection;
