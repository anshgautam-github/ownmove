import React, { useEffect, useRef, useState } from 'react';
import { supabase } from '../../services/supabase/client';

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
    localStorage.setItem('postLoginRedirect', target);
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
  const [progress, setProgress] = useState(0)
  // Below the lg breakpoint the 2-column card grid collapses to a single
  // stacked column, and a card's text block + device mockup stacked on top
  // of each other no longer fit inside the fixed 560px stage this
  // scroll-jacked pin animation was built around — the content would get
  // clipped by the stage's overflow-hidden. So the pin/crossfade is
  // desktop-only; below lg, cards render as a plain stacked list that
  // scrolls normally (no clipping, no dependency on the scroll math below).
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth >= 1024 : true
  )

  useEffect(() => {
    const mql = window.matchMedia('(min-width: 1024px)')
    const updateIsDesktop = () => setIsDesktop(mql.matches)
    updateIsDesktop()
    mql.addEventListener('change', updateIsDesktop)
    return () => mql.removeEventListener('change', updateIsDesktop)
  }, [])

  useEffect(() => {
    if (!isDesktop) return undefined

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
  }, [isDesktop])

  return (
    <div className="floating-top-edge floating-top-edge-light relative z-20 -mt-12 rounded-t-[38px] shadow-[0_-24px_60px_rgba(82,95,180,0.08)] sm:-mt-16 sm:rounded-t-[52px]">
      <div className="floating-top-edge-cap pointer-events-none absolute inset-x-0 -top-12 z-10 h-24 sm:-top-14 sm:h-28" />
      <div className="floating-top-edge-glow pointer-events-none absolute inset-x-0 top-0 z-10 h-20 sm:h-24" />
      <div className="floating-top-edge-sheen pointer-events-none absolute left-1/2 top-0 z-10 h-24 w-[68%] -translate-x-1/2 sm:h-28" />

      <section
        id="how-it-works"
        ref={sectionRef}
        className="relative bg-[linear-gradient(180deg,#ffffff_0%,#f7f7ff_100%)] text-[#1a215a]"
        style={isDesktop ? { minHeight: `${howItWorksCards.length * 100}vh` } : undefined}
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(127,116,255,0.08),transparent_24%),linear-gradient(180deg,rgba(255,255,255,0.96),rgba(246,247,255,0.98))]" />

        <div className="flex items-start lg:sticky lg:top-0 lg:h-[100svh] lg:overflow-hidden">
          <div className="relative mx-auto w-full max-w-[1220px] px-6 pb-14 pt-20 sm:px-10 sm:pb-16 sm:pt-24 lg:px-12">
            <div className="mx-auto max-w-[760px] text-center">
              <div className="text-[clamp(3rem,5.2vw,5.1rem)] font-medium leading-[0.94] tracking-[-0.07em] text-[#1c2565]">
                <span className="block">Everything you need to</span>
                <span className="block">make your next move.</span>
              </div>
              <p className="mx-auto mt-5 max-w-[640px] text-[clamp(1rem,1.15vw,1.18rem)] leading-8 text-[#8a90b5]">
                Discover what fits, understand where you stand, and turn your goals into a clear path forward.
              </p>
            </div>

            <div className="relative mt-12 flex flex-col gap-8 lg:block lg:h-[560px] lg:overflow-hidden">
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

                const desktopStyle = {
                  '--card-z': `${50 + index}`,
                  transform: `translate3d(0, ${translateY}%, 0) scale(${scale})`,
                  opacity,
                  pointerEvents: index === Math.floor(progress + 0.2) ? 'auto' : 'none',
                }

                return (
                  <article
                    key={card.title}
                    className="lg:absolute lg:inset-0 lg:z-[var(--card-z)]"
                    style={isDesktop ? desktopStyle : undefined}
                  >
                    <div className="how-neon-card rounded-[40px] bg-white px-6 py-7 shadow-[0_14px_42px_rgba(82,95,180,0.06)] transition-[transform,opacity,filter] duration-500 ease-out will-change-transform sm:px-12 sm:py-10">
                      <div className="grid items-center gap-8 lg:grid-cols-[minmax(320px,0.9fr)_minmax(360px,0.76fr)] lg:gap-10">
                        <div className="flex flex-col justify-start gap-6 lg:min-h-[320px]">
                          <h3 className="max-w-[440px] text-[clamp(2.2rem,4vw,4rem)] font-medium leading-[0.94] tracking-[-0.06em] text-[#202b6d]">
                            {card.title}
                          </h3>
                          <p className="max-w-[420px] text-[clamp(1rem,1.08vw,1.1rem)] leading-8 text-[#8b92b5]">
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
