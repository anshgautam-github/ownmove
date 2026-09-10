import React, { useEffect, useState } from 'react';
import { loadOnboardingProfile } from '../services/supabase/profiles';
import { supabase } from '../services/supabase/client';

const LIME = '#c8f24a';

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
  user: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><circle cx="12" cy="8" r="3.6" /><path d="M4.5 20c1.6-3.6 4.6-5.4 7.5-5.4s5.9 1.8 7.5 5.4" /></svg>),
  spark: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" /></svg>),
  briefcase: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><rect x="3" y="7.5" width="18" height="12" rx="2" /><path d="M8 7.5V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v1.5M3 12.5h18" /></svg>),
  gear: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><circle cx="12" cy="12" r="3" /><path d="M19.4 13a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V19a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H4a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H10a1.7 1.7 0 0 0 1-1.5V4a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V10a1.7 1.7 0 0 0 1.5 1H20a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" /></svg>),
  logout: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3M16 16l4-4-4-4M20 12H9" /></svg>),
  search: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m20 20-4.3-4.3" /></svg>),
  sliders: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M8 5v14M16 5v14" /><circle cx="8" cy="9" r="2.1" /><circle cx="16" cy="15" r="2.1" /></svg>),
  calendar: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><rect x="3" y="4.5" width="18" height="16" rx="2.5" /><path d="M3 9h18M8 3v3M16 3v3" /></svg>),
  bell: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M6 10a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 14 6 10Z" /><path d="M10.5 19a1.7 1.7 0 0 0 3 0" /></svg>),
  chat: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M4 5h16v11H9l-5 4V5Z" /></svg>),
  expand: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M7 17 17 7M9 7h8v8" /></svg>),
  back: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>),
  plus: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M12 5v14M5 12h14" /></svg>),
  refresh: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M20 11A8 8 0 0 0 6.3 6.3L4 8.6M4 13a8 8 0 0 0 13.7 4.7L20 15.4" /><path d="M4 4v4.6h4.6M20 20v-4.6h-4.6" /></svg>),
  close: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M6 6l12 12M18 6 6 18" /></svg>),
  headphones: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M4 13v-1a8 8 0 0 1 16 0v1" /><rect x="3" y="13" width="4" height="6" rx="1.5" /><rect x="17" y="13" width="4" height="6" rx="1.5" /></svg>),
  github: (<svg viewBox="0 0 24 24" fill="currentColor" className="h-3.5 w-3.5"><path d="M12 2C6.48 2 2 6.58 2 12.26c0 4.54 2.87 8.4 6.84 9.77.5.1.68-.22.68-.48 0-.24-.01-1.04-.01-1.88-2.78.62-3.37-1.22-3.37-1.22-.46-1.2-1.13-1.52-1.13-1.52-.92-.64.07-.63.07-.63 1.02.07 1.56 1.07 1.56 1.07.9 1.57 2.37 1.12 2.95.86.09-.67.35-1.12.63-1.38-2.22-.26-4.56-1.14-4.56-5.06 0-1.12.39-2.04 1.03-2.76-.1-.26-.45-1.31.1-2.72 0 0 .84-.27 2.75 1.05A9.12 9.12 0 0 1 12 7.58c.85 0 1.72.12 2.53.35 1.9-1.32 2.74-1.05 2.74-1.05.56 1.41.21 2.46.1 2.72.64.72 1.03 1.64 1.03 2.76 0 3.93-2.35 4.8-4.58 5.05.36.32.68.94.68 1.9 0 1.38-.01 2.49-.01 2.83 0 .26.18.59.69.48A10.26 10.26 0 0 0 22 12.26C22 6.58 17.52 2 12 2Z" /></svg>),
};

// ---------- helpers ----------

const weight = (s) => s.split('').reduce((a, c) => a + c.charCodeAt(0), 0);

function buildSmoothPath(pts) {
  if (pts.length < 2) return '';
  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] || p2;
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
  }
  return d;
}

function valuesToPoints(values, w, h, padX = 14, padY = 16) {
  if (values.length < 2) return null;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = Math.max(max - min, 1);
  const innerW = w - padX * 2;
  return values.map((v, i) => ({
    x: padX + innerW * (i / (values.length - 1)),
    y: h - padY - ((v - min) / span) * (h - padY * 2),
    v,
  }));
}

// ---------- shells ----------

