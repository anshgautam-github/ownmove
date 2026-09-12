import React from 'react';
import founderPhoto from '../../assets/founder.jpeg';

// Renders just the "Why We Built OwnMove" content block — the shared
// background/glow and outer section chrome now live one level up, in
// LandingPage's FounderTrustSection wrapper, so this and StatsBannerSection
// read as two chapters of one continuous section instead of two independent
// ones stacked on top of each other.
function FounderSection() {
  return (
    <div className="relative z-10 mx-auto flex w-full max-w-[760px] flex-col items-center text-center text-[#22242d]">
        <div className="mb-4 text-[0.8rem] font-semibold uppercase tracking-[0.16em] text-[#7b62e8]">
          Why we built OwnMove
        </div>

        <h2 className="founder-heading max-w-[620px] text-center text-[clamp(1.8rem,2.6vw,2.8rem)] font-medium leading-[1.15] tracking-[-0.04em] text-[#202124]">
          Good opportunities shouldn&apos;t depend on knowing where to look.
        </h2>

        <div className="founder-story-card relative mt-10 w-full overflow-hidden rounded-[28px] border border-black/[0.04] bg-[#f2f2ef] px-7 py-9 text-left shadow-[0_20px_48px_rgba(95,102,140,0.1)] sm:px-11 sm:py-11">
          <div className="founder-story-aura pointer-events-none absolute inset-x-[7%] -top-10 z-0 h-28 rounded-full" />
          <div className="founder-story-noise pointer-events-none absolute inset-0 z-0 opacity-[0.42]" />

          <div className="relative z-10 max-w-[560px] text-[1.02rem] leading-[1.75] tracking-[-0.01em] text-[#3c3f47] sm:text-[1.08rem]">
            <p>
              There are incredible programs, internships, fellowships, and career opportunities
              out there. Yet too many students discover them too late — or never discover them at
              all.
            </p>
            <p className="mt-5">
              <strong className="font-semibold text-[#202124]">And finding an opportunity is only half the problem.</strong> Knowing
              whether it fits you, whether you&apos;re ready for it, and what to do next can be
              just as difficult.
            </p>
            <p className="mt-5">
              That&apos;s why we built OwnMove — to help you discover what&apos;s out there,
              understand where you stand, and make better-informed moves toward where you want to
              go.
            </p>
          </div>

          <a
            href="https://www.linkedin.com/in/anshgautam1011/"
            target="_blank"
            rel="noopener noreferrer"
            className="relative z-10 mt-8 flex items-center gap-3 border-t border-black/[0.06] pt-6 transition-opacity hover:opacity-80"
          >
            {/* draggable/onContextMenu don't make the image uncopyable
                (devtools always can), but they block the two casual paths
                — right-click "Save image as" and a drag-out-to-desktop —
                that most people would actually use. */}
            <img
              src={founderPhoto}
              alt="Ansh Gautam"
              draggable={false}
              onContextMenu={(e) => e.preventDefault()}
              className="h-11 w-11 shrink-0 select-none rounded-full object-cover"
            />
            <div>
              <div className="text-[0.95rem] font-semibold tracking-tight text-[#202124]">Ansh Gautam</div>
              <div className="text-[0.82rem] text-[#6b6f7e]">Founder, OwnMove</div>
            </div>
          </a>
        </div>
    </div>
  )
}

export default FounderSection;
