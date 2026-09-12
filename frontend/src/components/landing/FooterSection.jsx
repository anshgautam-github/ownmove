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
// Real Gmail wordmark colors (not currentColor like LinkedIn) so it reads
// as the actual Gmail icon against the dark circle background. `mailto:`
// links don't need `external` — there's no new tab to open, just the
// user's default mail client.
const gmailIcon = (
  <svg viewBox="0 0 48 48" width="20" height="20" aria-hidden="true">
    <path fill="#4caf50" d="M45,16.2l-5,2.75l-5,4.75L35,40h7c1.657,0,3-1.343,3-3V16.2z"></path>
    <path fill="#1e88e5" d="M3,16.2l3.614,1.71L13,23.7V40H6c-1.657,0-3-1.343-3-3V16.2z"></path>
    <polygon fill="#e53935" points="35,11.2 24,19.45 13,11.2 12,17 13,23.7 24,31.95 35,23.7 36,17"></polygon>
    <path fill="#c62828" d="M3,12.298V16.2l10,7.5V11.2L9.876,8.859C9.132,8.301,8.228,8,7.298,8h0C4.924,8,3,9.924,3,12.298z"></path>
    <path fill="#fbc02d" d="M45,12.298V16.2l-10,7.5V11.2l3.124-2.341C38.868,8.301,39.772,8,40.702,8h0 C43.076,8,45,9.924,45,12.298z"></path>
  </svg>
);
// X and Discord dropped — LinkedIn and Gmail are the real presence for
// now. Each link carries its own `href` (and `external` for the ones that
// leave the site) rather than every icon pointing at the same placeholder
// "/" — LinkedIn goes to the real company page, Gmail opens a new email.
const socialLinks = [
  { label: 'LinkedIn', icon: linkedinIcon, href: 'https://www.linkedin.com/company/ownmove/', external: true },
  { label: 'Gmail', icon: gmailIcon, href: 'mailto:ownmovee@gmail.com' },
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

            {/* Mobile-only ask: this white "Why OwnMove" card stays for
                desktop (paired side-by-side with the recap text above at
                `lg`) but is dropped below `lg` — on a phone it was just a
                second, redundant restatement of the page's pitch stacked
                under the same three recap lines, right before the page
                ends. */}
            <div className="footer-newsletter-card ml-auto hidden w-full max-w-[640px] overflow-hidden rounded-[28px] border border-black/6 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(250,246,255,0.97))] px-5 py-5 text-[#19181f] shadow-[0_20px_60px_rgba(15,10,32,0.26)] sm:px-7 sm:py-7 lg:block">
              {/* This card sits right next to the dark card's own layered
                  glow/beams and, by comparison, was just a flat white
                  rectangle — a quiet corner blob gives it a touch of the
                  same depth without changing its own color scheme. */}
              <div className="pointer-events-none absolute -right-10 -top-14 h-40 w-40 rounded-full bg-[radial-gradient(circle,rgba(154,116,255,0.22)_0%,transparent_70%)] blur-2xl" />

              <div className="relative grid gap-4 sm:grid-cols-[0.9fr_1.1fr] sm:items-start sm:gap-6">
                <div>
                  <span className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-[#f2e9ff] px-3 py-1 text-[10px] font-black uppercase tracking-[0.14em] text-[#7b62e8]">
                    Why OwnMove
                  </span>
                  <h3 className="text-[clamp(2rem,3.1vw,3.2rem)] font-semibold leading-[0.92] tracking-[-0.06em]">
                    Own your
                    <br />
                    next move.
                  </h3>
                </div>

                <p className="max-w-[360px] text-[clamp(0.98rem,1vw,1.08rem)] leading-7 text-[#6e6876] sm:leading-8">
                  From your first internship to your next big decision, OwnMove brings real
                  opportunities and an AI Coach that actually knows your profile into one place —
                  not just another job board.
                </p>
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
                  href={link.href}
                  {...(link.external ? { target: '_blank', rel: 'noreferrer' } : {})}
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
