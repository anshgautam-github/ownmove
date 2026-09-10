import React, { useEffect, useRef, useState } from 'react';
import HeroSection from '../components/landing/HeroSection';
import WorkAiSection from '../components/landing/WorkAiSection';
import IntelligenceSection from '../components/landing/IntelligenceSection';
import DemoSection from '../components/landing/DemoSection';
import HowItWorksSection from '../components/landing/HowItWorksSection';
import FounderSection from '../components/landing/FounderSection';
import StatsBannerSection from '../components/landing/StatsBannerSection';
import TestimonialSection from '../components/landing/TestimonialSection';
import FaqSection from '../components/landing/FaqSection';
import WorkAiFeaturesSection from '../components/landing/WorkAiFeaturesSection';
import FooterSection from '../components/landing/FooterSection';

/**
 * Scroll-driven crossfade between the Hero and the Work AI section.
 * Kept here (rather than in components/landing) because it composes two
 * sections together — it is a page-level layout concern, not a section.
 */
function HeroWorkTransition() {
  const sectionRef = useRef(null);
  const [progress, setProgress] = useState(0);
  // Below lg, WorkAiSection's own two-column layout collapses to one stacked
  // column (visual block above the text block), which is taller than a
  // single mobile screen. That content was sitting inside a fixed h-[100svh]
  // overflow-hidden pin — fine at desktop widths where everything fits in
  // one viewport, but on mobile whatever didn't fit was simply invisible,
  // clipped by the pin's own overflow-hidden. So the scroll-jacked pin +
  // crossfade is desktop-only; below lg, Hero and WorkAi just render in
  // normal stacked document flow with nothing clipped.
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth >= 1024 : true
  );

  useEffect(() => {
    const mql = window.matchMedia('(min-width: 1024px)');
    const updateIsDesktop = () => setIsDesktop(mql.matches);
    updateIsDesktop();
    mql.addEventListener('change', updateIsDesktop);
    return () => mql.removeEventListener('change', updateIsDesktop);
  }, []);

  useEffect(() => {
    if (!isDesktop) return undefined;

    const updateProgress = () => {
      const node = sectionRef.current;
      if (!node) return;

      const rect = node.getBoundingClientRect();
      const maxTravel = Math.max(rect.height - window.innerHeight, 1);
      const traveled = Math.min(Math.max(-rect.top, 0), maxTravel);
      setProgress(traveled / maxTravel);
    };

    updateProgress();
    window.addEventListener('scroll', updateProgress, { passive: true });
    window.addEventListener('resize', updateProgress);

    return () => {
      window.removeEventListener('scroll', updateProgress);
      window.removeEventListener('resize', updateProgress);
    };
  }, [isDesktop]);

  const eased = 1 - Math.pow(1 - progress, 3);
  const revealStart = 0.04;
  const normalized = progress <= revealStart ? 0 : (progress - revealStart) / (1 - revealStart);
  const overlayPhase = Math.min(normalized / 0.55, 1);
  const takeoverPhase = normalized <= 0.55 ? 0 : (normalized - 0.55) / 0.45;
  const overlayEased = 1 - Math.pow(1 - overlayPhase, 3);
  const takeoverEased = 1 - Math.pow(1 - takeoverPhase, 3);

  const heroTranslate = -takeoverEased * 18;
  const heroScale = 1 - eased * 0.035;
  const heroOpacity = 1 - eased * 0.12;

  const workTranslate = overlayEased * 50 + takeoverEased * 50;
  const workScale = 0.96 + overlayEased * 0.02 + takeoverEased * 0.02;
  const workOpacity = progress < revealStart ? 0 : 1;

  return (
    <section
      ref={sectionRef}
      className="relative"
      style={isDesktop ? { minHeight: '220vh' } : undefined}
    >
      <div className={isDesktop ? 'sticky top-0 h-[100svh] overflow-hidden' : ''}>
        <div
          className={isDesktop ? 'absolute inset-0 will-change-transform' : ''}
          style={
            isDesktop
              ? { transform: `translate3d(0, ${heroTranslate}%, 0) scale(${heroScale})`, opacity: heroOpacity }
              : undefined
          }
        >
          <HeroSection />
        </div>

        <div
          className={
            isDesktop
              ? 'absolute inset-x-0 top-full z-20 overflow-hidden rounded-t-[42px] shadow-[0_-28px_80px_rgba(12,14,30,0.22)] will-change-transform sm:rounded-t-[56px]'
              : 'overflow-hidden rounded-t-[42px] shadow-[0_-28px_80px_rgba(12,14,30,0.22)] sm:rounded-t-[56px]'
          }
          style={
            isDesktop
              ? { transform: `translate3d(0, -${workTranslate}%, 0) scale(${workScale})`, opacity: workOpacity }
              : undefined
          }
        >
          <WorkAiSection />
        </div>
      </div>
    </section>
  );
}

/**
 * Scroll-driven handoff from the testimonial wall into the FAQ section.
 */
