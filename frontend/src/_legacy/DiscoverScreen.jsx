import React, { useEffect, useState } from 'react';
import { supabase } from '../services/supabase/client';

const icons = {
  logo: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="h-6 w-6">
      <circle cx="12" cy="4.4" r="2.1" /><circle cx="12" cy="19.6" r="2.1" />
      <circle cx="4.4" cy="12" r="2.1" /><circle cx="19.6" cy="12" r="2.1" />
      <circle cx="6.9" cy="6.9" r="1.7" /><circle cx="17.1" cy="17.1" r="1.7" />
      <circle cx="17.1" cy="6.9" r="1.7" /><circle cx="6.9" cy="17.1" r="1.7" />
    </svg>
  ),
  grid: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></svg>),
  analytics: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M4 19V5M4 19h16M8 15l3-4 3 2 4-6" /></svg>),
  pulse: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M3 12h4l2 6 4-14 2 8h6" /></svg>),
  data: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><ellipse cx="12" cy="5.5" rx="8" ry="3" /><path d="M4 5.5v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6M4 11.5v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" /></svg>),
  bell: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M6 10a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 14 6 10Z" /><path d="M10.5 19a1.7 1.7 0 0 0 3 0" /></svg>),
  back: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>),
  search: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m20 20-4.3-4.3" /></svg>),
  arrow: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M7 17 17 7M9 7h8v8" /></svg>),
  star: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><path d="M12 3.5l2.6 5.6 6.1.6-4.6 4.1 1.3 6-5.4-3.1-5.4 3.1 1.3-6-4.6-4.1 6.1-.6L12 3.5Z" /></svg>),
  briefcase: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><rect x="3" y="7.5" width="18" height="12" rx="2" /><path d="M8 7.5V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v1.5M3 12.5h18" /></svg>),
  trophy: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><path d="M7 4h10v5a5 5 0 0 1-10 0V4Z" /><path d="M7 5H4v1.5A3.5 3.5 0 0 0 7 10M17 5h3v1.5A3.5 3.5 0 0 1 17 10M9.5 19.5h5M12 14v5.5" /></svg>),
  award: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><circle cx="12" cy="9" r="5.2" /><path d="M8.5 13.5 7 20l5-2.3 5 2.3-1.5-6.5" /></svg>),
  cap: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><path d="M12 4.5 2.5 9 12 13.5 21.5 9 12 4.5Z" /><path d="M6 11v4.5c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5V11" /></svg>),
  flask: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><path d="M9.5 3.5h5M10 3.5v6.3L4.8 18a1.7 1.7 0 0 0 1.5 2.5h11.4a1.7 1.7 0 0 0 1.5-2.5L14 9.8V3.5" /><path d="M7.5 15.5h9" /></svg>),
  github: (<svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5"><path d="M12 2C6.48 2 2 6.58 2 12.26c0 4.54 2.87 8.4 6.84 9.77.5.1.68-.22.68-.48 0-.24-.01-1.04-.01-1.88-2.78.62-3.37-1.22-3.37-1.22-.46-1.2-1.13-1.52-1.13-1.52-.92-.64.07-.63.07-.63 1.02.07 1.56 1.07 1.56 1.07.9 1.57 2.37 1.12 2.95.86.09-.67.35-1.12.63-1.38-2.22-.26-4.56-1.14-4.56-5.06 0-1.12.39-2.04 1.03-2.76-.1-.26-.45-1.31.1-2.72 0 0 .84-.27 2.75 1.05A9.12 9.12 0 0 1 12 7.58c.85 0 1.72.12 2.53.35 1.9-1.32 2.74-1.05 2.74-1.05.56 1.41.21 2.46.1 2.72.64.72 1.03 1.64 1.03 2.76 0 3.93-2.35 4.8-4.58 5.05.36.32.68.94.68 1.9 0 1.38-.01 2.49-.01 2.83 0 .26.18.59.69.48A10.26 10.26 0 0 0 22 12.26C22 6.58 17.52 2 12 2Z" /></svg>),
  ribbon: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><circle cx="12" cy="8" r="5" /><path d="m8.5 12.5-1.8 8 5.3-2.7 5.3 2.7-1.8-8" /></svg>),
  target: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1.5" /></svg>),
  users2: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><circle cx="9" cy="8.5" r="3.2" /><circle cx="17" cy="9.5" r="2.6" /><path d="M3.5 19c1.2-3.2 3.4-4.7 5.5-4.7s4.3 1.5 5.5 4.7M15 14.9c2 .2 3.7 1.6 4.6 4.1" /></svg>),
  calendar: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><rect x="3" y="4.5" width="18" height="16" rx="2.5" /><path d="M3 9h18M8 3v3M16 3v3" /></svg>),
  layers: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 13 9 5 9-5" /></svg>),
};

