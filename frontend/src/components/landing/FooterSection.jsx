import React from 'react';

// Real single-path brand SVGs (filled with currentColor) for all four —
// letterforms ("in", "X") and a unicode envelope read inconsistently next
// to Discord's actual mark, so every icon here is now the genuine logo
// instead of a mix of text stand-ins and one real icon.
const linkedinIcon = (
  <svg viewBox="0 0 448 512" width="16" height="18" fill="currentColor" aria-hidden="true">
    <path d="M416 32H31.9C14.3 32 0 46.5 0 64.3v383.4C0 465.5 14.3 480 31.9 480H416c17.6 0 32-14.5 32-32.3V64.3c0-17.8-14.4-32.3-32-32.3zM135.4 416H69V202.2h66.5V416zm-33.2-243c-21.3 0-38.5-17.3-38.5-38.5S80.9 96 102.2 96c21.2 0 38.5 17.3 38.5 38.5 0 21.3-17.2 38.5-38.5 38.5zm282.1 243h-66.4V312c0-24.8-.5-56.7-34.5-56.7-34.6 0-39.9 27-39.9 54.9V416h-66.4V202.2h63.7v29.2h.9c8.9-16.8 30.6-34.5 62.9-34.5 67.2 0 79.7 44.3 79.7 101.9V416z" />
  </svg>
);
const mailIcon = (
  <svg viewBox="0 0 512 512" width="18" height="18" fill="currentColor" aria-hidden="true">
    <path d="M48 64C21.5 64 0 85.5 0 112c0 15.1 7.1 29.3 19.2 38.4L236.8 313.6c11.4 8.5 27 8.5 38.4 0L492.8 150.4c12.1-9.1 19.2-23.3 19.2-38.4c0-26.5-21.5-48-48-48H48zM0 176V384c0 35.3 28.7 64 64 64H448c35.3 0 64-28.7 64-64V176L294.4 339.2c-22.8 17.1-54 17.1-76.8 0L0 176z" />
  </svg>
);
const xIcon = (
  <svg viewBox="0 0 512 512" width="16" height="16" fill="currentColor" aria-hidden="true">
    <path d="M389.2 48h70.6L305.6 224.2 487 464H345L233.7 318.6 106.5 464H35.8L200.7 275.5 26.8 48H172.4L272.9 180.9 389.2 48zM364.4 421.8h39.1L151.1 88h-42L364.4 421.8z" />
  </svg>
);
const discordIcon = (
  <svg viewBox="0 0 640 512" width="19" height="15" fill="currentColor" aria-hidden="true">
    <path d="M524.5 69.8a1.5 1.5 0 0 0 -.8-.7A485.1 485.1 0 0 0 404.1 32a1.8 1.8 0 0 0 -1.9 .9 337.5 337.5 0 0 0 -14.9 30.6 447.8 447.8 0 0 0 -134.4 0 309.5 309.5 0 0 0 -15.1-30.6 1.9 1.9 0 0 0 -1.9-.9A483.7 483.7 0 0 0 116.1 69.1a1.7 1.7 0 0 0 -.8 .7C39.1 183.7 18.2 294.7 28.4 404.4a2 2 0 0 0 .8 1.4A487.7 487.7 0 0 0 176 479.9a1.9 1.9 0 0 0 2.1-.7A348.2 348.2 0 0 0 208.1 430.4a1.9 1.9 0 0 0 -1-2.6 321.2 321.2 0 0 1 -45.9-21.9 1.9 1.9 0 0 1 -.2-3.1c3.1-2.3 6.2-4.7 9.1-7.1a1.8 1.8 0 0 1 1.9-.3c96.2 43.9 200.4 43.9 295.5 0a1.8 1.8 0 0 1 1.9 .2c2.9 2.4 6 4.9 9.1 7.2a1.9 1.9 0 0 1 -.2 3.1 301.4 301.4 0 0 1 -45.9 21.8 1.9 1.9 0 0 0 -1 2.6 391.1 391.1 0 0 0 30 48.8 1.9 1.9 0 0 0 2.1 .7A486 486 0 0 0 610.7 405.7a1.9 1.9 0 0 0 .8-1.4C623.7 277.6 590.9 167.5 524.5 69.8zM222.5 337.6c-29 0-52.8-26.6-52.8-59.2S193.1 219.1 222.5 219.1c29.7 0 53.3 26.8 52.8 59.2C275.3 311 251.9 337.6 222.5 337.6zm195.4 0c-29 0-52.8-26.6-52.8-59.2S388.4 219.1 417.9 219.1c29.7 0 53.3 26.8 52.8 59.2C470.7 311 447.5 337.6 417.9 337.6z" />
  </svg>
);

