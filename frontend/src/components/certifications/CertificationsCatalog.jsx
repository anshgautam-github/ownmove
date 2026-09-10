import { useEffect, useRef, useState } from 'react';
import certificationTracks from '../../data/certificationTracks';

// Self-contained icon set — mirrors the stroke-based style used throughout
// AppShell.jsx, but AppShell doesn't export its `icons` object, so this
// component carries the handful it needs rather than reaching into another
// file's internals.
const icon = {
  tag: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M20.5 12.5 12 21l-9-9V4.5h7.5L20.5 12.5Z" /><circle cx="7.5" cy="7.5" r="1.5" /></svg>),
  clipboard: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5 shrink-0"><rect x="6" y="4.5" width="12" height="16" rx="1.5" /><path d="M9 4.5V3.5A1 1 0 0 1 10 2.5h4a1 1 0 0 1 1 1V4.5M9 10h6M9 13.5h6M9 17h4" /></svg>),
  expand: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M7 17 17 7M9 7h8v8" /></svg>),
  chevron: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="m6 9 6 6 6-6" /></svg>),
  check: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M20 6 9 17l-5-5" /></svg>),
};

// Domain-select dropdown, replacing the old pill-row track switcher. A
// scrollable panel keeps all 17 tracks reachable without the row wrapping
// into a wall of buttons — closes on outside click / Escape / selection.
function TrackDropdown({ tracks, activeKey, onSelect }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const active = tracks.find((t) => t.key === activeKey) || tracks[0];

  useEffect(() => {
    if (!open) return undefined;
    function handlePointerDown(event) {
      if (rootRef.current && !rootRef.current.contains(event.target)) setOpen(false);
    }
    function handleKeyDown(event) {
      if (event.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative mt-5 max-w-full shrink-0 sm:max-w-[420px]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={`flex w-full items-center gap-3 rounded-2xl border-2 bg-[#f6f4fe] px-4 py-3.5 text-left shadow-[0_10px_24px_-18px_rgba(123,98,232,0.45)] transition hover:bg-[#efebfd] ${
          open ? 'border-[#7b62e8]' : 'border-[#ded7f9]'
        }`}
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#7b62e8] text-white">{icon.clipboard}</span>
        <span className="min-w-0 flex-1">
          <span className="block text-[10.5px] font-bold uppercase tracking-wide text-[#7b62e8]">Certification domain</span>
          <span className="block text-[14px] font-black leading-tight text-[#1a1a1a]">{active.title}</span>
        </span>
        <span className={`shrink-0 text-[#7b62e8] transition-transform ${open ? 'rotate-180' : ''}`}>{icon.chevron}</span>
      </button>

      {/* No internal scroll: with only 17 domains, the list comfortably
          fits under the trigger in normal use, so it just expands to show
          everything at once rather than hiding entries behind a scrollbar.
          max-h/overflow stay on as a safety net for very short windows. */}
      {open && (
        <div
          role="listbox"
          className="custom-scroll custom-scroll-mono absolute left-0 right-0 top-[calc(100%+8px)] z-20 max-h-[75vh] overflow-y-auto rounded-2xl border-2 border-[#ded7f9] bg-white p-1.5 shadow-[0_24px_48px_-20px_rgba(123,98,232,0.55)]"
        >
          {tracks.map((t) => {
            const isActive = t.key === activeKey;
            return (
              <button
                key={t.key}
                type="button"
                role="option"
                aria-selected={isActive}
                onClick={() => {
                  onSelect(t.key);
                  setOpen(false);
                }}
                className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-[13px] font-bold transition ${
                  isActive ? 'bg-[#161616] text-white' : 'text-[#3a3a38] hover:bg-[#f5f5f2]'
                }`}
              >
                <span className="min-w-0 flex-1">{t.title}</span>
                {isActive && <span className="shrink-0 text-white">{icon.check}</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// The catalog data has each cert's own official URL but no separate logo
// field — deriving the domain from that URL (rather than hand-maintaining a
// logo per one of the ~86 entries) gets a real vendor mark for free and
// stays correct if a URL is ever corrected.
function domainFromUrl(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return null;
  }
}

// Same favicon-first, initials-on-failure treatment as the Discover
// opportunity cards (OpportunityCard's logo in AppShell.jsx) — matching
// that exact size/shape/fallback so a certification card reads as the same
// kind of card as a Programs/Internships one, not a plainer cousin of it.
function CertificationLogo({ domain, alt }) {
  const [failed, setFailed] = useState(false);

  if (!domain || failed) {
    return (
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[linear-gradient(160deg,#2a2a2a_0%,#121212_100%)] text-sm font-black text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.15),0_6px_14px_-8px_rgba(0,0,0,0.5)]">
        {(alt || '?').charAt(0).toUpperCase()}
      </div>
    );
  }

  return (
    <img
      src={`https://www.google.com/s2/favicons?domain=${domain}&sz=128`}
      alt={alt}
      className="h-11 w-11 shrink-0 rounded-xl border border-white/70 bg-[linear-gradient(160deg,#ffffff_0%,#f3f1fb_100%)] object-contain p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.85),0_6px_14px_-8px_rgba(40,30,80,0.3)]"
      onError={() => setFailed(true)}
    />
  );
}

// Same premium hover treatment as the Discover opportunity cards
// (OpportunityCard in AppShell.jsx) — richer glass gradient, a brand-purple
// glow that fades in on hover, an upgraded logo tile, and the expand button
// filling with the brand gradient on hover — so a certification card reads
// as the same quality of card, not a plainer cousin of it.
function CertificationCard({ cert }) {
  const domain = domainFromUrl(cert.url);



  return (
    <div
      className="group relative flex h-full flex-col gap-3 rounded-[20px] border border-white/60 bg-[linear-gradient(165deg,rgba(255,255,255,0.62)_0%,rgba(250,248,255,0.4)_55%,rgba(255,255,255,0.26)_100%)] p-4 shadow-[inset_0_1.5px_0_rgba(255,255,255,0.9),0_10px_24px_-18px_rgba(40,32,70,0.35)] backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:border-white/90 hover:bg-[linear-gradient(165deg,rgba(255,255,255,0.88)_0%,rgba(250,248,255,0.65)_55%,rgba(255,255,255,0.5)_100%)] hover:shadow-[inset_0_1.5px_0_rgba(255,255,255,0.95),0_24px_44px_-18px_rgba(101,89,227,0.28)]"
    >
      {/* Faint brand-tinted ambient glow, same as the opportunity cards */}
      <div className="pointer-events-none absolute -bottom-6 -left-6 h-24 w-24 rounded-full bg-[radial-gradient(circle,rgba(123,98,232,0.16)_0%,transparent_70%)] opacity-0 blur-xl transition-opacity duration-300 group-hover:opacity-100" />



      {/* Header: logo + name + issuing body — same layout as a Programs card */}
      <div className="relative flex items-start gap-3 pr-2">
        <CertificationLogo domain={domain} alt={cert.body} />
        <div className="min-w-0">
          <p className="text-[14.5px] font-black leading-tight text-[#1a1a1a] transition-colors duration-300 group-hover:text-[#4b3fa8]">{cert.name}</p>
          <p className="truncate text-[12px] font-semibold text-[#9a9a97]">{cert.body}</p>
        </div>
      </div>

      <div className="relative flex items-start gap-1.5 text-[12px] font-semibold text-[#5a5a58]">
        {icon.tag}
        <span className="leading-snug">{cert.examDetails}</span>
      </div>
    </div>
  );
}

export default function CertificationsCatalog({ searchQuery = '', onClearSearch }) {
  const [activeTrack, setActiveTrack] = useState(certificationTracks[0].key);
  const track = certificationTracks.find((t) => t.key === activeTrack) || certificationTracks[0];

  // The header search box (shared across every Discover tab) used to be a
  // no-op here — it filtered the plain opportunity grid, but this catalog
  // renders its own track-based view instead, so typing did nothing. Wired
  // up properly: a non-empty query searches cert name/issuing body/exam
  // details/domain title across ALL 17 tracks at once (not just the
  // currently selected one), since a student searching "AWS" or "security"
  // wants every match, not just whichever domain happens to be open.
  const query = searchQuery.trim().toLowerCase();
  const isSearching = query.length > 0;
  const searchResults = isSearching
    ? certificationTracks.flatMap((t) =>
        t.certs
          .filter((cert) => [cert.name, cert.body, cert.examDetails, t.title].filter(Boolean).join(' ').toLowerCase().includes(query))
          .map((cert) => ({ cert, trackKey: t.key })),
      )
    : [];

  return (
    <div className="custom-scroll custom-scroll-mono mt-3 flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-hidden pb-1 pr-2 pt-1">
      {/* Explainer — the whole reason this exists: make it obvious to a
          student that this catalog is a different, more rigorous thing
          than the free "Certifications" opportunity listings elsewhere in
          Discover. Just the one paragraph — the tab header above already
          carries the heading/icon, and the professional-vs-global split
          this paragraph already explains doesn't need its own two boxes
          repeating it. */}
      <div className="relative shrink-0 overflow-hidden rounded-[22px] border border-white/60 bg-white/55 p-4 backdrop-blur-md">
        <p className="max-w-3xl text-[12.5px] font-medium leading-relaxed text-[#5a5a58]">
          Every credential below is issued directly by the vendor or standards body that owns the technology — Amazon, Google, Microsoft, Cisco, EC-Council, and others — through a proctored exam with a real pass/fail bar.
        </p>
      </div>

      {isSearching ? (
        <>
          <p className="mt-4 shrink-0 text-[12px] font-bold text-[#7a7a76]">
            {searchResults.length} result{searchResults.length === 1 ? '' : 's'} for "{searchQuery}"
          </p>
          {searchResults.length === 0 ? (
            <div className="mt-3 flex flex-1 flex-col items-center justify-center gap-2 rounded-[20px] border border-dashed border-white/70 bg-white/40 px-6 py-10 text-center">
              <span className="rounded-full bg-white/80 px-3 py-1 text-[10px] font-black uppercase tracking-wide text-[#7a7a76]">No matches</span>
              <p className="max-w-sm text-[12.5px] font-semibold text-[#7a7a76]">Nothing matches "{searchQuery}" in Certifications. Try a different keyword.</p>
              {onClearSearch && (
                <button type="button" onClick={onClearSearch} className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-[#161616] px-4 py-2 text-[12px] font-bold text-white transition hover:bg-[#2a2a2a]">
                  Clear search
                </button>
              )}
            </div>
          ) : (
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {searchResults.map(({ cert, trackKey }) => (
                <CertificationCard key={`${trackKey}-${cert.name}`} cert={cert} />
              ))}
            </div>
          )}
        </>
      ) : (
        <>
          {/* Domain select — a single dropdown instead of a row of pills, so
              picking one of the 17 tracks is one deliberate click on a
              compact control rather than scanning/wrapping a wall of
              buttons. */}
          <TrackDropdown tracks={certificationTracks} activeKey={activeTrack} onSelect={setActiveTrack} />

          {/* Cards */}
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {track.certs.map((cert) => (
              <CertificationCard key={cert.name} cert={cert} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