function RoundBtn({ icon, dark, onClick, href, title }) {
  const cls = `flex h-9 w-9 items-center justify-center rounded-full border transition ${dark ? 'border-white/10 bg-[#161616] text-white hover:bg-[#2a2a2a]' : 'border-white/70 bg-white/55 text-[#3a3a38] backdrop-blur-md hover:bg-white/80 hover:text-[#161616]'}`;
  if (href) return <a href={href} title={title} className={cls}>{icon}</a>;
  return <button type="button" onClick={onClick} title={title} className={cls}>{icon}</button>;
}

function StatusScreen({ children }) {
  return <main className="flex min-h-screen items-center justify-center bg-[#e9e9e7] text-[#1a1a1a]"><div className="text-center">{children}</div></main>;
}

const categories = [
  { key: 'for-you', label: 'For You', icon: icons.star, desc: 'Matches curated from your skills, interests, and goals.', featured: true },
  { key: 'internships', label: 'Internships', icon: icons.briefcase, desc: 'Roles at startups and established companies.' },
  { key: 'hackathons', label: 'Hackathons', icon: icons.trophy, desc: 'Build fast, ship prototypes, win prizes.' },
  { key: 'fellowships', label: 'Fellowships', icon: icons.award, desc: 'Funded programs for focused, guided growth.' },
  { key: 'scholarships', label: 'Scholarships', icon: icons.cap, desc: 'Financial support for your education.' },
  { key: 'research', label: 'Research', icon: icons.flask, desc: 'Labs and projects looking for collaborators.' },
  { key: 'open-source', label: 'Open Source', icon: icons.github, desc: 'Contribute to projects that matter.' },
  { key: 'certifications', label: 'Certifications', icon: icons.ribbon, desc: 'Credentials that strengthen your profile.' },
  { key: 'challenges', label: 'Challenges', icon: icons.target, desc: 'Competitions that test and sharpen your skills.' },
  { key: 'communities', label: 'Communities', icon: icons.users2, desc: 'Groups and networks to grow alongside.' },
  { key: 'events', label: 'Events', icon: icons.calendar, desc: 'Conferences, meetups, and webinars.' },
  { key: 'all', label: 'All Opportunities', icon: icons.layers, desc: 'Browse everything in one place.' },
];