function Panel({ id, children, className = '', pad = 'p-4' }) {
  return (
    <section id={id} className={`relative flex flex-col overflow-hidden rounded-[26px] border border-white/70 bg-white/45 shadow-[inset_0_1px_0_rgba(255,255,255,0.9),inset_0_0_0_1px_rgba(255,255,255,0.25),0_20px_44px_-24px_rgba(40,50,30,0.35)] backdrop-blur-2xl ${pad} ${className}`}>
      {children}
    </section>
  );
}

function RoundBtn({ icon, dark, onClick, href, title }) {
  const cls = `flex h-9 w-9 items-center justify-center rounded-full border transition ${dark ? 'border-white/10 bg-[#161616] text-white hover:bg-[#2a2a2a]' : 'border-white/70 bg-white/55 text-[#3a3a38] backdrop-blur-md hover:bg-white/80 hover:text-[#161616]'}`;
  if (href) return <a href={href} title={title} className={cls}>{icon}</a>;
  return <button type="button" onClick={onClick} title={title} className={cls}>{icon}</button>;
}

function CardHead({ title, sub, action, dark }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className={`text-[14px] font-bold tracking-tight ${dark ? 'text-white' : 'text-[#1a1a1a]'}`}>{title}</p>
        {sub && <p className={`mt-0.5 text-[11px] font-medium ${dark ? 'text-white/45' : 'text-[#9a9a97]'}`}>{sub}</p>}
      </div>
      {action}
    </div>
  );
}

function MiniIconBtn({ icon, dark }) {
  return (
    <span className={`flex h-7 w-7 items-center justify-center rounded-full ${dark ? 'bg-[#161616] text-white' : 'bg-white/70 text-[#6a6a67] border border-white/70 backdrop-blur-md'}`}>{icon}</span>
  );
}

// ---------- charts ----------

function SkillActivity({ skills }) {
  const items = skills.slice(0, 7);
  if (!items.length) {
    return <div className="flex flex-1 flex-col items-center justify-center gap-1.5 text-center"><p className="text-xs font-semibold text-[#9a9a97]">No skills yet.</p><a href="/onboarding" className="text-[11px] font-bold text-[#1a1a1a] underline underline-offset-4">Add skills</a></div>;
  }
  const ws = items.map(weight);
  const max = Math.max(...ws);
  const topIdx = ws.indexOf(max);
  return (
    <div className="mt-2 flex flex-1 items-end justify-between gap-2">
      {items.map((skill, i) => {
        const pct = 26 + Math.round((ws[i] / max) * 74);
        const isTop = i === topIdx;
        return (
          <div key={skill} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1.5">
            {isTop && <span className="rounded-md bg-[#c8f24a] px-1.5 py-0.5 text-[8px] font-black uppercase tracking-wide text-[#1a1a1a]">Top</span>}
            <div className="flex w-full flex-1 items-end">
              <div className={`w-full rounded-[6px] ${isTop ? 'bg-[#c8f24a] shadow-[0_6px_14px_-4px_rgba(160,200,40,0.6)]' : 'bg-white/45 border border-white/60'}`} style={{ height: `${pct}%` }} title={skill} />
            </div>
            <span className="w-full truncate text-center text-[9px] font-semibold text-[#9a9a97]">{skill.length > 5 ? `${skill.slice(0, 4)}…` : skill}</span>
          </div>
        );
      })}
    </div>
  );
}

function AreaChart({ values, badge }) {
  const W = 340;
  const H = 118;
  const pts = valuesToPoints(values, W, H);
  if (!pts) {
    return <div className="flex flex-1 items-center justify-center"><p className="text-xs font-semibold text-[#9a9a97]">Add more skills to see your strength curve.</p></div>;
  }
  const line = buildSmoothPath(pts);
  const area = `${line} L ${pts[pts.length - 1].x} ${H - 6} L ${pts[0].x} ${H - 6} Z`;
  const mid = pts[Math.floor(pts.length / 2)];
  const badgeY = Math.max(mid.y - 20, 2);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 h-full min-h-[88px] w-full" preserveAspectRatio="none">
      <defs>
        <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="6" stroke="#c9c9c4" strokeWidth="1" />
        </pattern>
      </defs>
      <path d={area} fill="url(#hatch)" opacity="0.7" />
      <path d={line} fill="none" stroke="#1a1a1a" strokeWidth="1.6" />
      {pts.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="2.4" fill="#1a1a1a" />)}
      <g transform={`translate(${mid.x - 16}, ${badgeY})`}>
        <rect width="34" height="15" rx="7.5" fill="#c8f24a" />
        <text x="17" y="10.5" textAnchor="middle" fontSize="8.5" fontWeight="800" fill="#1a1a1a">{badge}</text>
      </g>
    </svg>
  );
}