const socialLinks = [
  { label: 'LinkedIn', icon: linkedinIcon },
  { label: 'Gmail', icon: mailIcon },
  { label: 'X', icon: xIcon },
  { label: 'Discord', icon: discordIcon },
]

function FooterSection() {
  return (
    <footer className="footer-stage relative overflow-hidden px-5 pb-8 pt-12 text-white sm:px-8 lg:px-10">
      <div className="footer-bg-noise pointer-events-none absolute inset-0" />

      <div className="relative mx-auto max-w-[1400px] overflow-hidden rounded-[34px] border border-white/10 bg-[linear-gradient(180deg,#05060b_0%,#090a14_30%,#090912_100%)] px-6 py-7 shadow-[0_24px_80px_rgba(7,8,20,0.52)] sm:px-8 sm:py-8 lg:px-10 lg:py-10">
        <div className="footer-inner-glow pointer-events-none absolute inset-0" />
        {/* These five used to sit as siblings of this card, positioned
            against <footer> itself — but this card paints its own opaque
            background on top of them in normal stacking order, so the
            animated beams and glowing orbs were completely hidden behind
            it everywhere except the thin pale margin around the card. That
            silently killed most of the intended depth/richness, which is
            a big part of why the whole thing read as flat. Moved inside
            the card instead (still under the `relative z-10` content
            below), where `mix-blend-mode: screen` actually has the card's
            own dark background to blend against and `overflow-hidden`
            clips them to its rounded corners. */}
        <div className="footer-beam footer-beam-a pointer-events-none absolute left-[12%] top-[-10%] h-[120%] w-[24%]" />
        <div className="footer-beam footer-beam-b pointer-events-none absolute left-[34%] top-[-16%] h-[132%] w-[20%]" />
        <div className="footer-beam footer-beam-c pointer-events-none absolute right-[14%] top-[-14%] h-[128%] w-[24%]" />
        <div className="footer-orb footer-orb-a pointer-events-none absolute left-[16%] bottom-[8%] h-48 w-48 rounded-full" />
        <div className="footer-orb footer-orb-b pointer-events-none absolute right-[18%] bottom-[12%] h-56 w-56 rounded-full" />
        <div className="footer-vignette pointer-events-none absolute inset-0" />

        {/* `min-h-[520px]` only from `lg` up now — below that this used to
            force the same fixed minimum height regardless of how little
            content there was to fill it, stretching the mobile, single-
            column layout with a lot of dead empty space between the
            newsletter card and the wordmark row below it, which read as
            "flat" as much as any color/contrast issue did. */}
        <div className="relative z-10 flex flex-col justify-between gap-6 lg:min-h-[520px] lg:gap-10">
          <div className="grid gap-5 lg:grid-cols-[1.08fr_0.92fr] lg:items-start lg:gap-8">
            {/* This was just an empty spacer div reserving room for the
                newsletter card's height — leaving the entire left half of
                the footer as bare gradient with nothing in it. Filling it
                with the same three lines already used as the real section
                headings in WorkAiFeaturesSection (verbatim, not new copy)
                turns it into a closing recap of the page's actual pitch,
                fading line to line the way the hero's Discover→Understand→
                Decide flow already does. */}
            {/* `min-h-[280px]` only from `lg` up — that height exists so
                this text block vertically centers against the taller
                newsletter card when they sit side by side there. Forcing
                the same height below `lg`, where the two stack instead,
                just left a tall empty gap under three lines of text before
                the card even started — another contributor to the mobile
                layout reading as sparse/flat rather than deliberate. */}
            <div className="flex flex-col justify-center gap-1.5 pr-4 lg:min-h-[280px]">
              <div className="text-[clamp(1.7rem,2.7vw,2.75rem)] font-semibold leading-[1.1] tracking-[-0.04em] text-white/95">
                Discover what fits you.
              </div>
              <div className="text-[clamp(1.7rem,2.7vw,2.75rem)] font-semibold leading-[1.1] tracking-[-0.04em] text-white/58">
                Understand where you stand.
              </div>
              <div className="text-[clamp(1.7rem,2.7vw,2.75rem)] font-semibold leading-[1.1] tracking-[-0.04em] text-white/32">
                Make better career decisions.
              </div>
            </div>

            <div className="footer-newsletter-card ml-auto w-full max-w-[640px] overflow-hidden rounded-[28px] border border-black/6 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(250,246,255,0.97))] px-5 py-5 text-[#19181f] shadow-[0_20px_60px_rgba(15,10,32,0.26)] sm:px-7 sm:py-7">
              {/* This card sits right next to the dark card's own layered
                  glow/beams and, by comparison, was just a flat white
                  rectangle — a quiet corner blob gives it a touch of the
                  same depth without changing its own color scheme. */}
              <div className="pointer-events-none absolute -right-10 -top-14 h-40 w-40 rounded-full bg-[radial-gradient(circle,rgba(154,116,255,0.22)_0%,transparent_70%)] blur-2xl" />

              <div className="relative grid gap-4 sm:grid-cols-[0.9fr_1.1fr] sm:items-start sm:gap-6">
                <div>
                  <span className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-[#f2e9ff] px-3 py-1 text-[10px] font-black uppercase tracking-[0.14em] text-[#7b62e8]">
                    <span className="[&>svg]:h-3 [&>svg]:w-3">{mailIcon}</span>
                    Newsletter
                  </span>
                  <h3 className="text-[clamp(2rem,3.1vw,3.2rem)] font-semibold leading-[0.92] tracking-[-0.06em]">
                    Keeping up
                    <br />
                    with us.
                  </h3>
                </div>

                <p className="max-w-[360px] text-[clamp(0.98rem,1vw,1.08rem)] leading-7 text-[#6e6876] sm:leading-8">
                  Get new opportunities, career tips, and product updates dropped straight into your
                  inbox. No spam, just what actually helps you land the next role.
                </p>
              </div>

              <div className="relative mt-5 flex flex-col gap-3 rounded-[22px] bg-[linear-gradient(90deg,rgba(242,220,255,0.82),rgba(241,224,255,0.72))] p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.72)] sm:mt-8 sm:flex-row sm:items-center">
                <input
                  type="email"
                  placeholder="Your email"
                  className="min-w-0 flex-1 rounded-[18px] bg-transparent px-4 py-3.5 text-[1.25rem] font-medium tracking-[-0.03em] text-[#3b3151] outline-none placeholder:text-[#52456c] sm:py-4"
                />
                {/* Flat white on a pale pink strip was the one genuinely
                    lifeless element in the stacked mobile layout — full
                    width and a colored gradient here gives the actual call
                    to action some presence. sm+ keeps the original flat-
                    white treatment, which already reads fine sitting in a
                    row next to the input instead of stacked under it. */}
                <button
                  type="button"
                  className="footer-submit-button inline-flex w-full items-center justify-center gap-3 rounded-[18px] bg-[linear-gradient(120deg,#7b62e8_0%,#5c63ff_55%,#ff6fae_100%)] px-5 py-3.5 text-white shadow-[0_14px_32px_-10px_rgba(101,89,227,0.55)] transition hover:translate-y-[-1px] sm:w-auto sm:justify-between sm:gap-6 sm:bg-white sm:py-4 sm:text-[#141019] sm:shadow-[0_10px_24px_rgba(32,19,60,0.12)]"
                >
                  <span className="text-[1.9rem] font-light leading-none">+</span>
                  <span className="text-[0.95rem] font-semibold uppercase tracking-[0.14em]">Submit</span>
                </button>
              </div>
            </div>
          </div>

          <div className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-end">
            <div className="flex flex-col gap-8">
              <div className="footer-brand text-[clamp(3.2rem,5.8vw,5.7rem)] font-semibold leading-[0.86] tracking-[-0.07em]">
                Own<span className="text-white/86">Move</span>
              </div>

              <div className="flex flex-wrap items-center gap-5 text-[0.92rem] text-white/58">
                <span>© 2026 OwnMove. All rights reserved</span>
                <span className="hidden h-1 w-1 rounded-full bg-white/26 sm:inline-block" />
                <span>Built for the next chapter of your career</span>
              </div>
            </div>

            {/* justify-end reads fine at lg, where this sits beside the
                wordmark in a 2-column row — but below lg the two blocks
                stack, and a lone right-aligned icon row on its own full-width
                line looks like a leftover from the desktop layout rather
                than a deliberate mobile one. Centering it below lg reads as
                intentional. */}
            <div className="flex items-center justify-center gap-3 lg:justify-end">
              {socialLinks.map((link) => (
                <a
                  key={link.label}
                  href="/"
                  aria-label={link.label}
                  className="footer-social flex h-12 w-12 items-center justify-center rounded-full border border-white/12 bg-white/6 text-white/88 backdrop-blur-md transition hover:translate-y-[-2px]"
                >
                  {link.icon}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default FooterSection;
