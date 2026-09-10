import { useState } from 'react';
import learningPlatforms, { learningHubCategories } from '../../data/learningPlatforms';

// Same self-contained icon approach as CertificationsCatalog.jsx — AppShell
// doesn't export its `icons` object, so this carries the handful it needs.
const icon = {
  building: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><rect x="4" y="3" width="16" height="18" rx="1.5" /><path d="M9 8h.01M15 8h.01M9 12h.01M15 12h.01M9 16h.01M15 16h.01" /></svg>),
  expand: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M7 17 17 7M9 7h8v8" /></svg>),
};

function PlatformCard({ platform }) {
  return (
    <div className="group relative flex flex-col gap-3 rounded-[20px] border border-white/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.55)_0%,rgba(255,255,255,0.28)_100%)] p-4 pr-9 shadow-[inset_0_1.5px_0_rgba(255,255,255,0.9),0_10px_24px_-18px_rgba(40,50,30,0.35)] backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:border-white/90 hover:bg-[linear-gradient(180deg,rgba(255,255,255,0.8)_0%,rgba(255,255,255,0.5)_100%)]">
      {/* Same "bitten corner" go-to button as the Discover opportunity cards
          and the Certifications catalog cards, for visual consistency. */}
      <div className="pointer-events-none absolute -right-2.5 -top-2.5 z-[5] h-14 w-14 rounded-full bg-[#f5f5f2]" />
      <a
        href={platform.url}
        target="_blank"
        rel="noreferrer"
        title="Go to platform"
        className="absolute -right-0.5 -top-0.5 z-10 flex h-10 w-10 items-center justify-center rounded-full border border-white/70 bg-white/95 text-[#3a3a38] shadow-[0_6px_16px_-6px_rgba(40,50,30,0.35)] transition group-hover:bg-white"
      >
        {icon.expand}
      </a>

      <p className="pr-2 text-[14.5px] font-black leading-tight text-[#1a1a1a]">{platform.name}</p>
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="inline-flex items-center gap-1 rounded-full border border-white/70 bg-white/70 px-2.5 py-1 text-[11px] font-bold text-[#4a4a48]">
          {icon.building}{platform.company}
        </span>
      </div>
      <p className="text-[12px] font-semibold leading-snug text-[#5a5a58]">{platform.description}</p>
    </div>
  );
}

export default function LearningHubCatalog() {
  const [activeCategory, setActiveCategory] = useState('all');
  const platforms = activeCategory === 'all' ? learningPlatforms : learningPlatforms.filter((p) => p.category === activeCategory);

  return (
    <>
      {/* Category filter — the standard header (icon, "Learning Hub" title,
          subheading) is rendered by SidebarContentBody in AppShell.jsx, the
          same shared header every other Discover tab uses, so this only
          owns what's specific to Learning Hub: the filter and the cards. */}
      <nav className="custom-scroll -mx-1 flex shrink-0 gap-2 overflow-x-auto px-1 pb-1">
        {learningHubCategories.map((c) => {
          const isActive = c.key === activeCategory;
          const count = c.key === 'all' ? learningPlatforms.length : learningPlatforms.filter((p) => p.category === c.key).length;
          return (
            <button
              key={c.key}
              type="button"
              onClick={() => setActiveCategory(c.key)}
              className={`flex shrink-0 items-center gap-2 whitespace-nowrap rounded-full border px-4 py-2.5 text-[12.5px] font-bold transition ${
                isActive
                  ? 'border-black bg-[#161616] text-white'
                  : 'border-white/70 bg-white/75 text-[#4a4a48] backdrop-blur-md hover:bg-white/90'
              }`}
            >
              {c.label}
              <span className={`flex h-5 min-w-[20px] items-center justify-center rounded-full px-1 text-[10px] font-black ${isActive ? 'bg-white/20 text-white' : 'bg-[#eeecfa] text-[#7b62e8]'}`}>
                {count}
              </span>
            </button>
          );
        })}
      </nav>

      {/* Cards */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {platforms.map((platform) => (
          <PlatformCard key={platform.name} platform={platform} />
        ))}
      </div>
    </>
  );
}