function CurveChart({ values }) {
  const W = 340;
  const H = 96;
  const pts = valuesToPoints(values, W, H, 16, 14);
  if (!pts) {
    return <div className="flex h-24 items-center justify-center"><p className="text-xs font-semibold text-[#9a9a97]">Not enough data yet.</p></div>;
  }
  const line = buildSmoothPath(pts);
  const peak = pts.reduce((a, b) => (b.y < a.y ? b : a), pts[0]);
  const badgeX = Math.min(Math.max(peak.x - 20, 2), W - 42);
  const badgeY = peak.y - 20 < 2 ? peak.y + 7 : peak.y - 20;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-1 h-full min-h-[68px] w-full" preserveAspectRatio="none">
      <path d={line} fill="none" stroke="#1a1a1a" strokeWidth="1.6" />
      {pts.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="2.6" fill="#1a1a1a" />)}
      <g transform={`translate(${badgeX}, ${badgeY})`}>
        <rect width="40" height="15" rx="7.5" fill="#c8f24a" />
        <text x="20" y="10.5" textAnchor="middle" fontSize="8.5" fontWeight="800" fill="#1a1a1a">{Math.round(peak.v)}</text>
      </g>
    </svg>
  );
}

// ---------- bubble visual (hero) ----------

function BubbleCluster() {
  const dots = [
    [58, 22, 22], [72, 30, 15], [46, 34, 17], [64, 44, 19], [80, 46, 12],
    [40, 50, 13], [54, 56, 16], [70, 60, 14], [34, 64, 10], [50, 70, 12],
    [84, 62, 9], [62, 74, 10], [44, 80, 8], [76, 76, 8], [30, 44, 8],
  ];
  return (
    <div className="pointer-events-none absolute inset-0">
      {dots.map(([x, y, s], i) => (
        <span
          key={i}
          className="absolute rounded-full"
          style={{
            left: `${x}%`, top: `${y}%`, width: `${s}%`, aspectRatio: '1',
            background: `radial-gradient(circle at 32% 28%, #eafcb0, #b6e63f 55%, #7fae1f)`,
            boxShadow: '0 6px 14px -4px rgba(120,160,30,0.5)',
          }}
        />
      ))}
    </div>
  );
}

function StatusScreen({ children }) {
  return <main className="flex min-h-screen items-center justify-center bg-[#e9e9e7] text-[#1a1a1a]"><div className="text-center">{children}</div></main>;
}

// ---------- main ----------