function DiscoverScreen() {
  const [status, setStatus] = useState('loading');
  const [user, setUser] = useState(null);
  const [active, setActive] = useState('for-you');

  useEffect(() => {
    let active2 = true;
    (async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const currentUser = session?.user ?? null;
      if (!active2) return;
      if (!currentUser) { setStatus('signed-out'); return; }
      setUser(currentUser);
      setStatus('ready');
    })();
    return () => { active2 = false; };
  }, []);

  if (status === 'loading') return <StatusScreen><p className="text-xs font-bold uppercase tracking-[0.2em] text-[#9a9a97]">Loading Discover…</p></StatusScreen>;
  if (status === 'signed-out') {
    return (
      <StatusScreen>
        <p className="text-lg font-semibold">You need to sign in to view Discover.</p>
        <a href="/" className="mt-5 inline-block rounded-full bg-[#161616] px-5 py-2.5 text-sm font-bold text-white transition hover:bg-[#2a2a2a]">Go to login</a>
      </StatusScreen>
    );
  }

  const fullName = user?.user_metadata?.full_name || user?.user_metadata?.name || 'Builder';
  const avatarUrl = user?.user_metadata?.avatar_url || user?.user_metadata?.picture;

  const navTabs = [
    { label: 'Dashboard', icon: icons.grid, href: '/dashboard' },
    { label: 'Discover', icon: icons.analytics, active: true, href: '/discover' },
    { label: 'Career AI', icon: icons.pulse, href: '/dashboard#momentum-card' },
    { label: 'Profile', icon: icons.data, href: '/onboarding' },
  ];

  const activeCategory = categories.find((c) => c.key === active) || categories[0];

  return (
    <div className="relative h-screen overflow-hidden bg-[#eaeae7] text-[#1a1a1a]">
      {/* ambient wash so the glass has color to refract */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-24 -top-24 h-[380px] w-[380px] rounded-full bg-[#c8f24a] opacity-25 blur-[120px]" />
        <div className="absolute right-[-80px] top-[10%] h-[340px] w-[340px] rounded-full bg-[#bcd6ff] opacity-30 blur-[130px]" />
        <div className="absolute bottom-[-120px] left-1/3 h-[420px] w-[420px] rounded-full bg-[#ffe2b0] opacity-25 blur-[130px]" />
        <div className="absolute bottom-0 right-1/4 h-[300px] w-[300px] rounded-full bg-[#d6f7a8] opacity-20 blur-[120px]" />
      </div>

      <div className="relative z-10 mx-auto flex h-full max-w-[1440px] flex-col px-6 py-5 sm:px-10 sm:py-6">
        {/* Top nav */}
        <header className="flex shrink-0 items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <a href="/" className="text-[#1a1a1a]">{icons.logo}</a>
            <nav className="hidden items-center gap-1.5 md:flex">
              {navTabs.map((t) => (
                <a key={t.label} href={t.href} className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12.5px] font-semibold transition ${t.active ? 'bg-[#161616] text-white' : 'border border-white/70 bg-white/55 text-[#4a4a48] backdrop-blur-md hover:bg-white/80 hover:text-[#161616]'}`}>
                  {t.icon}{t.label}
                </a>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-2.5">
            <RoundBtn icon={icons.bell} />
            {avatarUrl ? <img src={avatarUrl} alt={fullName} className="h-9 w-9 rounded-full object-cover ring-2 ring-white" /> : <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#161616] text-xs font-black text-white">{fullName.charAt(0).toUpperCase()}</div>}
          </div>
        </header>

        {/* Title row */}
        <div className="mt-5 flex shrink-0 flex-wrap items-center justify-between gap-y-2.5 gap-x-3">
          <div className="flex items-center gap-3">
            <a href="/dashboard" className="flex h-9 w-9 items-center justify-center rounded-full border border-white/70 bg-white/55 text-[#3a3a38] backdrop-blur-md transition hover:bg-white/80 hover:text-[#161616]">{icons.back}</a>
            <div>
              <p className="text-[11px] font-semibold text-[#9a9a97]">Discover · Opportunities</p>
              <h1 className="text-[22px] font-black leading-none tracking-tight sm:text-[25px]">Find your next move</h1>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <RoundBtn icon={icons.search} />
            <span className="rounded-full border border-white/70 bg-white/55 px-3 py-1.5 text-[12px] font-semibold text-[#4a4a48] backdrop-blur-md">{categories.length} categories</span>
          </div>
        </div>

        {/* Body: sidebar + content */}
        <div className="mt-5 flex min-h-0 flex-1 gap-5">
          {/* Sidebar */}
          <div className="flex w-[228px] shrink-0 flex-col overflow-hidden rounded-[26px] border border-white/70 bg-white/45 p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.9),inset_0_0_0_1px_rgba(255,255,255,0.25),0_20px_44px_-24px_rgba(40,50,30,0.35)] backdrop-blur-2xl">
            <p className="px-2.5 pb-2 pt-1 text-[10.5px] font-bold uppercase tracking-[0.12em] text-[#9a9a97]">Categories</p>
            <nav className="flex flex-1 flex-col gap-1 overflow-y-auto pr-0.5">
              {categories.map((c) => {
                const isActive = active === c.key;
                return (
                  <button
                    key={c.key}
                    type="button"
                    onClick={() => setActive(c.key)}
                    className={`flex items-center gap-2.5 rounded-2xl px-2.5 py-2.5 text-left transition ${
                      isActive ? 'bg-[#161616] text-white shadow-[0_10px_22px_-10px_rgba(0,0,0,0.5)]' : 'text-[#4a4a48] hover:bg-white/70'
                    }`}
                  >
                    <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${isActive ? 'bg-white/15 text-white' : 'bg-white/70 text-[#1a1a1a] backdrop-blur-md'}`}>{c.icon}</span>
                    <span className="min-w-0 flex-1 truncate text-[12.5px] font-bold">{c.label}</span>
                    {c.featured && <span className="shrink-0 rounded-full bg-[#c8f24a] px-1.5 py-0.5 text-[8px] font-black uppercase tracking-wide text-[#1a1a1a]">New</span>}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Content */}
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[26px] border border-white/70 bg-white/45 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.9),inset_0_0_0_1px_rgba(255,255,255,0.25),0_20px_44px_-24px_rgba(40,50,30,0.35)] backdrop-blur-2xl">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#161616] text-white">{activeCategory.icon}</span>
                <div>
                  <p className="text-[16px] font-black tracking-tight">{activeCategory.label}</p>
                  <p className="text-[11.5px] font-medium text-[#7a7a76]">{activeCategory.desc}</p>
                </div>
              </div>
              {activeCategory.featured && <span className="shrink-0 rounded-full bg-[#c8f24a] px-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-[#1a1a1a]">Recommended</span>}
            </div>

            <div className="mt-5 flex flex-1 flex-col items-center justify-center gap-2 rounded-[20px] border border-dashed border-white/70 bg-white/40 px-6 py-10 text-center">
              <span className="rounded-full bg-[#c8f24a] px-3 py-1 text-[10px] font-black uppercase tracking-wide text-[#1a1a1a]">Coming soon</span>
              <p className="max-w-sm text-[12.5px] font-semibold text-[#7a7a76]">We're building out live listings for {activeCategory.label.toLowerCase()}. Check back soon, or complete your profile so we can match you the moment they land.</p>
              <a href="/onboarding" className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-[#161616] px-4 py-2 text-[12px] font-bold text-white transition hover:bg-[#2a2a2a]">Complete your profile</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DiscoverScreen;
