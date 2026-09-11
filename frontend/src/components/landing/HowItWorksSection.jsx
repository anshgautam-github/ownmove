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
    title: 'Start with where you are.',
    body:
      'Add your goals, interests, skills, education, projects, and experience once. Your profile becomes the context behind everything OwnMove does for you.',
    ui: 'profile',
    cta: 'Build my profile',
  },
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
    if (isDesktop) return undefined

    const measure = () => {
      const heights = cardRefs.current.map((node) => node?.offsetHeight ?? 0)
      const tallest = Math.max(0, ...heights)
      if (tallest > 0) setMobileStageHeight(tallest)

      // How much vertical room the pinned frame has left for the stage,
      // after the heading block and the container's own top/bottom padding
      // -- read via getComputedStyle rather than hardcoded so it stays
      // correct if the padding classes above ever change.
      const stickyNode = stickyRef.current
      const containerNode = pinnedContainerRef.current
      const headingNode = headingRef.current
      if (stickyNode && containerNode && headingNode) {
        const containerStyle = window.getComputedStyle(containerNode)
        const topPad = parseFloat(containerStyle.paddingTop) || 0
        const bottomPad = parseFloat(containerStyle.paddingBottom) || 0
        const stageTopGap = 20 // matches the mobile-only marginTop override on
                                // the stage wrapper below (mt-12/48px only
                                // applies on desktop / before the pin kicks in).
        const reserved = topPad + headingNode.offsetHeight + stageTopGap + bottomPad
        const available = Math.max(stickyNode.clientHeight - reserved, 220)
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
  // tall it should be: always true on desktop (fixed 560px), and on
  // smaller screens only once mobileStageHeight has actually been measured.
  const canAnimate = isDesktop || mobileStageHeight !== null
  // Never let the stage claim more height than the pinned frame actually
  // has once the heading above it is accounted for -- a card taller than
  // this still shows everything (including its CTA button), it just
  // scrolls internally instead of being clipped by the stage's own
  // overflow-hidden (see the how-neon-card style below).
  const stageHeightPx = isDesktop
    ? 560
    : mobileAvailableHeight !== null
      ? Math.min(mobileStageHeight, mobileAvailableHeight)
      : mobileStageHeight

  useEffect(() => {
    if (!canAnimate) return undefined

    const updateProgress = () => {
      const node = sectionRef.current
      if (!node) return

      const rect = node.getBoundingClientRect()
      const maxTravel = Math.max(rect.height - window.innerHeight, 1)
      const traveled = Math.min(Math.max(-rect.top, 0), maxTravel)
      const nextProgress = (traveled / maxTravel) * (howItWorksCards.length - 1)
      setProgress(nextProgress)
    }

    updateProgress()
    window.addEventListener('scroll', updateProgress, { passive: true })
    window.addEventListener('resize', updateProgress)

    return () => {
      window.removeEventListener('scroll', updateProgress)
      window.removeEventListener('resize', updateProgress)
    }
  }, [canAnimate])

  return (
    <div className="floating-top-edge floating-top-edge-light relative z-20 -mt-12 rounded-t-[38px] shadow-[0_-24px_60px_rgba(82,95,180,0.08)] sm:-mt-16 sm:rounded-t-[52px]">
      <div className="floating-top-edge-cap pointer-events-none absolute inset-x-0 -top-12 z-10 h-24 sm:-top-14 sm:h-28" />
      <div className="floating-top-edge-glow pointer-events-none absolute inset-x-0 top-0 z-10 h-20 sm:h-24" />
      <div className="floating-top-edge-sheen pointer-events-none absolute left-1/2 top-0 z-10 h-24 w-[68%] -translate-x-1/2 sm:h-28" />

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
                      style={
                        canAnimate && !isDesktop
                          ? {
                              maxHeight: `${stageHeightPx}px`,
                              overflowY: 'auto',
                              WebkitOverflowScrolling: 'touch',
                              // `contain` (the previous value here) keeps
                              // the overscroll *glow/bounce* from leaking
                              // out, but it also does something easy to
                              // miss: it stops scroll CHAINING to the
                              // window once the card hits its own
                              // top/bottom boundary. On a normal page
                              // that's usually what you want -- but this
                              // card sits inside a scroll-jacked pinned
                              // stack whose crossfade is driven entirely by
                              // window scroll (see `updateProgress` above),
                              // so trapping the gesture here meant that once
                              // you scrolled the card's own content to the
                              // end, the *same* continued drag couldn't
                              // hand off to the window -- you had to lift
                              // your finger and start a new gesture
                              // somewhere off the card just to keep
                              // scrolling the page. `auto` restores normal
                              // chaining: the card scrolls internally first
                              // (revealing the CTA), and once it's exhausted
                              // the rest of the same gesture flows through
                              // to the window, advancing the pin/crossfade
                              // like everywhere else on the page.
                              overscrollBehavior: 'auto',
                              // Without this, a touch-drag that starts on the
                              // card is ambiguous between "scroll my overflow
                              // content" and "advance the pinned scroll-jack",
                              // and mobile browsers tend to resolve that
                              // ambiguity in favor of the outer/window
                              // scroll, so the card's own overflow never
                              // moves and a CTA below the fold stays
                              // unreachable by touch. `pan-y` tells the
                              // browser up front that this element owns
                              // vertical panning gestures itself, so touch
                              // scrolling here reliably scrolls the card --
                              // and with `overscrollBehavior: 'auto'` above,
                              // it still chains through to the window once
                              // the card's own scroll is exhausted.
                              touchAction: 'pan-y',
                            }
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
    </div>
  )
}

export default HowItWorksSection;