function DashboardScreen() {
  const [status, setStatus] = useState('loading');
  const [profile, setProfile] = useState(null);
  const [user, setUser] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [heroOpen, setHeroOpen] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const currentUser = session?.user ?? null;
      if (!active) return;
      if (!currentUser) { setStatus('signed-out'); return; }
      setUser(currentUser);
      const loaded = await loadOnboardingProfile();
      if (!active) return;
      setProfile(loaded || {});
      setStatus('ready');
    })();
    return () => { active = false; };
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    const { data: { session } } = await supabase.auth.getSession();
    const currentUser = session?.user ?? null;
    if (!currentUser) { setStatus('signed-out'); setIsRefreshing(false); return; }
    setUser(currentUser);
    const loaded = await loadOnboardingProfile();
    setProfile(loaded || {});
    setStatus('ready');
    setIsRefreshing(false);
  };

  const handleLogout = async () => { await supabase.auth.signOut(); window.location.assign('/'); };

  if (status === 'loading') return <StatusScreen><p className="text-xs font-bold uppercase tracking-[0.2em] text-[#9a9a97]">Loading your dashboard…</p></StatusScreen>;
  if (status === 'signed-out') {
    return (
      <StatusScreen>
        <p className="text-lg font-semibold">You need to sign in to view your dashboard.</p>
        <a href="/" className="mt-5 inline-block rounded-full bg-[#161616] px-5 py-2.5 text-sm font-bold text-white transition hover:bg-[#2a2a2a]">Go to login</a>
      </StatusScreen>
    );
  }

  const skills = profile.currentSkills || [];
  const interests = profile.careerInterests || [];
  const experiences = profile.experiences || [];

  const progressSections = [
    { label: 'Education', done: Boolean(profile.collegeName && profile.educationLevel) },
    { label: 'Skills', done: skills.length > 0 },
    { label: 'Interests', done: interests.length > 0 },
    { label: 'Experience', done: experiences.length > 0 },
    { label: 'Links', done: Boolean(profile.githubUsername || profile.linkedinUrl) },
  ];
  const doneCount = progressSections.filter((s) => s.done).length;
  const completionPct = Math.round((doneCount / progressSections.length) * 100);

  const fullName = user?.user_metadata?.full_name || user?.user_metadata?.name || profile.githubUsername || profile.collegeName || 'Builder';
  const avatarUrl = user?.user_metadata?.avatar_url || user?.user_metadata?.picture;

  const combinedTags = [...interests, ...skills];
  const totalSignals = skills.length + interests.length + experiences.length;

  const now = new Date();
  const dateStr = now.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });

  // chart data (real, derived)
  const strengthValues = skills.slice(0, 7).map(weight);
  const eduFilled = [profile.collegeName, profile.educationLevel, profile.degree, profile.branch, profile.major].filter(Boolean).length;
  const linksFilled = [profile.githubUsername, profile.linkedinUrl].filter(Boolean).length;
  const buildupValues = [eduFilled, skills.length, interests.length, experiences.length, linksFilled];

  const tagTotal = combinedTags.length || 1;
  const skillShare = Math.round((skills.length / tagTotal) * 100);
  const interestShare = 100 - skillShare;

  const railItems = [
    { icon: icons.grid, href: '/dashboard', active: true, title: 'Dashboard' },
    { icon: icons.user, href: '/onboarding', title: 'Profile' },
    { icon: icons.spark, href: '#momentum-card', title: 'Career AI' },
    { icon: icons.briefcase, href: '#strength-card', title: 'Experience' },
    { icon: icons.gear, disabled: true, title: 'Settings' },
  ];

  const navTabs = [
    { label: 'Dashboard', icon: icons.grid, active: true, href: '/dashboard' },
    { label: 'Discover', icon: icons.analytics, href: '/discover' },
    { label: 'Career AI', icon: icons.pulse, href: '#momentum-card' },
    { label: 'Profile', icon: icons.data, href: '/onboarding' },
  ];

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
            <a href="/onboarding" className="hidden items-center gap-1.5 rounded-full border border-white/70 bg-white/55 px-3 py-1.5 text-[12.5px] font-semibold text-[#4a4a48] backdrop-blur-md transition hover:bg-white/80 hover:text-[#161616] sm:inline-flex">{icons.expand} Share</a>
            <RoundBtn icon={icons.bell} />
            {avatarUrl ? <img src={avatarUrl} alt={fullName} className="h-9 w-9 rounded-full object-cover ring-2 ring-white" /> : <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#161616] text-xs font-black text-white">{fullName.charAt(0).toUpperCase()}</div>}
          </div>
        </header>

        {/* Title row */}
        <div className="mt-5 flex shrink-0 flex-wrap items-center justify-between gap-y-2.5 gap-x-3">
          <div className="flex items-center gap-3">
            <a href="/" className="flex h-9 w-9 items-center justify-center rounded-full border border-white/70 bg-white/55 text-[#3a3a38] backdrop-blur-md transition hover:bg-white/80 hover:text-[#161616]">{icons.back}</a>
            <div>
              <p className="text-[11px] font-semibold text-[#9a9a97]">Profile · Overview</p>
              <h1 className="text-[22px] font-black leading-none tracking-tight sm:text-[25px]">Career Performance</h1>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <RoundBtn icon={icons.search} />
            <RoundBtn icon={icons.calendar} dark />
            <span className="hidden rounded-full border border-white/70 bg-white/55 px-3 py-1.5 text-[12px] font-semibold text-[#4a4a48] backdrop-blur-md sm:inline">{dateStr}</span>
            <button type="button" onClick={handleRefresh} disabled={isRefreshing} className="inline-flex items-center gap-1.5 rounded-full border border-white/70 bg-white/55 px-3 py-1.5 text-[12px] font-bold text-[#4a4a48] backdrop-blur-md transition hover:bg-white/80 hover:text-[#161616] disabled:opacity-50">{icons.refresh}{isRefreshing ? 'Refreshing' : 'Refresh'}</button>
            <a href="/onboarding" className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-[#161616] px-3.5 py-1.5 text-[12px] font-bold text-white transition hover:bg-[#2a2a2a]">{icons.plus} Edit Profile</a>
          </div>
        </div>

        {/* Body: rail + bento */}
        <div className="mt-5 flex min-h-0 flex-1 gap-5">
        {/* Icon rail */}
        <div className="hidden shrink-0 flex-col items-center justify-between py-1 lg:flex">
          <div className="flex flex-col items-center gap-3">
            {railItems.map((r, i) => (
              <a
                key={i}
                href={r.disabled ? undefined : r.href}
                title={r.title}
                className={`flex h-9 w-9 items-center justify-center rounded-full transition ${r.active ? 'bg-[#161616] text-white shadow-[0_8px_18px_-6px_rgba(0,0,0,0.5)]' : r.disabled ? 'text-[#bcbcb9] cursor-default' : 'border border-white/70 bg-white/55 text-[#6a6a67] backdrop-blur-md hover:bg-white/80 hover:text-[#161616]'}`}
              >
                {r.icon}
              </a>
            ))}
          </div>
          <button type="button" onClick={handleLogout} title="Logout" className="flex h-9 w-9 items-center justify-center rounded-full border border-white/70 bg-white/55 text-[#6a6a67] backdrop-blur-md transition hover:bg-white/80 hover:text-[#161616]">{icons.logout}</button>
        </div>

        {/* Bento */}
        <div className="grid min-h-0 flex-1 grid-cols-1 gap-5 lg:grid-cols-12 lg:grid-rows-[minmax(0,1fr)_minmax(0,1fr)]">
          {/* Hero (tall) */}
          {heroOpen && (
            <Panel className="lg:col-span-4 lg:row-span-2" pad="p-0">
              <div className="relative flex-1 overflow-hidden rounded-t-[22px] bg-[linear-gradient(160deg,rgba(242,246,230,0.6),rgba(224,232,210,0.35))]">
                <div className="relative z-10 flex items-center justify-between p-4">
                  <p className="text-[14px] font-bold tracking-tight">Your profile</p>
                  <button type="button" onClick={() => setHeroOpen(false)} className="flex h-7 w-7 items-center justify-center rounded-full border border-white/70 bg-white/70 text-[#5a5a58] backdrop-blur-md transition hover:text-[#161616]">{icons.close}</button>
                </div>
                <BubbleCluster />
              </div>
              {/* nested glass */}
              <div className="relative m-4 rounded-[20px] border border-white/70 bg-white/45 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_12px_30px_-16px_rgba(0,0,0,0.3)] backdrop-blur-2xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#161616] text-white">{icons.spark}</span>
                    <div>
                      <p className="text-[13px] font-bold leading-tight">Highlights</p>
                      <p className="text-[10px] text-[#9a9a97]">Your profile at a glance</p>
                    </div>
                  </div>
                  <a href="/onboarding" className="flex h-7 w-7 items-center justify-center rounded-full border border-white/70 bg-white/70 text-[#5a5a58] backdrop-blur-md transition hover:text-[#161616]">{icons.expand}</a>
                </div>
                <div className="mt-3 flex items-end gap-5">
                  <div><p className="text-[22px] font-black leading-none">{completionPct}%</p><p className="text-[10px] font-semibold text-[#9a9a97]">complete</p></div>
                  <div><p className="text-[22px] font-black leading-none">{totalSignals}</p><p className="text-[10px] font-semibold text-[#9a9a97]">signals</p></div>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  {[{ n: skills.length, l: 'Skills', hi: true }, { n: interests.length, l: 'Interests', hi: false }, { n: experiences.length, l: 'Experience', hi: true }].map((b, i) => (
                    <div key={i} className="flex flex-col items-center">
                      <div className="flex h-12 w-full items-end justify-center">
                        <div className={`w-full rounded-md ${b.hi ? 'bg-[#c8f24a] shadow-[0_6px_14px_-5px_rgba(160,200,40,0.6)]' : 'bg-white/50 border border-white/60'}`} style={{ height: `${Math.min(30 + b.n * 16, 100)}%` }} />
                      </div>
                      <p className="mt-1 text-[13px] font-black leading-none">{b.n}</p>
                      <p className="text-[9px] font-semibold text-[#9a9a97]">{b.l}</p>
                    </div>
                  ))}
                </div>
              </div>
            </Panel>
          )}

          {/* Activity → Skill mix */}
          <Panel className={heroOpen ? 'lg:col-span-3' : 'lg:col-span-4'}>
            <CardHead title="Activity" sub="Skills captured" action={<div className="flex gap-1.5"><MiniIconBtn icon={icons.sliders} /><MiniIconBtn icon={icons.expand} /></div>} />
            <p className="mt-1.5 text-[26px] font-black leading-none">{skills.length}</p>
            <SkillActivity skills={skills} />
          </Panel>

          {/* Comparison of Revenue → Strength */}
          <Panel id="strength-card" className={heroOpen ? 'lg:col-span-5' : 'lg:col-span-4'}>
            <CardHead title="Profile Strength" sub="Relative strength across your skills" action={<div className="flex gap-1.5"><MiniIconBtn icon={icons.sliders} dark /><MiniIconBtn icon={icons.chat} /><MiniIconBtn icon={icons.expand} /></div>} />
            <p className="mt-1 text-[24px] font-black leading-none">{completionPct}<span className="text-base font-bold text-[#9a9a97]">% ready</span></p>
            <div className="mt-1 flex flex-1"><AreaChart values={strengthValues} badge={`+${completionPct}%`} /></div>
          </Panel>

          {/* Total Spend → Momentum */}
          <Panel id="momentum-card" className="lg:col-span-5">
            <CardHead title="Profile Buildup" sub="Items across your profile sections" action={<div className="flex gap-1.5"><MiniIconBtn icon={icons.sliders} dark /><MiniIconBtn icon={icons.expand} /></div>} />
            <div className="mt-1 flex items-end gap-5">
              <div className="shrink-0">
                <p className="text-[24px] font-black leading-none">{totalSignals}<span className="ml-1 text-sm font-bold text-[#9a9a97]">signals</span></p>
                <p className="text-[11px] font-semibold text-[#9a9a97]">of {progressSections.length} sections filled</p>
              </div>
              <div className="flex flex-1"><CurveChart values={buildupValues} /></div>
            </div>
            <div className="mt-2 flex gap-2">
              <span className="inline-flex items-center gap-2 rounded-lg border border-white/70 bg-white/55 px-3 py-1.5 text-[11px] font-bold text-[#4a4a48] backdrop-blur-md"><b className="text-[13px] text-[#1a1a1a]">{skills.length}</b> Skills</span>
              <span className="inline-flex items-center gap-2 rounded-lg border border-white/70 bg-white/55 px-3 py-1.5 text-[11px] font-bold text-[#4a4a48] backdrop-blur-md"><b className="text-[13px] text-[#1a1a1a]">{interests.length}</b> Interests</span>
            </div>
          </Panel>

          {/* Virtual Cards → Split */}
          <Panel className="lg:col-span-3">
            <CardHead title="Career Snapshot" action={<MiniIconBtn icon={icons.expand} />} />
            <p className="mt-2 text-[11px] font-semibold text-[#9a9a97]">Profile completion</p>
            <p className="text-[26px] font-black leading-none">{completionPct}<span className="text-base font-bold text-[#9a9a97]">%</span></p>
            <p className="mt-0.5 truncate text-[11px] font-semibold text-[#9a9a97]">{profile.collegeName || 'College not added'}</p>
            <div className="mt-auto space-y-2.5 pt-3">
              <div>
                <div className="flex items-center justify-between text-[11px] font-bold"><span className="text-[#4a4a48]">Skills</span><span className="text-[#9a9a97]">{skillShare}%</span></div>
                <div className="mt-1 h-2 rounded-full bg-white/50 border border-white/60"><div className="h-full rounded-full bg-[#c8f24a]" style={{ width: `${skillShare}%` }} /></div>
              </div>
              <div>
                <div className="flex items-center justify-between text-[11px] font-bold"><span className="text-[#4a4a48]">Interests</span><span className="text-[#9a9a97]">{interestShare}%</span></div>
                <div className="mt-1 h-2 rounded-full bg-white/50 border border-white/60"><div className="h-full rounded-full bg-[#161616]" style={{ width: `${interestShare}%` }} /></div>
              </div>
            </div>
          </Panel>
        </div>
        </div>
      </div>
    </div>
  );
}

export default DashboardScreen;