function TestimonialFaqTransition() {
  const sectionRef = useRef(null);
  const [progress, setProgress] = useState(0);
  // Same issue as HeroWorkTransition below: FaqSection's stacked mobile
  // layout (category list, then the full FAQ list, then the support card)
  // is taller than one screen, and it was sitting inside a fixed h-[100svh]
  // overflow-hidden pin built for the desktop crossfade. Below lg, drop the
  // pin entirely and let Testimonial + Faq render as two normal stacked
  // sections — nothing gets clipped, and the "FAQ" nav anchor still lands
  // on real, normally-scrollable content.
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth >= 1024 : true
  );

  useEffect(() => {
    const mql = window.matchMedia('(min-width: 1024px)');
    const updateIsDesktop = () => setIsDesktop(mql.matches);
    updateIsDesktop();
    mql.addEventListener('change', updateIsDesktop);
    return () => mql.removeEventListener('change', updateIsDesktop);
  }, []);

  useEffect(() => {
    if (!isDesktop) return undefined;

    const updateProgress = () => {
      const node = sectionRef.current;
      if (!node) return;

      const rect = node.getBoundingClientRect();
      const maxTravel = Math.max(rect.height - window.innerHeight, 1);
      const traveled = Math.min(Math.max(-rect.top, 0), maxTravel);
      setProgress(traveled / maxTravel);
    };

    updateProgress();
    window.addEventListener('scroll', updateProgress, { passive: true });
    window.addEventListener('resize', updateProgress);

    return () => {
      window.removeEventListener('scroll', updateProgress);
      window.removeEventListener('resize', updateProgress);
    };
  }, [isDesktop]);

  const transitionPhase = Math.min(progress / 0.84, 1);
  const eased = 1 - Math.pow(1 - transitionPhase, 3);
  const softStart = transitionPhase < 0.12 ? transitionPhase / 0.12 : 1;
  const soften = softStart * softStart * (3 - 2 * softStart);
  const blend = eased * soften;

  const testimonialTranslate = -blend * 102;
  const testimonialScale = 1 - blend * 0.06;
  const faqTranslate = 20 - blend * 20;
  const faqScale = 0.986 + blend * 0.014;
  const faqOpacity = 0.72 + blend * 0.28;

  return (
    // FaqSection itself never has its own scroll position — it's crossfaded
    // in via transform/opacity inside this section's scroll-jack, so the
    // header's "FAQ" link needs an id up here (the one element with real
    // document height) rather than on FaqSection's own <section>, which
    // wouldn't be scrollable to on its own.
    <section
      id="faq"
      ref={sectionRef}
      className="relative"
      style={isDesktop ? { minHeight: '320vh' } : undefined}
    >
      <div
        className={
          isDesktop
            ? 'sticky top-0 h-[100svh] overflow-hidden bg-[linear-gradient(180deg,#0b0c16_0%,#fdfaf6_72%,#fffdf9_100%)]'
            : 'bg-[linear-gradient(180deg,#0b0c16_0%,#fdfaf6_72%,#fffdf9_100%)]'
        }
      >
        {/* Reordered so mobile's natural stacked flow reads Testimonials
            then FAQ (matching this section's place in the page); the
            desktop crossfade is unaffected since Testimonial's explicit z-20
            still keeps it on top of Faq regardless of DOM order. */}
        <div
          className={isDesktop ? 'absolute inset-0 z-20 will-change-transform' : ''}
          style={
            isDesktop
              ? { transform: `translate3d(0, ${testimonialTranslate}%, 0) scale(${testimonialScale})`, opacity: 1, filter: 'none' }
              : undefined
          }
        >
          <TestimonialSection />
        </div>

        <div
          className={isDesktop ? 'absolute inset-0 will-change-transform' : ''}
          style={
            isDesktop
              ? { transform: `translate3d(0, ${faqTranslate}%, 0) scale(${faqScale})`, opacity: faqOpacity }
              : undefined
          }
        >
          <FaqSection />
        </div>
      </div>
    </section>
  );
}

/**
 * Founder ("Why We Built OwnMove") and Trust/Social Proof used to be two
 * independently-styled <section>s (each with its own background, padding,
 * and — in Founder's case — a hard border-top/border-bottom) stacked back
 * to back, which read as two unrelated chunks of page rather than one
 * chapter. This wrapper owns the shared background/glow treatment and the
 * single block of vertical rhythm between the two parts; FounderSection and
 * StatsBannerSection now render just their content.
 */
function FounderTrustSection() {
  return (
    <section id="why-ownmove" className="founder-stage relative overflow-hidden bg-[#ffffff] px-6 pb-20 pt-24 text-[#22242d] sm:px-10 sm:pb-24 sm:pt-28">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(120,140,255,0.03),transparent_35%),linear-gradient(180deg,#ffffff_0%,#fbfbfd_55%,#f3f6ff_100%)]" />
      <div className="founder-stage-glow pointer-events-none absolute left-1/2 top-[12%] h-[420px] w-[min(72vw,920px)] -translate-x-1/2 rounded-full" />

      <div className="relative z-10 mx-auto flex w-full max-w-[1160px] flex-col items-center">
        <FounderSection />
        <div className="mt-20 flex w-full flex-col items-center sm:mt-24">
          <StatsBannerSection />
        </div>
      </div>
    </section>
  );
}

/**
 * The public marketing site (route: "/").
 */
function LandingPage() {
  return (
    <main className="bg-[#06070f]">
      <HeroWorkTransition />
      <DemoSection />
      <HowItWorksSection />
      <IntelligenceSection />
      <FounderTrustSection />
      <TestimonialFaqTransition />
      <WorkAiFeaturesSection />
      <FooterSection />
    </main>
  );
}

export default LandingPage;
