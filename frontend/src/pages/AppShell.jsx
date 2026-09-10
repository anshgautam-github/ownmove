import React, { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react';
import { loadOnboardingProfile, saveOnboardingProfile, uploadResume, getResumeSignedUrl, validateResumeFile } from '../services/supabase/profiles';
import { loadOpportunities } from '../services/supabase/opportunities';
import { loadForYouRecommendations } from '../services/api/recommendations';
import { loadSavedOpportunities, saveOpportunity, unsaveOpportunity } from '../services/supabase/savedOpportunities';
import { loadAppliedOpportunityIds, markOpportunityApplied, unmarkOpportunityApplied } from '../services/supabase/opportunityApplications';
import { supabase } from '../services/supabase/client';
import { getCache, setCache, setCacheScope } from '../services/api/localCache';
import CertificationsCatalog from '../components/certifications/CertificationsCatalog';

// Code-split: these five are the heaviest screens in the app (rich
// dashboards, an animated SVG/Framer-Motion roadmap) and are only ever
// needed once a signed-in user actually opens Career AI or Learning Hub —
// loading them eagerly on first paint (landing page, sign-in, onboarding)
// bought nothing for most visitors. React.lazy + the <Suspense> boundaries
// below defer their JS until the user actually navigates there.
const ProfileAnalysisDashboard = lazy(() => import('../components/career-ai/ProfileAnalysisDashboard'));
const CareerRoadmapDashboard = lazy(() => import('../components/career-ai/CareerRoadmapDashboard'));
const CareerSimulationDashboard = lazy(() => import('../components/career-ai/CareerSimulationDashboard'));
const CareerCoachDashboard = lazy(() => import('../components/career-ai/CareerCoachDashboard'));
const LearningJourney = lazy(() => import('../components/certifications/LearningJourney'));

// Same spinner used for the top-level "Loading…" auth check (see
// StatusScreen usage below) so a lazy chunk loading reads as the same kind
// of brief wait, not a different, unfamiliar loading style.
function PaneLoadingFallback() {
  return (
    <div className="flex h-full min-h-[240px] w-full flex-col items-center justify-center gap-4">
      <div className="h-9 w-9 animate-spin rounded-full border-[3px] border-[#ded9ff] border-t-[#5c63ff]" />
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#9a9a97]">Loading…</p>
    </div>
  );
}

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
  star: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><path d="M12 3.5l2.6 5.6 6.1.6-4.6 4.1 1.3 6-5.4-3.1-5.4 3.1 1.3-6-4.6-4.1 6.1-.6L12 3.5Z" /></svg>),
  briefcaseLg: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><rect x="3" y="7.5" width="18" height="12" rx="2" /><path d="M8 7.5V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v1.5M3 12.5h18" /></svg>),
  trophy: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><path d="M7 4h10v5a5 5 0 0 1-10 0V4Z" /><path d="M7 5H4v1.5A3.5 3.5 0 0 0 7 10M17 5h3v1.5A3.5 3.5 0 0 1 17 10M9.5 19.5h5M12 14v5.5" /></svg>),
  award: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><circle cx="12" cy="9" r="5.2" /><path d="M8.5 13.5 7 20l5-2.3 5 2.3-1.5-6.5" /></svg>),
  cap: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><path d="M12 4.5 2.5 9 12 13.5 21.5 9 12 4.5Z" /><path d="M6 11v4.5c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5V11" /></svg>),
  flask: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><path d="M9.5 3.5h5M10 3.5v6.3L4.8 18a1.7 1.7 0 0 0 1.5 2.5h11.4a1.7 1.7 0 0 0 1.5-2.5L14 9.8V3.5" /><path d="M7.5 15.5h9" /></svg>),
  github: (<svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5"><path d="M12 2C6.48 2 2 6.58 2 12.26c0 4.54 2.87 8.4 6.84 9.77.5.1.68-.22.68-.48 0-.24-.01-1.04-.01-1.88-2.78.62-3.37-1.22-3.37-1.22-.46-1.2-1.13-1.52-1.13-1.52-.92-.64.07-.63.07-.63 1.02.07 1.56 1.07 1.56 1.07.9 1.57 2.37 1.12 2.95.86.09-.67.35-1.12.63-1.38-2.22-.26-4.56-1.14-4.56-5.06 0-1.12.39-2.04 1.03-2.76-.1-.26-.45-1.31.1-2.72 0 0 .84-.27 2.75 1.05A9.12 9.12 0 0 1 12 7.58c.85 0 1.72.12 2.53.35 1.9-1.32 2.74-1.05 2.74-1.05.56 1.41.21 2.46.1 2.72.64.72 1.03 1.64 1.03 2.76 0 3.93-2.35 4.8-4.58 5.05.36.32.68.94.68 1.9 0 1.38-.01 2.49-.01 2.83 0 .26.18.59.69.48A10.26 10.26 0 0 0 22 12.26C22 6.58 17.52 2 12 2Z" /></svg>),
  ribbon: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><circle cx="12" cy="8" r="5" /><path d="m8.5 12.5-1.8 8 5.3-2.7 5.3 2.7-1.8-8" /></svg>),
  book: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15.5H6.5A2.5 2.5 0 0 0 4 21V5.5Z" /><path d="M4 18.5A2.5 2.5 0 0 1 6.5 16H20" /></svg>),
  target: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1.5" /></svg>),
  users2: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><circle cx="9" cy="8.5" r="3.2" /><circle cx="17" cy="9.5" r="2.6" /><path d="M3.5 19c1.2-3.2 3.4-4.7 5.5-4.7s4.3 1.5 5.5 4.7M15 14.9c2 .2 3.7 1.6 4.6 4.1" /></svg>),
  calendarLg: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><rect x="3" y="4.5" width="18" height="16" rx="2.5" /><path d="M3 9h18M8 3v3M16 3v3" /></svg>),
  layers: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 13 9 5 9-5" /></svg>),
  route: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><circle cx="5.5" cy="6" r="2" /><circle cx="18.5" cy="18" r="2" /><path d="M5.5 8v2.5A4 4 0 0 0 9.5 14.5h5a4 4 0 0 1 4 4V19" strokeDasharray="2.2 3" /></svg>),
  chevronDown: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="m6 9 6 6 6-6" /></svg>),
  check: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5"><path d="M5 13l4 4L19 7" /></svg>),
  bookmark: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M6 4.5h12a1 1 0 0 1 1 1V21l-7-4-7 4V5.5a1 1 0 0 1 1-1Z" /></svg>),
  pin: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3"><path d="M12 21s7-6.5 7-11.5a7 7 0 1 0-14 0C5 14.5 12 21 12 21Z" /><circle cx="12" cy="9.5" r="2.3" /></svg>),
  globe: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3"><circle cx="12" cy="12" r="8.5" /><path d="M3.5 12h17M12 3.5c2.5 2.4 3.8 5.4 3.8 8.5s-1.3 6.1-3.8 8.5c-2.5-2.4-3.8-5.4-3.8-8.5S9.5 5.9 12 3.5Z" /></svg>),
  linkedin: (<svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5"><rect x="3" y="3" width="18" height="18" rx="3" /><path fill="#fff" d="M7.8 9.6h2.6v8.4H7.8V9.6Zm1.3-4.2a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM12 9.6h2.5v1.15h.03c.35-.63 1.2-1.3 2.47-1.3 2.64 0 3.13 1.65 3.13 3.8v4.75h-2.6v-4.21c0-1-.02-2.3-1.44-2.3-1.44 0-1.66 1.08-1.66 2.2v4.31H12V9.6Z" /></svg>),
  resume: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5"><path d="M7 3.5h7l3.5 3.5V20a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" /><path d="M14 3.5V7h3.5" /><path d="M8.5 12h7M8.5 15h7M8.5 18h4" /></svg>),
  info: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3"><circle cx="12" cy="12" r="8.5" /><path d="M12 11v5.5" /><circle cx="12" cy="8" r="0.6" fill="currentColor" stroke="none" /></svg>),
};

// ---------- opportunities helpers ----------

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diffMs = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diffMs / 86400000);
  if (days <= 0) return 'today';
  if (days === 1) return '1 day ago';
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return `${months} ${months === 1 ? 'month' : 'months'} ago`;
}

function formatDate(dateStr) {
  if (!dateStr) return null;
  return new Date(dateStr).toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
}

function isWithinDeadlineWindow(deadline, days) {
  if (!deadline) return false;
  return new Date(deadline).getTime() - Date.now() <= days * 86400000;
}

// ---------- profile form config ----------

const educationLevels = ['High school', 'Diploma', 'Undergraduate', 'Graduate', 'Postgraduate', 'Bootcamp', 'Self-taught'];
const degreeOptions = ['B.Tech', 'B.E.', 'B.Sc', 'BCA', 'BBA', 'BA', 'MBA', 'M.Tech', 'M.Sc', 'Diploma', 'Other'];
const branchOptions = ['Computer Science', 'Information Technology', 'Electronics', 'Mechanical', 'Civil', 'Data Science', 'Design', 'Business', 'Other'];
const graduationStatusOptions = ['Currently studying', 'Graduated', 'On a gap year', 'Dropped out'];
const careerInterestOptions = ['AI/ML', 'Frontend', 'Backend', 'Full Stack', 'Product', 'Data Science', 'Cybersecurity', 'Cloud', 'UI/UX', 'Marketing', 'Founder'];
const skillOptions = ['React', 'JavaScript', 'Python', 'Node.js', 'SQL', 'Git', 'Figma', 'Excel', 'ML', 'Communication', 'Leadership', 'Writing'];
const employmentTypes = ['Internship', 'Part-time', 'Full-time', 'Freelance', 'Volunteer', 'Campus role', 'Project'];

function normalizeProfile(existing) {
  const source = existing || {};
  return {
    fullName: source.fullName || '',
    headline: source.headline || '',
    bio: source.bio || '',
    city: source.city || '',
    country: source.country || '',
    collegeName: source.collegeName || '',
    educationLevel: source.educationLevel || '',
    degree: source.degree || '',
    branch: source.branch || '',
    major: source.major || '',
    graduationYear: source.graduationYear != null ? String(source.graduationYear) : '',
    graduationStatus: source.graduationStatus || '',
    careerInterests: source.careerInterests || [],
    currentSkills: source.currentSkills || [],
    targetRole: source.targetRole || '',
    targetCompany: source.targetCompany || '',
    experiences: (source.experiences || []).map((experience) => ({
      id: experience.id || crypto.randomUUID(),
      title: experience.title || '',
      company: experience.company || '',
      experienceType: experience.experienceType || '',
      location: experience.location || '',
      startDate: experience.startDate || '',
      endDate: experience.endDate || '',
      currentlyWorking: !!experience.currentlyWorking,
      description: experience.description || '',
      skillsUsed: experience.skillsUsed || [],
    })),
    githubUrl: source.githubUrl || '',
    linkedinUrl: source.linkedinUrl || '',
    resumeUrl: source.resumeUrl || '',
  };
}

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

// The shared "glass panel" recipe: a translucent top-to-bottom gradient
// (rather than a flat tint) plus backdrop-blur gives each card a soft sheen
// and lets the ambient color blobs behind the shell read through it, closer
// to an iOS frosted-glass surface than a plain white card. The extra inset
// highlight along the top edge is the "light catching the rim of the glass"
// touch — kept subtle so it reads as depth, not a gimmick.
function Panel({ id, children, className = '', pad = 'p-4' }) {
  return (
    <section
      id={id}
      className={`relative flex flex-col overflow-hidden rounded-[26px] border border-white/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.82)_0%,rgba(255,255,255,0.58)_100%)] shadow-[inset_0_1.5px_0_rgba(255,255,255,0.95),inset_0_0_0_1px_rgba(255,255,255,0.3),0_24px_48px_-24px_rgba(40,50,30,0.4)] backdrop-blur-2xl ${pad} ${className}`}
    >
      {children}
    </section>
  );
}

function RoundBtn({ icon, dark, onClick, href, title }) {
  const cls = `flex h-9 w-9 items-center justify-center rounded-full border transition ${dark ? 'border-white/10 bg-[#161616] text-white hover:bg-[#2a2a2a]' : 'border-white/70 bg-white/75 backdrop-blur-md text-[#3a3a38] hover:bg-white/80 hover:text-[#161616]'}`;
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
    <span className={`flex h-7 w-7 items-center justify-center rounded-full ${dark ? 'bg-[#161616] text-white' : 'bg-white/70 text-[#6a6a67] border border-white/70'}`}>{icon}</span>
  );
}

// ---------- charts ----------

function SkillActivity({ skills }) {
  const items = skills.slice(0, 7);
  if (!items.length) {
    return <div className="flex flex-1 flex-col items-center justify-center gap-1.5 text-center"><p className="text-xs font-semibold text-[#9a9a97]">No skills yet.</p><a href="/profile" className="text-[11px] font-bold text-[#1a1a1a] underline underline-offset-4">Add skills</a></div>;
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
            {isTop && <span className="rounded-md bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] px-1.5 py-0.5 text-[8px] font-black uppercase tracking-wide text-white">Top</span>}
            <div className="flex w-full flex-1 items-end">
              <div className={`w-full rounded-[6px] ${isTop ? 'bg-[#7b62e8] shadow-[0_6px_14px_-4px_rgba(101,89,227,0.5)]' : 'bg-white/70 border border-white/60'}`} style={{ height: `${pct}%` }} title={skill} />
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
        <rect width="34" height="15" rx="7.5" fill="#7b62e8" />
        <text x="17" y="10.5" textAnchor="middle" fontSize="8.5" fontWeight="800" fill="#ffffff">{badge}</text>
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
        <rect width="40" height="15" rx="7.5" fill="#7b62e8" />
        <text x="20" y="10.5" textAnchor="middle" fontSize="8.5" fontWeight="800" fill="#ffffff">{Math.round(peak.v)}</text>
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
            background: `radial-gradient(circle at 32% 28%, #d8ceff, #8a72f0 55%, #5c46c9)`,
            boxShadow: '0 6px 14px -4px rgba(101,89,227,0.5)',
          }}
        />
      ))}
    </div>
  );
}

// This used to be a flat #e9e9e7 rectangle with plain gray text sitting on
// it — the very first thing anyone sees while the session/profile check
// resolves, and it looked like a broken page rather than part of OwnMove.
// It now uses the same warm-cream/lavender wash and radial glows as the
// Discover/Career AI panels and the FAQ section, with the wordmark anchoring
// it, so the boot screen actually reads as this product loading rather than
// a blank tab.
function StatusScreen({ children }) {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[linear-gradient(180deg,#fffdf9_0%,#fff8f2_42%,#f8f6ff_100%)] text-[#1a1a1a]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(255,224,187,0.4),transparent_30%),radial-gradient(circle_at_85%_25%,rgba(154,127,255,0.22),transparent_28%),radial-gradient(circle_at_50%_100%,rgba(101,99,255,0.1),transparent_35%)]" />
      <div className="relative z-10 flex flex-col items-center text-center">
        <img src="/logo.svg" alt="OwnMove" className="h-12 w-auto" />
        <div className="mt-8">{children}</div>
      </div>
    </main>
  );
}

// ---------- discover categories ----------

const categories = [
  { key: 'for-you', label: 'For You', icon: icons.star, desc: 'Matches curated from your skills, interests, and goals.', featured: true },
  { key: 'programs', label: 'Programs', icon: icons.cap, desc: 'Ambassador programs, summer schools, and student initiatives.' },
  { key: 'hackathons', label: 'Hackathons', icon: icons.trophy, desc: 'Build fast, ship prototypes, win prizes.' },
  { key: 'certifications', label: 'Certifications', icon: icons.ribbon, desc: 'Credentials that strengthen your profile.' },
  { key: 'learning-hub', label: 'Learning Hub', icon: icons.book, desc: "Explore official learning platforms from the world's leading companies" },
  { key: 'communities', label: 'Communities', icon: icons.users2, desc: 'Groups and networks to grow alongside.' },
  { key: 'events', label: 'Events', icon: icons.calendarLg, desc: 'Conferences, meetups, and webinars.' },
  { key: 'applied', label: 'Applied', icon: icons.check, desc: "Opportunities you've marked as applied." },
];

// Lets the applied-toggle toast say "Moved to Applied" / "Moved back to
// Programs" without a switch statement — keyed off the same `categories`
// list that drives the sidebar tabs, so labels never drift out of sync.
const categoryLabelByKey = categories.reduce((acc, c) => { acc[c.key] = c.label; return acc; }, {});

const careerAiOptions = [
  { key: 'ai-coach', label: 'AI Coach', icon: icons.spark, desc: 'A guided assistant that helps you plan your next move.', featured: true },
  { key: 'profile-analysis', label: 'Profile Analysis', icon: icons.pulse, desc: 'A breakdown of your profile’s strengths and gaps.' },
  { key: 'career-roadmap', label: 'Career Roadmap', icon: icons.route, desc: 'A step-by-step path toward your target roles.' },
  { key: 'career-simulation', label: 'Career Simulation', icon: icons.layers, desc: 'Preview how different paths could play out.' },
  { key: 'linkedin-optimizer', label: 'LinkedIn Optimizer', icon: icons.linkedin, desc: 'Sharpen your LinkedIn presence for recruiters.', comingSoon: true },
  { key: 'github-optimizer', label: 'GitHub Optimizer', icon: icons.github, desc: 'Make your GitHub profile easier to evaluate.', comingSoon: true },
  { key: 'resume-optimizer', label: 'Resume Optimizer', icon: icons.resume, desc: 'Tighten your resume for the roles you want.', comingSoon: true },
];

// ---------- dashboard content ----------

function DashboardBody({ profile }) {
  const [heroOpen, setHeroOpen] = useState(true);

  const skills = profile.currentSkills || [];
  const interests = profile.careerInterests || [];
  const experiences = profile.experiences || [];

  const progressSections = [
    { label: 'Education', done: Boolean(profile.collegeName && profile.educationLevel) },
    { label: 'Skills', done: skills.length > 0 },
    { label: 'Interests', done: interests.length > 0 },
    { label: 'Experience', done: experiences.length > 0 },
    { label: 'Links', done: Boolean(profile.githubUrl || profile.linkedinUrl) },
  ];
  const doneCount = progressSections.filter((s) => s.done).length;
  const completionPct = Math.round((doneCount / progressSections.length) * 100);

  const combinedTags = [...interests, ...skills];
  const totalSignals = skills.length + interests.length + experiences.length;

  const strengthValues = skills.slice(0, 7).map(weight);
  const eduFilled = [profile.collegeName, profile.educationLevel, profile.degree, profile.branch, profile.major].filter(Boolean).length;
  const linksFilled = [profile.githubUrl, profile.linkedinUrl].filter(Boolean).length;
  const buildupValues = [eduFilled, skills.length, interests.length, experiences.length, linksFilled];

  const tagTotal = combinedTags.length || 1;
  const skillShare = Math.round((skills.length / tagTotal) * 100);
  const interestShare = 100 - skillShare;

  const railItems = [
    { icon: icons.grid, href: '/dashboard', active: true, title: 'Dashboard' },
    { icon: icons.user, href: '/profile', title: 'Profile' },
    { icon: icons.spark, href: '/career-ai', title: 'Career AI' },
    { icon: icons.briefcase, href: '#strength-card', title: 'Experience' },
    { icon: icons.gear, disabled: true, title: 'Settings' },
  ];

  const handleLogout = async () => { await supabase.auth.signOut(); window.location.assign('/'); };

  return (
    <div className="flex min-h-0 flex-1 gap-5">
      {/* Icon rail */}
      <div className="hidden shrink-0 flex-col items-center justify-between py-1 lg:flex">
        <div className="flex flex-col items-center gap-3">
          {railItems.map((r, i) => (
            <a
              key={i}
              href={r.disabled ? undefined : r.href}
              title={r.title}
              className={`flex h-9 w-9 items-center justify-center rounded-full transition ${r.active ? 'bg-[#161616] text-white shadow-[0_8px_18px_-6px_rgba(0,0,0,0.5)]' : r.disabled ? 'text-[#bcbcb9] cursor-default' : 'border border-white/70 bg-white/75 backdrop-blur-md text-[#6a6a67] hover:bg-white/80 hover:text-[#161616]'}`}
            >
              {r.icon}
            </a>
          ))}
        </div>
        <button type="button" onClick={handleLogout} title="Logout" className="flex h-9 w-9 items-center justify-center rounded-full border border-white/70 bg-white/75 backdrop-blur-md text-[#6a6a67] transition hover:bg-white/80 hover:text-[#161616]">{icons.logout}</button>
      </div>

      {/* Bento */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-5 lg:grid-cols-12 lg:grid-rows-[minmax(0,1fr)_minmax(0,1fr)]">
        {/* Hero (tall) */}
        {heroOpen && (
          <Panel className="lg:col-span-4 lg:row-span-2" pad="p-0">
            <div className="relative flex-1 overflow-hidden rounded-t-[26px] bg-[linear-gradient(160deg,rgba(242,246,230,0.6),rgba(224,232,210,0.35))]">
              <div className="relative z-10 flex items-center justify-between p-4">
                <p className="text-[14px] font-bold tracking-tight">Your profile</p>
                <button type="button" onClick={() => setHeroOpen(false)} className="flex h-7 w-7 items-center justify-center rounded-full border border-white/70 bg-white/70 text-[#5a5a58] transition hover:text-[#161616]">{icons.close}</button>
              </div>
              <BubbleCluster />
            </div>
            {/* nested glass */}
            <div className="relative m-4 rounded-[20px] border border-white/70 bg-white/70 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_12px_30px_-16px_rgba(0,0,0,0.3)]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#161616] text-white">{icons.spark}</span>
                  <div>
                    <p className="text-[13px] font-bold leading-tight">Highlights</p>
                    <p className="text-[10px] text-[#9a9a97]">Your profile at a glance</p>
                  </div>
                </div>
                <a href="/profile" className="flex h-7 w-7 items-center justify-center rounded-full border border-white/70 bg-white/70 text-[#5a5a58] transition hover:text-[#161616]">{icons.expand}</a>
              </div>
              <div className="mt-3 flex items-end gap-5">
                <div><p className="text-[22px] font-black leading-none">{completionPct}%</p><p className="text-[10px] font-semibold text-[#9a9a97]">complete</p></div>
                <div><p className="text-[22px] font-black leading-none">{totalSignals}</p><p className="text-[10px] font-semibold text-[#9a9a97]">signals</p></div>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2">
                {[{ n: skills.length, l: 'Skills', hi: true }, { n: interests.length, l: 'Interests', hi: false }, { n: experiences.length, l: 'Experience', hi: true }].map((b, i) => (
                  <div key={i} className="flex flex-col items-center">
                    <div className="flex h-12 w-full items-end justify-center">
                      <div className={`w-full rounded-md ${b.hi ? 'bg-[#7b62e8] shadow-[0_6px_14px_-5px_rgba(101,89,227,0.5)]' : 'bg-white/50 border border-white/60'}`} style={{ height: `${Math.min(30 + b.n * 16, 100)}%` }} />
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
            <span className="inline-flex items-center gap-2 rounded-lg border border-white/70 bg-white/75 backdrop-blur-md px-3 py-1.5 text-[11px] font-bold text-[#4a4a48]"><b className="text-[13px] text-[#1a1a1a]">{skills.length}</b> Skills</span>
            <span className="inline-flex items-center gap-2 rounded-lg border border-white/70 bg-white/75 backdrop-blur-md px-3 py-1.5 text-[11px] font-bold text-[#4a4a48]"><b className="text-[13px] text-[#1a1a1a]">{interests.length}</b> Interests</span>
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
              <div className="mt-1 h-2 rounded-full bg-white/50 border border-white/60"><div className="h-full rounded-full bg-[linear-gradient(90deg,#7b62e8_0%,#5c63ff_100%)]" style={{ width: `${skillShare}%` }} /></div>
            </div>
            <div>
              <div className="flex items-center justify-between text-[11px] font-bold"><span className="text-[#4a4a48]">Interests</span><span className="text-[#9a9a97]">{interestShare}%</span></div>
              <div className="mt-1 h-2 rounded-full bg-white/50 border border-white/60"><div className="h-full rounded-full bg-[#161616]" style={{ width: `${interestShare}%` }} /></div>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}

// ---------- opportunity card ----------

function OpportunityCard({ item, matched, saved, onToggleSaved, applied, onToggleApplied, exiting }) {
  const [logoFailed, setLogoFailed] = useState(false);
  // Once something is saved, the bookmark button's only remaining job is
  // "remove it" — swapping to a cross on hover (Saved tab and Discover
  // alike) makes that obvious instead of leaving the same bookmark glyph
  // in both its "save" and "remove" states.
  const [saveHovered, setSaveHovered] = useState(false);
  // Description preview used to be hover-only, which doesn't exist on a
  // touchscreen. Tapping the row now toggles this instead, alongside
  // (not instead of) the CSS :hover reveal, so desktop keeps working
  // exactly as before while touch devices get an explicit tap target.
  const [showDescription, setShowDescription] = useState(false);
  const deadlineLabel = formatDate(item.deadline);
  const postedLabel = timeAgo(item.postedAt);
  const eligibleYearsLabel = (item.eligibleYears || []).length > 0 ? item.eligibleYears.join(', ') : '';
  const locationLabel = item.isRemote ? 'Remote' : (item.location || 'On-site');
  const showLogo = item.logoUrl && !logoFailed;

  // Only the expand arrow (a real <a href> in the corner notch) opens the
  // listing now — the card background itself is no longer a click target,
  // so tapping/clicking anywhere else on the card (description preview,
  // save, mark-as-applied, or just empty space) does nothing but its own
  // thing instead of also opening a new tab underneath it.

  return (
    <>
    <div
      className={`group relative flex transform-gpu flex-col rounded-[22px] border border-white/60 bg-[linear-gradient(165deg,rgba(255,255,255,0.62)_0%,rgba(250,248,255,0.4)_55%,rgba(255,255,255,0.26)_100%)] p-4 pr-9 text-[#1a1a1a] shadow-[inset_0_1.5px_0_rgba(255,255,255,0.9),0_10px_24px_-18px_rgba(40,32,70,0.35)] backdrop-blur-xl transition-all duration-300 ease-out ${
        exiting
          ? 'pointer-events-none scale-90 opacity-0'
          : 'hover:-translate-y-1 hover:border-white/90 hover:bg-[linear-gradient(165deg,rgba(255,255,255,0.88)_0%,rgba(250,248,255,0.65)_55%,rgba(255,255,255,0.5)_100%)] hover:shadow-[inset_0_1.5px_0_rgba(255,255,255,0.95),0_24px_44px_-18px_rgba(101,89,227,0.28)]'
      }`}
    >
      {/* Faint brand-tinted ambient glow in the opposite corner from the
          "bitten corner" notch — same quiet warm/lavender wash used on the
          Learning Hub and FAQ panels, dialed down so it reads as a bit of
          premium depth rather than a redesign. */}
      <div className="pointer-events-none absolute -bottom-6 -left-6 h-24 w-24 rounded-full bg-[radial-gradient(circle,rgba(123,98,232,0.16)_0%,transparent_70%)] opacity-0 blur-xl transition-opacity duration-300 group-hover:opacity-100" />

      {/* "Bitten corner" notch: paints a circle the same tone as the panel
          behind the card, straddling the corner itself (mostly anchored
          inside the card, only a small sliver crossing the edge). That
          sliver reveals a genuine ring of the true background color, so it
          reads as an open notch bitten into the corner rather than a flat
          circle pasted inside the card (too closed) or a button floating
          detached in the grid gap (too far outside). */}
      <div className="pointer-events-none absolute -right-2.5 -top-2.5 z-[5] h-14 w-14 rounded-full bg-[#f5f5f2]" />

      {/* Button sits centered in the notch, just barely crossing the edge —
          fills with the brand gradient on hover instead of staying plain
          white, so the one interactive element in the notch actually reads
          as "premium" up close, not just flat and functional. */}
      <a
        href={item.applyUrl || '#'}
        target="_blank"
        rel="noreferrer"
        title="View listing"
        onClick={(e) => e.stopPropagation()}
        className="absolute -right-0.5 -top-0.5 z-10 flex h-10 w-10 items-center justify-center rounded-full border border-white/70 bg-white/95 text-[#3a3a38] shadow-[0_6px_16px_-6px_rgba(40,50,30,0.35)] transition-all duration-300 group-hover:border-transparent group-hover:bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] group-hover:text-white group-hover:shadow-[0_10px_22px_-8px_rgba(101,89,227,0.65)]"
      >
        {icons.expand}
      </a>

      {/* Header: logo + role + org */}
      <div className="relative flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-3">
          {showLogo ? (
            <img
              src={item.logoUrl}
              alt={item.organization}
              className="h-11 w-11 shrink-0 rounded-xl border border-white/70 bg-[linear-gradient(160deg,#ffffff_0%,#f3f1fb_100%)] object-contain p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.85),0_6px_14px_-8px_rgba(40,30,80,0.3)]"
              onError={() => setLogoFailed(true)}
            />
          ) : (
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[linear-gradient(160deg,#2a2a2a_0%,#121212_100%)] text-sm font-black text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.15),0_6px_14px_-8px_rgba(0,0,0,0.5)]">
              {(item.organization || item.title).charAt(0).toUpperCase()}
            </div>
          )}
          <div className="min-w-0">
            <p title={item.title} className="line-clamp-2 break-words text-[14.5px] font-black leading-tight tracking-tight transition-colors duration-300 group-hover:text-[#4b3fa8]">{item.title}</p>
            <p title={[item.organization, locationLabel].filter(Boolean).join(' · ')} className="truncate text-[12px] font-semibold text-[#9a9a97]">{[item.organization, locationLabel].filter(Boolean).join(' · ')}</p>
            {matched && (
              <span className="mt-1.5 inline-flex w-fit items-center gap-1 rounded-full bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] px-2.5 py-1 text-[10px] font-black uppercase tracking-wide text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.3),0_6px_14px_-6px_rgba(101,89,227,0.5)]">
                <svg viewBox="0 0 24 24" fill="currentColor" className="h-2.5 w-2.5"><path d="M12 2l2.2 6.8H21l-5.6 4.1 2.2 6.9L12 15.7 6.4 19.8l2.2-6.9L3 8.8h6.8z" /></svg>
                Matches you
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Info pill: deadline + skills + posted, each on their own row */}
      <div className="relative mt-3 flex flex-col gap-2.5 rounded-[16px] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.6)_0%,rgba(255,255,255,0.35)_100%)] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)] transition group-hover:bg-[linear-gradient(180deg,rgba(255,255,255,0.78)_0%,rgba(255,255,255,0.5)_100%)]">
        <div className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[linear-gradient(135deg,#f2f0fd_0%,#e8ecff_100%)] text-[#5c4fd8]">{icons.calendarLg}</span>
          <p className="truncate text-[12.5px] font-black leading-tight">{deadlineLabel ? `Apply by ${deadlineLabel}` : 'Rolling applications'}</p>
        </div>

        {item.description && (
          <div className="group/desc flex items-center gap-2 pl-9">
            <span className="shrink-0 text-[9.5px] font-black uppercase tracking-wide text-[#9a9a97]">Description</span>
            {/* Hover-only text/behavior doesn't exist on touch devices, so
                this is now also a real tap target: onClick toggles
                `showDescription`, which the pop-out below responds to in
                addition to (not instead of) the CSS :hover reveal. The
                label itself swaps between "Hover to preview" and "Tap to
                preview" based on the (hover: hover) media feature, since
                that's a more reliable signal than screen width for whether
                a pointing device is actually available. */}
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setShowDescription((open) => !open); }}
              aria-expanded={showDescription}
              className="inline-flex items-center gap-1 text-[10.5px] font-bold text-[#5c4fd8]/80"
            >
              {icons.info}
              <span className="hidden [@media(hover:hover)]:inline">Hover to preview</span>
              <span className="inline [@media(hover:hover)]:hidden">Tap to preview</span>
            </button>

            {/* Description pop-out: this row's own hover (`group/desc`)
                drives it on devices that support hover, and the
                `showDescription` tap-toggle above drives it on touch
                devices — it still fills the same pill footprint as before
                (`inset-0` resolves against the pill container above, the
                nearest *positioned* ancestor; this row itself is left
                unpositioned in flow so it doesn't become that container).
                The open/closed state is one exclusive branch below rather
                than a base "pointer-events-none/opacity-0/…" plus a
                same-specificity "pointer-events-auto/opacity-100/…"
                tacked on top — two plain (non-variant) utility classes for
                the same property have no reliable winner by source order
                alone, which is exactly why the tap-to-open version of this
                wasn't actually becoming interactive on phones (pointer
                events kept resolving to "none", so nothing inside —
                scrolling, the close button — ever received a touch). The
                `group-hover/desc:` variants are safe left as-is: the
                `:hover` pseudo-class gives them higher specificity, so
                they still correctly win on hover-capable devices. */}
            <div
              onClick={(e) => e.stopPropagation()}
              className={`absolute inset-0 z-20 flex origin-center flex-col gap-1.5 overflow-hidden rounded-[16px] border border-white/80 bg-[linear-gradient(165deg,rgba(255,255,255,0.98)_0%,rgba(250,248,255,0.96)_100%)] p-3.5 shadow-[inset_0_1.5px_0_rgba(255,255,255,0.95),0_20px_40px_-16px_rgba(101,89,227,0.35)] ring-1 ring-[#7b62e8]/[0.14] transition-all duration-300 ease-out group-hover/desc:pointer-events-auto group-hover/desc:translate-y-0 group-hover/desc:scale-100 group-hover/desc:opacity-100 ${
                showDescription
                  ? 'pointer-events-auto translate-y-0 scale-100 opacity-100'
                  : 'pointer-events-none scale-95 -translate-y-1 opacity-0'
              }`}
            >
              <p className="flex shrink-0 items-center justify-between gap-1.5 text-[9.5px] font-black uppercase tracking-wide text-[#7b62e8]">
                <span className="flex items-center gap-1.5">
                  {icons.info}
                  Description
                </span>
                {/* Only needed on touch — there's no hover-out to close the
                    pop-out with, so it needs its own explicit dismiss.
                    Hidden on hover-capable devices, where mousing away
                    already closes it. */}
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setShowDescription(false); }}
                  aria-label="Close preview"
                  className="-m-1 hidden h-5 w-5 shrink-0 items-center justify-center rounded-full text-[#9a9a97] transition hover:text-[#4a4a48] [@media(hover:none)]:flex"
                >
                  {icons.close}
                </button>
              </p>
              <div className="custom-scroll min-h-0 flex-1 overflow-y-auto pr-1 text-[11.5px] font-semibold leading-relaxed text-[#4a4a48]">
                {item.description}
              </div>
            </div>
          </div>
        )}

        {(item.duration || eligibleYearsLabel) && (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pl-9">
            {item.duration && (
              <span className="text-[10.5px] font-semibold text-[#6a6a68]">
                <span className="font-black uppercase tracking-wide text-[#9a9a97]">Duration </span>{item.duration}
              </span>
            )}
            {eligibleYearsLabel && (
              <span className="text-[10.5px] font-semibold text-[#6a6a68]">
                <span className="font-black uppercase tracking-wide text-[#9a9a97]">Eligible </span>{eligibleYearsLabel}
              </span>
            )}
          </div>
        )}

        {postedLabel && (
          <div className="flex items-center gap-2 pl-9">
            <span className="shrink-0 text-[9.5px] font-black uppercase tracking-wide text-[#9a9a97]">Posted</span>
            <span className="text-[10.5px] font-semibold text-[#6a6a68]">{postedLabel}</span>
          </div>
        )}
      </div>

      {/* Bottom action row: status, save, apply */}
      <div className="relative mt-3 flex items-center gap-2">
        <span className="inline-flex min-w-0 flex-1 items-center gap-2 rounded-2xl border border-white/60 bg-white/65 px-3 py-2 text-[11px] font-bold text-[#4a4a48] transition group-hover:bg-white/85">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[linear-gradient(160deg,#2a2a2a_0%,#121212_100%)] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.15)]">{item.isRemote ? icons.globe : icons.pin}</span>
          <span title={locationLabel} className="min-w-0 flex-1 truncate">{locationLabel}</span>
        </span>
        <button
          type="button"
          disabled={exiting}
          title={applied ? 'Disconnect — move back to its category' : 'Mark as applied'}
          onClick={(e) => { e.stopPropagation(); onToggleApplied && onToggleApplied(item); }}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border transition-all duration-300 ${
            exiting
              ? 'scale-125 border-transparent bg-[linear-gradient(160deg,#2a2a2a_0%,#121212_100%)] text-white shadow-[0_8px_18px_-8px_rgba(0,0,0,0.5)]'
              : applied
                ? 'border-transparent bg-[linear-gradient(160deg,#2a2a2a_0%,#121212_100%)] text-white shadow-[0_8px_18px_-8px_rgba(0,0,0,0.5)] hover:brightness-125'
                : 'border-white/60 bg-white/65 text-[#5a5a58] hover:bg-white'
          }`}
        >
          {exiting ? icons.check : applied ? icons.close : icons.check}
        </button>
        <button
          type="button"
          title={saved ? 'Remove from saved' : 'Save'}
          onClick={(e) => { e.stopPropagation(); onToggleSaved && onToggleSaved(item); }}
          onMouseEnter={() => setSaveHovered(true)}
          onMouseLeave={() => setSaveHovered(false)}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border transition-all duration-300 ${
            saved
              ? 'border-transparent bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-white shadow-[0_8px_18px_-8px_rgba(101,89,227,0.6)] hover:brightness-110'
              : 'border-white/60 bg-white/65 text-[#5a5a58] hover:bg-white'
          }`}
        >
          {saved && saveHovered ? icons.close : icons.bookmark}
        </button>
      </div>
    </div>
    </>
  );
}

// Memoized so toggling one card's saved state (or an unrelated re-render of
// the list it lives in) doesn't force every other card on screen to
// re-render too — each card only re-renders when its own props actually
// change.
const OpportunityCardMemo = React.memo(OpportunityCard);

function OpportunityCardSkeleton() {
  return (
    <div className="flex animate-pulse flex-col rounded-[22px] border border-white/70 bg-white/60 p-4">
      <div className="flex items-center gap-3">
        <div className="h-11 w-11 shrink-0 rounded-xl bg-[#e7e7e2]" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-2/3 rounded-full bg-[#e7e7e2]" />
          <div className="h-2.5 w-1/2 rounded-full bg-[#eeeeea]" />
        </div>
      </div>
      <div className="mt-3 h-16 rounded-[16px] bg-[#f1f1ee]" />
      <div className="mt-3 h-8 rounded-full bg-[#eeeeea]" />
    </div>
  );
}

// ---------- sidebar + content pane (shared by Discover and Career AI) ----------

// Every category (and "For You") is derived client-side from ONE fetch of
// the whole active opportunities table, cached under this key — see the
// note above the fetch effect below for why this replaced a per-category
// fetch-on-click design.
const OPPORTUNITIES_CACHE_KEY = 'discover:opportunities:all';

// How long a cached snapshot is trusted before a background refetch is
// triggered (see the fetch effect below) -- long enough that switching
// categories/tabs, or a quick reload, never re-hits the network, but short
// enough that a long-lived tab picks up new listings from the daily
// ingestion runs (see backend/app/ingestion/) within one session, without
// requiring a manual sessionStorage clear or tab close.
const OPPORTUNITIES_CACHE_TTL_MS = 15 * 60 * 1000; // 15 minutes

// Wraps localCache's plain get/set with a fetchedAt timestamp, scoped to
// just this one cache key -- every OTHER use of getCache/setCache in this
// codebase (Profile Analysis, Career Roadmap, Career Simulation, AI Coach --
// see localCache.js's own module docstring) intentionally has NO expiry:
// that data only changes via an explicit user action (generate roadmap,
// re-analyze, ...), so "never refetch until a mutation writes a new value"
// is correct there. Opportunities are different -- they change on their own,
// via a backend cron job the user has no button for -- so only this one
// cache gets a TTL, not the shared helper itself.
function readOpportunitiesCache() {
  const entry = getCache(OPPORTUNITIES_CACHE_KEY);
  if (entry === undefined) return undefined;
  // Back-compat: a session that cached the old plain-array shape (written
  // before this TTL was added) is treated as maximally stale -- fetchedAt=0
  // -- so it revalidates in the background on next visit instead of being
  // silently trusted forever under the new shape's assumptions.
  if (Array.isArray(entry)) return { rows: entry, fetchedAt: 0 };
  return entry;
}

function writeOpportunitiesCache(rows) {
  setCache(OPPORTUNITIES_CACHE_KEY, { rows, fetchedAt: Date.now() });
}

function SidebarContentBody({ items, sectionLabel, initialKey, mode, profile, savedIds, onToggleSaved, appliedIds, onToggleApplied, pendingAppliedIds, locked = false }) {
  const [active, setActive] = useState(() => {
    const hash = window.location.hash.replace('#', '');
    if (hash && items.some((item) => item.key === hash)) {
      return hash;
    }
    return initialKey;
  });
  // Hydrated synchronously from `localCache` via lazy useState initializers
  // — same pattern as the Career AI dashboards (see e.g.
  // ProfileAnalysisDashboard.jsx) — so a revisit, or even a full page
  // reload within the session, shows every category instantly with zero
  // network calls.
  const [allOpportunities, setAllOpportunities] = useState(() => (mode === 'opportunities' ? readOpportunitiesCache()?.rows || [] : []));
  const [opportunitiesStatus, setOpportunitiesStatus] = useState(() => {
    if (mode !== 'opportunities') return 'ready';
    return readOpportunitiesCache() ? 'ready' : 'loading';
  });
  const [opportunitiesError, setOpportunitiesError] = useState('');
  // "For You" upgrade: the FastAPI hybrid recommendation engine (semantic +
  // keyword retrieval, ranked by skill/interest/role/freshness — see
  // backend/app/services/recommendation_service.py) replaces the plain
  // client-side tag-overlap sort below once it resolves. `null` means "not
  // fetched yet" (distinct from an empty, successfully-fetched list).
  const [forYouRecommendations, setForYouRecommendations] = useState(null);
  const [forYouStatus, setForYouStatus] = useState('idle'); // idle | ready | error
  const forYouFetchStarted = useRef(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  // Hackathon-only filters (remote/on-site, an apply-by window, and a
  // specific location) — kept local to this tab rather than added to the
  // shared header every opportunity category uses, since only Hackathons
  // was asked for these.
  const [hackathonLocationType, setHackathonLocationType] = useState('all'); // all | remote | onsite
  const [hackathonDateFilter, setHackathonDateFilter] = useState('all'); // all | 7 | 30 | 90 (days until deadline)
  const [hackathonLocation, setHackathonLocation] = useState('all');
  const searchInputRef = useRef(null);
  const contentScrollRef = useRef(null);
  const activeItem = items.find((c) => c.key === active) || items[0];

  useEffect(() => {
    if (searchOpen) searchInputRef.current?.focus();
  }, [searchOpen]);

  // Reset scroll to the top whenever the active tab changes, so switching
  // tools always opens at the top instead of wherever the previous tab was
  // scrolled to. Done via a ref + scrollTop rather than remounting the pane
  // (e.g. a `key={active}` on the container) — remounting would also tear
  // down and re-fetch each dashboard's own state on every switch, which is
  // exactly the "lag every time I click between tabs" symptom this is
  // fixing, not causing.
  useEffect(() => {
    if (contentScrollRef.current) contentScrollRef.current.scrollTop = 0;
  }, [active]);

  // ONE fetch for the whole Discover section, not one per category. This
  // used to fetch per-category on first visit to each tab — meaning a fast
  // first pass through Programs -> Internships -> Hackathons -> Open
  // Source -> ... fired a fresh network request on every single click, and
  // that per-click network latency was the lag, not a rendering problem.
  // `loadOpportunities()` with no category argument already returns every
  // active listing (it's the same query "For You" always used); every
  // other category's list is now just a client-side `.filter(...)` over
  // that one array below, so switching categories is a pure in-memory
  // operation with zero network calls after this single fetch resolves —
  // including the very first time you visit each category, not just on a
  // revisit.
  useEffect(() => {
    if (mode !== 'opportunities') return;
    const cached = readOpportunitiesCache();
    // A fresh-enough cache: the lazy useState initializers above already
    // hydrated `allOpportunities` from it with zero network calls, and
    // there's nothing to do here. A stale (or missing) one falls through
    // and fetches below -- but if there's SOME cached data, however stale,
    // it's already on screen (opportunitiesStatus was set to 'ready' by the
    // initializer) while this refetch happens quietly in the background, so
    // a long-lived tab picks up newly-ingested opportunities (e.g. a daily
    // Devpost/Devfolio run) without ever showing a loading spinner over
    // content that's already there -- only a tab with NO cache at all sees
    // 'loading'.
    if (cached && Date.now() - cached.fetchedAt < OPPORTUNITIES_CACHE_TTL_MS) return;
    let cancelled = false;
    (async () => {
      try {
        const rows = await loadOpportunities();
        if (cancelled) return;
        setAllOpportunities(rows);
        setOpportunitiesStatus('ready');
        writeOpportunitiesCache(rows);
      } catch (error) {
        if (cancelled) return;
        // A background revalidation failing is not the same as a first
        // load failing: if there's already-cached data on screen, keep
        // showing it rather than replacing it with the error state over a
        // single transient refresh failure (e.g. a network blip).
        if (cached) return;
        setOpportunitiesError(error.message || 'Failed to load listings.');
        setOpportunitiesStatus('error');
      }
    })();
    return () => { cancelled = true; };
  }, [mode]);

  // Fired only on first visit to the "For You" tab this session, and only
  // once (guarded by the ref below, not state — setting state synchronously
  // in an effect body just to mark "fetch started" trips the react-hooks
  // set-state-in-effect rule for no benefit, since nothing here needs to
  // render a distinct "loading" state). Runs independently of the base
  // `allOpportunities` fetch above — the backend hydrates its own
  // opportunity rows from the ranked candidate ids, so this adds no latency
  // to any other tab and doesn't wait on that fetch either. On failure it
  // just leaves forYouStatus at 'error'; the listings computation below
  // silently keeps using the client-side tag-overlap sort in that case, so
  // there's no separate error UI to wire for this — same graceful-fallback
  // shape as the rest of this component.
  useEffect(() => {
    if (mode !== 'opportunities') return;
    if (active !== 'for-you') return;
    if (forYouFetchStarted.current) return;
    forYouFetchStarted.current = true;
    let cancelled = false;
    (async () => {
      try {
        const items = await loadForYouRecommendations();
        if (cancelled) return;
        setForYouRecommendations(items);
        setForYouStatus('ready');
      } catch {
        if (cancelled) return;
        setForYouStatus('error');
      }
    })();
    return () => { cancelled = true; };
  }, [mode, active]);

  // Always hits the network — a previous load just failed, so there's
  // nothing trustworthy in the cache to reuse.
  const retryOpportunities = async () => {
    setOpportunitiesStatus('loading');
    setOpportunitiesError('');
    try {
      const rows = await loadOpportunities();
      setAllOpportunities(rows);
      setOpportunitiesStatus('ready');
      writeOpportunitiesCache(rows);
    } catch (error) {
      setOpportunitiesError(error.message || 'Failed to load listings.');
      setOpportunitiesStatus('error');
    }
  };

  const matchTags = new Set([...(profile?.currentSkills || []), ...(profile?.careerInterests || [])].map((t) => t.toLowerCase()));
  const scoreOf = (item) => (item.tags || []).filter((t) => matchTags.has(t.toLowerCase())).length;

  let listings;
  if (active === 'applied') {
    // Its own pseudo-category, same idea as 'for-you'/'all': pulled from
    // every real category by id rather than filtered by `item.category`.
    listings = allOpportunities.filter((item) => appliedIds?.has(item.id));
  } else if (active === 'for-you' && forYouStatus === 'ready' && forYouRecommendations) {
    // Backend hybrid ranking available — use it as-is (already sorted by
    // score) instead of the client-side tag-overlap sort below.
    listings = forYouRecommendations;
    if (appliedIds && appliedIds.size > 0) {
      listings = listings.filter((item) => !appliedIds.has(item.id));
    }
  } else {
    listings = active === 'for-you' || active === 'all' ? allOpportunities : allOpportunities.filter((item) => item.category === active);
    // Marking an opportunity applied moves it out of every regular category
    // list and into the Applied tab above — same list, filtered by id,
    // rather than a separate query, so it moves the instant
    // `onToggleApplied` fires (see AppShell's optimistic `toggleApplied`)
    // with no extra network round trip.
    if (appliedIds && appliedIds.size > 0) {
      listings = listings.filter((item) => !appliedIds.has(item.id));
    }
    if (active === 'for-you') {
      // Not yet fetched, still loading, or the backend call failed — same
      // client-side tag-overlap sort this tab has always used, so "For You"
      // never looks broken or blank while/if the upgrade path is unavailable.
      listings = [...listings].sort((a, b) => scoreOf(b) - scoreOf(a));
    }
  }

  const query = searchQuery.trim().toLowerCase();
  if (query) {
    listings = listings.filter((item) => {
      const haystack = [item.title, item.organization, item.location, ...(item.tags || [])].filter(Boolean).join(' ').toLowerCase();
      return haystack.includes(query);
    });
  }

  const isHackathonsTab = active === 'hackathons';
  // Built from every hackathon (not just the currently-filtered list), so
  // picking a location never shrinks its own dropdown's other options.
  const hackathonLocationOptions = isHackathonsTab
    ? Array.from(new Set(
        allOpportunities
          .filter((o) => o.category === 'hackathons' && !o.isRemote && o.location)
          .map((o) => o.location)
      )).sort()
    : [];

  if (isHackathonsTab) {
    if (hackathonLocationType === 'remote') {
      listings = listings.filter((item) => item.isRemote);
    } else if (hackathonLocationType === 'onsite') {
      listings = listings.filter((item) => !item.isRemote);
    }
    if (hackathonLocation !== 'all') {
      listings = listings.filter((item) => item.location === hackathonLocation);
    }
    if (hackathonDateFilter !== 'all') {
      const days = Number(hackathonDateFilter);
      listings = listings.filter((item) => isWithinDeadlineWindow(item.deadline, days));
    }
  }
  const hackathonFiltersActive = isHackathonsTab && (hackathonLocationType !== 'all' || hackathonDateFilter !== 'all' || hackathonLocation !== 'all');
  const resetHackathonFilters = () => {
    setHackathonLocationType('all');
    setHackathonDateFilter('all');
    setHackathonLocation('all');
  };

  const isLoading = opportunitiesStatus === 'loading';
  const isError = opportunitiesStatus === 'error';

  // A touch of the FAQ section's warm-cream/lavender palette — its signature
  // purple-blue gradient in place of the lime green used elsewhere, since
  // green clashes with that theme. This component only ever renders as
  // Discover (mode: 'opportunities') or Career AI (mode: undefined), so the
  // accent applies the same way to both.
  const accentBadgeCls = 'bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-white shadow-[0_6px_14px_-6px_rgba(101,89,227,0.5)]';

  return (
    // A fixed 240px sidebar next to a flex-1 content pane worked at desktop
    // widths but left barely any room for the content pane on a phone (the
    // sidebar alone was wider than most of the viewport). Below lg this now
    // stacks: a horizontal scrollable pill bar for category switching sits
    // above the content pane instead of a vertical list beside it; the
    // original 240px sidebar returns unchanged at lg and up.
    <div className="relative flex min-h-0 flex-1 flex-col lg:flex-row">
    {/* `locked` (Career AI, pre-launch): everything below still renders and
        every tool still mounts, fetches, and works exactly as before -
        nothing here is deleted or disabled in code. This just visually
        dims/blurs it and blocks pointer events so it reads as "not live
        yet", with a small card explaining that on top. Flip `locked` to
        false at the call site once Career AI is ready to launch. */}
    <div className={`flex min-h-0 flex-1 flex-col gap-3 lg:flex-row lg:gap-5 transition-[filter,opacity] duration-300 ${locked ? 'pointer-events-none select-none opacity-[0.42] grayscale-[0.65] blur-[1.5px] saturate-[0.65]' : ''}`}>
      {/* Sidebar — desktop only. Stretches full height to match the content
          pane's bottom edge, like a proper pair of side-by-side cards. Every
          item in the CATEGORIES list must stay visible with no scrollbar no
          matter the viewport height, so instead of sitting at a fixed
          natural size (which got the last item or two clipped by this
          card's own overflow-hidden on shorter screens), each button below
          is flex-1 with min-h-0: together they always divide up exactly the
          height available, growing a bit on tall screens and shrinking
          gracefully on short ones, so all 9 are always fully on screen at
          once. */}
      <div className="hidden lg:flex lg:w-[240px] lg:min-h-0 lg:shrink-0 flex-col overflow-hidden rounded-[26px] border border-white/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.82)_0%,rgba(255,255,255,0.58)_100%)] p-3.5 shadow-[inset_0_1.5px_0_rgba(255,255,255,0.95),inset_0_0_0_1px_rgba(255,255,255,0.3),0_24px_48px_-24px_rgba(40,50,30,0.4)] backdrop-blur-2xl">
        <p className="shrink-0 px-2.5 pb-2.5 pt-1 text-[11.5px] font-bold uppercase tracking-[0.12em] text-[#9a9a97]">{sectionLabel}</p>
        <nav className="flex min-h-0 flex-1 flex-col gap-1.5">
          {items.map((c) => {
            const isActive = active === c.key;
            const muted = c.comingSoon && !isActive;
            return (
              <button
                key={c.key}
                type="button"
                onClick={() => { setActive(c.key); setSearchOpen(false); setSearchQuery(''); }}
                className={`group flex min-h-0 flex-1 items-center gap-3 rounded-2xl border px-3 py-1.5 text-left transition-all duration-200 ${
                  isActive
                    ? 'border-transparent bg-[#161616] text-white'
                    : muted
                      ? 'border-[#ece7fb] bg-[linear-gradient(135deg,#faf9ff_0%,#f6f3ff_100%)] text-[#4a4a48] hover:border-[#ddd4fb] hover:bg-[#f3efff]'
                      // Previous hover (bg-white/70) barely showed up against
                      // this panel's own near-white background — an opaque
                      // white fill, a visible border, and a soft lift/shadow
                      // instead make the hover state actually readable.
                      : 'border-transparent text-[#4a4a48] hover:-translate-y-[1px] hover:border-white/80 hover:bg-white hover:shadow-[0_10px_22px_-14px_rgba(40,50,30,0.4)]'
                }`}
              >
                <span
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-colors duration-200 ${
                    isActive ? 'bg-white/15 text-white' : muted ? 'bg-white text-[#7b62e8] shadow-[0_2px_6px_-2px_rgba(123,98,232,0.35)]' : 'bg-white/70 text-[#1a1a1a] group-hover:bg-[#f3efff] group-hover:text-[#5c4fd8]'
                  }`}
                >
                  {c.icon}
                </span>
                <span className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="block truncate text-[14px] font-bold leading-tight">{c.label}</span>
                  {c.comingSoon && (
                    <span
                      className={`inline-block w-fit rounded-full px-1.5 py-0.5 text-[9px] font-black uppercase tracking-wide ${
                        isActive ? 'bg-white/20 text-white' : 'bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-white'
                      }`}
                    >
                      Coming soon
                    </span>
                  )}
                </span>
                {c.featured && <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-black uppercase tracking-wide ${accentBadgeCls}`}>New</span>}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Category pills — mobile/tablet only */}
      <nav className="custom-scroll -mx-1 flex shrink-0 gap-2 overflow-x-auto px-1 pb-1 lg:hidden">
        {items.map((c) => {
          const isActive = active === c.key;
          const muted = c.comingSoon && !isActive;
          return (
            <button
              key={c.key}
              type="button"
              onClick={() => { setActive(c.key); setSearchOpen(false); setSearchQuery(''); }}
              className={`flex shrink-0 items-center gap-2 whitespace-nowrap rounded-full border px-4 py-2.5 text-[13px] font-bold transition ${
                isActive
                  ? 'border-black bg-[#161616] text-white'
                  : muted
                    ? 'border-[#ece7fb] bg-[linear-gradient(135deg,#faf9ff_0%,#f6f3ff_100%)] text-[#4a4a48]'
                    : 'border-white/70 bg-white/75 text-[#4a4a48] backdrop-blur-md'
              }`}
            >
              <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${isActive ? 'bg-white/15 text-white' : muted ? 'bg-white text-[#7b62e8]' : 'bg-white/70 text-[#1a1a1a]'}`}>
                {c.icon}
              </span>
              {c.label}
              {c.featured && <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[8px] font-black uppercase tracking-wide ${accentBadgeCls}`}>New</span>}
              {c.comingSoon && (
                <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[8px] font-black uppercase tracking-wide ${isActive ? 'bg-white/20 text-white' : 'bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-white'}`}>
                  Soon
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Content */}
      <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-[26px] border border-white/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.82)_0%,rgba(255,255,255,0.58)_100%)] p-4 sm:p-6 shadow-[inset_0_1.5px_0_rgba(255,255,255,0.95),inset_0_0_0_1px_rgba(255,255,255,0.3),0_24px_48px_-24px_rgba(40,50,30,0.4)] backdrop-blur-2xl">
        {/* A faint echo of the FAQ section's warm-peach + lavender corner
            glows, dialed way down so it reads as texture, not a redesign. */}
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -left-10 -top-10 h-40 w-40 rounded-full bg-[radial-gradient(circle,rgba(255,224,187,0.35)_0%,transparent_70%)]" />
          <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-[radial-gradient(circle,rgba(123,98,232,0.16)_0%,transparent_70%)] blur-2xl" />
        </div>
        <div className="relative flex shrink-0 flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#161616] text-white">{activeItem.icon}</span>
            <div className="min-w-0">
              <p className="truncate text-[16px] font-black tracking-tight">{activeItem.label}</p>
              {/* Same size/weight/color on every tab (Discover categories and
                  Career AI tools alike) so the subheading reads as one
                  consistent piece of UI rather than varying tab to tab —
                  sized up from the original 11.5px and no longer truncated,
                  since a one-line clamp was cutting off longer copy (like
                  Learning Hub's) before a reader could finish it. Still
                  dropped on the smallest screens, where it and the search
                  control would otherwise fight for the same row. */}
              <p className="hidden max-w-2xl text-[13.5px] font-semibold leading-snug text-[#5a5a58] sm:block">{activeItem.desc}</p>
            </div>
          </div>
          {mode === 'opportunities' && active !== 'learning-hub' && active !== 'certifications' && (
            <div className="flex items-center gap-2">
              {activeItem.featured && (
                <span
                  className={`shrink-0 overflow-hidden whitespace-nowrap rounded-full text-[10px] font-black uppercase tracking-wide transition-all duration-300 ease-out ${accentBadgeCls} ${
                    searchOpen ? 'max-w-0 px-0 py-1.5 opacity-0' : 'max-w-[160px] px-3 py-1.5 opacity-100'
                  }`}
                >
                  Recommended
                </span>
              )}
              <div
                className={`flex h-9 items-center overflow-hidden rounded-full border border-white/70 bg-white/85 shadow-[inset_0_1px_0_rgba(255,255,255,0.9)] backdrop-blur-md transition-[width] duration-300 ease-out ${
                  searchOpen ? 'w-44 sm:w-64' : 'w-9'
                }`}
              >
                <button
                  type="button"
                  onClick={() => setSearchOpen((o) => !o)}
                  title="Search"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[#3a3a38] transition hover:bg-white/80 hover:text-[#161616]"
                >
                  {icons.search}
                </button>
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={`Search ${activeItem.label.toLowerCase()}...`}
                  tabIndex={searchOpen ? 0 : -1}
                  className={`min-w-0 flex-1 bg-transparent pr-1 text-[12.5px] font-semibold text-[#1a1a1a] placeholder:text-[#b0b0ac] transition-opacity duration-200 focus:outline-none ${
                    searchOpen ? 'opacity-100 delay-100' : 'opacity-0'
                  }`}
                />
                <button
                  type="button"
                  title="Close search"
                  tabIndex={searchOpen ? 0 : -1}
                  onClick={() => { setSearchOpen(false); setSearchQuery(''); }}
                  className={`mr-1.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[#9a9a97] transition hover:bg-white hover:text-[#161616] ${
                    searchOpen ? 'opacity-100 delay-100' : 'pointer-events-none opacity-0'
                  }`}
                >
                  {icons.close}
                </button>
              </div>
            </div>
          )}
        </div>

        {mode === 'opportunities' && active === 'hackathons' && (
          <div className="relative mt-3 flex shrink-0 flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 rounded-full border border-white/70 bg-white/70 p-1 backdrop-blur-md">
              {[
                { key: 'all', label: 'All' },
                { key: 'remote', label: 'Remote' },
                { key: 'onsite', label: 'On-site' },
              ].map((opt) => (
                <button
                  key={opt.key}
                  type="button"
                  onClick={() => setHackathonLocationType(opt.key)}
                  className={`rounded-full px-3 py-1.5 text-[11.5px] font-bold transition ${
                    hackathonLocationType === opt.key ? 'bg-[#161616] text-white' : 'text-[#4a4a48] hover:bg-white'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <div className="relative">
              <select
                value={hackathonDateFilter}
                onChange={(e) => setHackathonDateFilter(e.target.value)}
                className="h-9 appearance-none rounded-full border border-white/70 bg-white/75 pl-3.5 pr-8 text-[11.5px] font-bold text-[#4a4a48] backdrop-blur-md transition hover:bg-white focus:outline-none"
              >
                <option value="all">Any date</option>
                <option value="7">Apply within 7 days</option>
                <option value="30">Apply within 30 days</option>
                <option value="90">Apply within 90 days</option>
              </select>
              <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[#9a9a97]">{icons.chevronDown}</span>
            </div>

            {hackathonLocationOptions.length > 0 && (
              <div className="relative">
                <select
                  value={hackathonLocation}
                  onChange={(e) => setHackathonLocation(e.target.value)}
                  className="h-9 max-w-[180px] appearance-none rounded-full border border-white/70 bg-white/75 pl-3.5 pr-8 text-[11.5px] font-bold text-[#4a4a48] backdrop-blur-md transition hover:bg-white focus:outline-none"
                >
                  <option value="all">All locations</option>
                  {hackathonLocationOptions.map((loc) => (
                    <option key={loc} value={loc}>{loc}</option>
                  ))}
                </select>
                <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[#9a9a97]">{icons.chevronDown}</span>
              </div>
            )}

            {hackathonFiltersActive && (
              <button
                type="button"
                onClick={resetHackathonFilters}
                className="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-[11.5px] font-bold text-[#7b62e8] transition hover:text-[#5c4fd8]"
              >
                {icons.close}
                Clear filters
              </button>
            )}
          </div>
        )}

        {mode === 'opportunities' && active === 'certifications' ? (
          // Shared header above (icon, title, subheading) stays, same as
          // every other tab — only the content below it is this catalog's
          // own explainer banner + track switcher + cards, not the plain
          // opportunity grid every other tab uses. The shared search box in
          // that header used to be a no-op here (it only ever filtered the
          // plain opportunity grid); searchQuery is now passed through so
          // it actually searches certifications across every domain.
          <CertificationsCatalog searchQuery={searchQuery} onClearSearch={() => setSearchQuery('')} />
        ) : mode === 'opportunities' && active === 'learning-hub' ? (
          // Shared header above (icon, title, subheading) stays, minus the
          // search box (hidden for this tab above) — Learning Hub is a
          // short, browsable grid of ~14 official platforms, not something
          // that needs searching. Below it, a clean grid of platform tiles
          // plus a floating info card, not the plain opportunity grid every
          // other tab uses.
          <Suspense fallback={<PaneLoadingFallback />}>
            <LearningJourney />
          </Suspense>
        ) : mode === 'opportunities' ? (
          <div ref={contentScrollRef} className="custom-scroll mt-3 min-h-0 flex-1 overflow-y-auto overflow-x-hidden pb-1 pr-2 pt-2">
            {isLoading && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => <OpportunityCardSkeleton key={i} />)}
              </div>
            )}
            {isError && (
              <div className="flex h-full flex-col items-center justify-center gap-2 rounded-[20px] border border-dashed border-white/70 bg-white/40 px-6 py-10 text-center">
                <p className="text-[12.5px] font-semibold text-[#b34747]">{opportunitiesError}</p>
                <button type="button" onClick={retryOpportunities} className="mt-1 rounded-full bg-[#161616] px-4 py-2 text-[12px] font-bold text-white transition hover:bg-[#2a2a2a]">Try again</button>
              </div>
            )}
            {!isLoading && !isError && listings.length === 0 && (query || hackathonFiltersActive) && (
              <div className="flex h-full flex-col items-center justify-center gap-2 rounded-[20px] border border-dashed border-white/70 bg-white/40 px-6 py-10 text-center">
                <span className="rounded-full bg-white/80 px-3 py-1 text-[10px] font-black uppercase tracking-wide text-[#7a7a76]">No matches</span>
                <p className="max-w-sm text-[12.5px] font-semibold text-[#7a7a76]">
                  {query ? `Nothing matches "${searchQuery}" in ${activeItem.label}.` : 'No hackathons match these filters.'} Try {query ? 'a different keyword' : 'different filters'}.
                </p>
                <button
                  type="button"
                  onClick={() => { setSearchQuery(''); resetHackathonFilters(); }}
                  className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-[#161616] px-4 py-2 text-[12px] font-bold text-white transition hover:bg-[#2a2a2a]"
                >
                  {query && hackathonFiltersActive ? 'Clear search & filters' : query ? 'Clear search' : 'Clear filters'}
                </button>
              </div>
            )}
            {!isLoading && !isError && listings.length === 0 && !query && active === 'applied' && (
              <div className="flex h-full flex-col items-center justify-center gap-2 rounded-[20px] border border-dashed border-white/70 bg-white/40 px-6 py-10 text-center">
                <span className="rounded-full bg-white/80 px-3 py-1 text-[10px] font-black uppercase tracking-wide text-[#7a7a76]">Nothing here yet</span>
                <p className="max-w-sm text-[12.5px] font-semibold text-[#7a7a76]">Mark a listing as applied from any category and it'll move here — tap the checkmark on a card.</p>
              </div>
            )}
            {!isLoading && !isError && listings.length === 0 && !query && !hackathonFiltersActive && active !== 'applied' && (
              <div className="flex h-full flex-col items-center justify-center gap-2 rounded-[20px] border border-dashed border-white/70 bg-white/40 px-6 py-10 text-center">
                <span className={`rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-wide ${accentBadgeCls}`}>Nothing yet</span>
                <p className="max-w-sm text-[12.5px] font-semibold text-[#7a7a76]">No open {activeItem.label.toLowerCase()} right now. Check back soon, or complete your profile so we can match you the moment new ones land.</p>
                <a href="/profile" className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-[#161616] px-4 py-2 text-[12px] font-bold text-white transition hover:bg-[#2a2a2a]">Complete your profile</a>
              </div>
            )}
            {!isLoading && !isError && listings.length > 0 && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {listings.map((item) => (
                  <OpportunityCardMemo key={item.id} item={item} matched={scoreOf(item) > 0} saved={savedIds?.has(item.id)} onToggleSaved={onToggleSaved} applied={active === 'applied'} onToggleApplied={onToggleApplied} exiting={pendingAppliedIds?.has(item.id)} />
                ))}
              </div>
            )}
          </div>
        ) : (
          // Same "mount once, toggle visibility" pattern as the top-level
          // Dashboard/Discover/Career AI/Profile switch above — each tool
          // dashboard fetches its own data on mount and owns its own state;
          // conditionally rendering only the active one (the old approach)
          // meant switching away unmounted it, so switching *back* to a tool
          // you'd already visited unmounted-then-remounted it from scratch —
          // a fresh network fetch and loading skeleton on every click, which
          // is exactly the "lag on back-and-forth switching" this fixes.
          // Keeping all four mounted and only toggling opacity/pointer-events
          // means a revisit is instant because nothing was ever torn down.
          <Suspense fallback={<PaneLoadingFallback />}>
          <div className="relative mt-3 min-h-0 flex-1">
            <div
              ref={active === 'profile-analysis' ? contentScrollRef : undefined}
              aria-hidden={active !== 'profile-analysis'}
              className={`custom-scroll absolute inset-0 transform-gpu overflow-y-auto overflow-x-hidden pb-1 pr-2 pt-2 ${
                active === 'profile-analysis' ? '' : 'pointer-events-none opacity-0'
              }`}
            >
              <ProfileAnalysisDashboardMemo />
            </div>
            <div
              ref={active === 'career-roadmap' ? contentScrollRef : undefined}
              aria-hidden={active !== 'career-roadmap'}
              className={`custom-scroll absolute inset-0 transform-gpu overflow-y-auto overflow-x-hidden pb-1 pr-2 pt-2 ${
                active === 'career-roadmap' ? '' : 'pointer-events-none opacity-0'
              }`}
            >
              <CareerRoadmapDashboardMemo profile={profile} />
            </div>
            <div
              ref={active === 'career-simulation' ? contentScrollRef : undefined}
              aria-hidden={active !== 'career-simulation'}
              className={`custom-scroll absolute inset-0 transform-gpu overflow-y-auto overflow-x-hidden pb-1 pr-2 pt-2 ${
                active === 'career-simulation' ? '' : 'pointer-events-none opacity-0'
              }`}
            >
              <CareerSimulationDashboardMemo profile={profile} />
            </div>
            <div
              ref={active === 'ai-coach' ? contentScrollRef : undefined}
              aria-hidden={active !== 'ai-coach'}
              className={`custom-scroll absolute inset-0 transform-gpu overflow-y-auto overflow-x-hidden pb-1 pr-2 pt-2 ${
                active === 'ai-coach' ? '' : 'pointer-events-none opacity-0'
              }`}
            >
              <CareerCoachDashboardMemo profile={profile} onNavigateTab={setActive} />
            </div>
            {!['profile-analysis', 'career-roadmap', 'career-simulation', 'ai-coach'].includes(active) && (
              <div ref={contentScrollRef} className="custom-scroll absolute inset-0 flex transform-gpu flex-col items-center justify-center gap-2 overflow-y-auto overflow-x-hidden rounded-[20px] border border-dashed border-white/70 bg-white/40 px-6 py-10 text-center">
                <span className={`rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-wide ${accentBadgeCls}`}>Coming soon</span>
                <p className="max-w-sm text-[12.5px] font-semibold text-[#7a7a76]">We're building out {activeItem.label.toLowerCase()}. Check back soon, or complete your profile so we can put it to work for you.</p>
                <a href="/profile" className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-[#161616] px-4 py-2 text-[12px] font-bold text-white transition hover:bg-[#2a2a2a]">Complete your profile</a>
              </div>
            )}
          </div>
          </Suspense>
        )}
      </div>
    </div>

    {locked && (
      <div className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center p-4 sm:p-8">
        <div className="pointer-events-auto flex max-w-sm flex-col items-center gap-3 rounded-[24px] border border-white/80 bg-[linear-gradient(165deg,rgba(255,255,255,0.97)_0%,rgba(250,248,255,0.92)_100%)] px-6 py-7 text-center shadow-[inset_0_1.5px_0_rgba(255,255,255,0.95),0_28px_60px_-20px_rgba(40,50,30,0.45)] ring-1 ring-[#7b62e8]/[0.12] ring-offset-2 ring-offset-white/40 backdrop-blur-2xl">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-white shadow-[0_10px_24px_-8px_rgba(101,89,227,0.6)]">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
              <rect x="5" y="11" width="14" height="9" rx="2.5" />
              <path d="M8 11V7a4 4 0 0 1 8 0v4" />
            </svg>
          </span>
          <span className="w-fit rounded-full bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] px-3 py-1 text-[10px] font-black uppercase tracking-wide text-white">Coming soon</span>
          <p className="text-[16px] font-black tracking-tight text-[#1a1a1a]">Career AI isn't live yet</p>
          <p className="text-[12.5px] font-semibold leading-snug text-[#5a5a58]">We're still polishing this experience behind the scenes. It'll switch on for everyone in an upcoming update - check back soon.</p>
        </div>
      </div>
    )}
    </div>
  );
}

// ---------- saved (bookmarked) opportunities, across every category ----------

// Purely presentational — AppShell owns the fetch + optimistic save/unsave
// state (savedItems) and passes it straight in. This pane used to fetch its
// own copy keyed off the saved-ids set, but that refetch could race an
// in-flight unsave's DELETE and briefly show a just-removed card again.
// Deriving the list straight from shared state instead of a parallel fetch
// makes "unsave" instant and correct everywhere, including here.
function SavedBody({ items, status, onRetry, onToggleSaved, profile, appliedIds, onToggleApplied, onBrowseDiscover }) {
  const matchTags = new Set([...(profile?.currentSkills || []), ...(profile?.careerInterests || [])].map((t) => t.toLowerCase()));
  const scoreOf = (item) => (item.tags || []).filter((t) => matchTags.has(t.toLowerCase())).length;

  const isLoading = status === 'loading';
  const isError = status === 'error';

  return (
    <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-[26px] border border-white/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.82)_0%,rgba(255,255,255,0.58)_100%)] p-6 shadow-[inset_0_1.5px_0_rgba(255,255,255,0.95),inset_0_0_0_1px_rgba(255,255,255,0.3),0_24px_48px_-24px_rgba(40,50,30,0.4)] backdrop-blur-2xl">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-10 -top-10 h-40 w-40 rounded-full bg-[radial-gradient(circle,rgba(255,224,187,0.35)_0%,transparent_70%)]" />
        <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-[radial-gradient(circle,rgba(123,98,232,0.16)_0%,transparent_70%)] blur-2xl" />
      </div>
      <div className="relative flex shrink-0 items-center gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#161616] text-white">{icons.bookmark}</span>
        <div>
          <p className="text-[16px] font-black tracking-tight">Saved</p>
          <p className="text-[11.5px] font-medium text-[#7a7a76]">Every internship, program, hackathon, and opportunity you've bookmarked.</p>
        </div>
      </div>

      <div className="custom-scroll mt-3 min-h-0 flex-1 overflow-y-auto overflow-x-hidden pb-1 pr-2 pt-2">
        {isLoading && (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(300px,360px))] gap-4">
            {Array.from({ length: 4 }).map((_, i) => <OpportunityCardSkeleton key={i} />)}
          </div>
        )}
        {isError && (
          <div className="flex h-full flex-col items-center justify-center gap-2 rounded-[20px] border border-dashed border-white/70 bg-white/40 px-6 py-10 text-center">
            <p className="text-[12.5px] font-semibold text-[#b34747]">Failed to load your saved items.</p>
            <button type="button" onClick={onRetry} className="mt-1 rounded-full bg-[#161616] px-4 py-2 text-[12px] font-bold text-white transition hover:bg-[#2a2a2a]">Try again</button>
          </div>
        )}
        {!isLoading && !isError && items.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-2 rounded-[20px] border border-dashed border-white/70 bg-white/40 px-6 py-10 text-center">
            <span className="rounded-full bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] px-3 py-1 text-[10px] font-black uppercase tracking-wide text-white shadow-[0_6px_14px_-6px_rgba(101,89,227,0.5)]">Nothing saved yet</span>
            <p className="max-w-sm text-[12.5px] font-semibold text-[#7a7a76]">Tap the bookmark icon on any card in Discover to save it here — internships, programs, hackathons, open source, and more.</p>
            {/* This app switches panes with client-side view state
                (goToView), not real routes — a plain <a href="/discover">
                pointed at a path the router has no page for and either
                404'd or reloaded the whole app. A button that calls back
                into goToView('discover') switches panes the same way the
                Discover tab in the header does. */}
            <button type="button" onClick={onBrowseDiscover} className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-[#161616] px-4 py-2 text-[12px] font-bold text-white transition hover:bg-[#2a2a2a]">Browse Discover</button>
          </div>
        )}
        {!isLoading && !isError && items.length > 0 && (
          // This pane isn't docked next to the Categories sidebar the way
          // Discover's grid is, so it has a lot more raw width to work
          // with — a plain 1/2/3-column split (same breakpoints as
          // Discover) was stretching each column, and each card with it,
          // to fill that extra space instead of staying the same fixed
          // card size used everywhere else. auto-fill with a capped
          // minmax keeps every card that same fixed width and just adds
          // more columns (or empty trailing space) as the pane gets wider.
          <div className="grid grid-cols-[repeat(auto-fill,minmax(300px,360px))] gap-4">
            {items.map((item) => (
              <OpportunityCardMemo key={item.id} item={item} matched={scoreOf(item) > 0} saved onToggleSaved={onToggleSaved} applied={appliedIds?.has(item.id)} onToggleApplied={onToggleApplied} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------- profile form primitives ----------

function FormField({ label, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] font-bold text-[#4a4a48]">{label}</span>
      {children}
    </label>
  );
}

function FormInput(props) {
  return (
    <input
      {...props}
      className="h-10 w-full rounded-[14px] border border-white/70 bg-white/60 px-3.5 text-[14.5px] font-medium text-[#1a1a1a] outline-none transition placeholder:text-[#9a9a97] focus:border-[#161616]/30 focus:bg-white/85"
    />
  );
}

function FormTextArea(props) {
  return (
    <textarea
      {...props}
      className="min-h-[58px] w-full resize-none rounded-[14px] border border-white/70 bg-white/60 px-3.5 py-2.5 text-[14.5px] font-medium leading-5 text-[#1a1a1a] outline-none transition placeholder:text-[#9a9a97] focus:border-[#161616]/30 focus:bg-white/85"
    />
  );
}

function FormSelect({ value, onChange, placeholder, options }) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full appearance-none rounded-[14px] border border-white/70 bg-white/60 px-3.5 pr-9 text-[14.5px] font-medium text-[#1a1a1a] outline-none transition focus:border-[#161616]/30 focus:bg-white/85"
      >
        <option value="">{placeholder}</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[#7a7a76]">{icons.chevronDown}</span>
    </div>
  );
}

function FormChip({ active, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-1.5 text-[13px] font-bold transition ${
        active ? 'border-[#161616]/10 bg-[#161616] text-white' : 'border-white/70 bg-white/75 backdrop-blur-md text-[#4a4a48] hover:bg-white/80'
      }`}
    >
      {children}
    </button>
  );
}

// Uploads immediately on selection (rather than deferring to "Save changes")
// so a failed upload surfaces right away instead of at save time, and so
// draft.resumeUrl — the storage path, not a viewable link — is always in
// sync with what's actually in the bucket.
function ResumeField({ draft, onField }) {
  const [fileName, setFileName] = useState('');
  const [state, setState] = useState('idle'); // idle | uploading | error
  const [error, setError] = useState('');

  const handleSelect = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const validationError = validateResumeFile(file);
    if (validationError) {
      setState('error');
      setError(validationError);
      event.target.value = '';
      return;
    }

    setFileName(file.name);
    setState('uploading');
    setError('');
    try {
      const { path } = await uploadResume(file);
      onField('resumeUrl', path);
      setState('idle');
    } catch (uploadError) {
      setState('error');
      setError(uploadError.message || 'Upload failed.');
    }
  };

  const handleView = async () => {
    if (!draft.resumeUrl) return;
    try {
      const url = await getResumeSignedUrl(draft.resumeUrl);
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch {
      setState('error');
      setError('Could not open resume.');
    }
  };

  return (
    <FormField label="Resume">
      <div className="flex items-center gap-2">
        <label className="flex h-10 min-w-0 flex-1 cursor-pointer items-center gap-2 rounded-[14px] border border-white/70 bg-white/75 backdrop-blur-md py-1 pl-3.5 pr-1.5 text-[14.5px] text-[#161616] transition hover:bg-white/80">
          <span className={`min-w-0 flex-1 truncate ${fileName || draft.resumeUrl ? 'text-[#161616]' : 'text-[#9a9a97]'}`}>
            {state === 'uploading' ? 'Uploading…' : fileName || (draft.resumeUrl ? 'Resume on file — choose a file to replace it' : 'Upload PDF or DOCX (max 5MB)')}
          </span>
          <span className="shrink-0 whitespace-nowrap rounded-full bg-white px-2.5 py-1 text-[12.5px] font-bold text-[#6a5ae0] shadow-[0_1px_3px_rgba(0,0,0,0.08)]">Browse</span>
          <input type="file" accept=".pdf,.doc,.docx" className="hidden" onChange={handleSelect} disabled={state === 'uploading'} />
        </label>
        {draft.resumeUrl && (
          <button type="button" onClick={handleView} className="shrink-0 rounded-[14px] border border-white/70 bg-white/75 backdrop-blur-md px-3 py-2.5 text-[13.5px] font-bold text-[#4a4a48] transition hover:bg-white/80">
            View
          </button>
        )}
      </div>
      {state === 'error' && <p className="mt-1.5 text-[12.5px] font-semibold text-red-600">{error}</p>}
    </FormField>
  );
}

// Per-experience skills — a finer-grained signal than the profile-level
// currentSkills list, scoped to what was actually used in that one role.
// Reuses the same skillOptions pool for consistency, plus a free-text add.
function ExperienceSkillsField({ experience, onExperienceField }) {
  const [customSkill, setCustomSkill] = useState('');
  const skillsUsed = experience.skillsUsed || [];
  const visibleOptions = [...skillOptions, ...skillsUsed.filter((s) => !skillOptions.includes(s))];

  const toggleSkill = (skill) => {
    const exists = skillsUsed.includes(skill);
    const next = exists ? skillsUsed.filter((s) => s !== skill) : [...skillsUsed, skill];
    onExperienceField(experience.id, 'skillsUsed', next);
  };

  const addCustomSkill = () => {
    const clean = customSkill.trim();
    if (!clean) return;
    if (!skillsUsed.includes(clean)) {
      onExperienceField(experience.id, 'skillsUsed', [...skillsUsed, clean]);
    }
    setCustomSkill('');
  };

  return (
    <FormField label="Skills used">
      <div className="flex flex-wrap gap-2">
        {visibleOptions.map((skill) => (
          <FormChip key={skill} active={skillsUsed.includes(skill)} onClick={() => toggleSkill(skill)}>{skill}</FormChip>
        ))}
      </div>
      <div className="mt-2.5 flex gap-2">
        <FormInput value={customSkill} onChange={(e) => setCustomSkill(e.target.value)} placeholder="Add skill…" />
        <button type="button" onClick={addCustomSkill} className="shrink-0 rounded-[14px] bg-[#161616] px-3.5 text-[13.5px] font-bold text-white transition hover:bg-[#2a2a2a]">Add</button>
      </div>
    </FormField>
  );
}

// ---------- profile content ----------

function ProfileBody({ draft, onField, onToggleList, onAddCustom, onAddExperience, onRemoveExperience, onExperienceField }) {
  const [customInterest, setCustomInterest] = useState('');
  const [customSkill, setCustomSkill] = useState('');

  const visibleInterests = [...careerInterestOptions, ...draft.careerInterests.filter((v) => !careerInterestOptions.includes(v))];
  const visibleSkills = [...skillOptions, ...draft.currentSkills.filter((v) => !skillOptions.includes(v))];

  // Same real, already-tracked signals used for the (unused) dashboard's
  // completion ring — reused here as an actual sidebar instead of dead
  // space. Stretching every text input edge-to-edge to fill the width just
  // made a one-word field like "Full name" absurdly wide without adding any
  // value; a form's fields should stay a normal reading width regardless of
  // how much screen it has. Discover and Career AI both pair their content
  // with a fixed-width column (the category rail / tools rail) rather than
  // stretching their content full-bleed, so this gives Profile the same
  // shape: a capped-width form + a real fixed-width column, not a wider box.
  const strengthSections = [
    { label: 'About you', done: Boolean(draft.fullName && draft.headline) },
    { label: 'Education', done: Boolean(draft.collegeName && draft.educationLevel) },
    { label: 'Links', done: Boolean(draft.githubUrl || draft.linkedinUrl) },
    { label: 'Skills', done: draft.currentSkills.length > 0 },
    { label: 'Interests', done: draft.careerInterests.length > 0 },
    { label: 'Experience', done: draft.experiences.length > 0 },
  ];
  const strengthDone = strengthSections.filter((s) => s.done).length;
  const strengthPct = Math.round((strengthDone / strengthSections.length) * 100);

  return (
    <div className="flex min-h-0 w-full flex-1 gap-5 overflow-hidden">
    <div className="custom-scroll flex min-h-0 max-w-4xl flex-1 flex-col gap-4 overflow-y-auto overflow-x-hidden pb-4 pr-1">
      {/* About you */}
      <Panel className="shrink-0">
        <CardHead title="About you" sub="How you show up across the app" />
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <FormField label="Full name">
            <FormInput value={draft.fullName} onChange={(e) => onField('fullName', e.target.value)} placeholder="e.g. Ansh Gautam" />
          </FormField>
          <FormField label="Headline">
            <FormInput value={draft.headline} onChange={(e) => onField('headline', e.target.value)} placeholder="e.g. Aspiring Frontend Engineer" />
          </FormField>
          <div className="sm:col-span-2">
            <FormField label="Short bio">
              <FormTextArea value={draft.bio} onChange={(e) => onField('bio', e.target.value)} placeholder="A couple of lines about who you are and what you're working toward." />
            </FormField>
          </div>
          <FormField label="City">
            <FormInput value={draft.city} onChange={(e) => onField('city', e.target.value)} placeholder="e.g. Delhi" />
          </FormField>
          <FormField label="Country">
            <FormInput value={draft.country} onChange={(e) => onField('country', e.target.value)} placeholder="e.g. India" />
          </FormField>
        </div>
      </Panel>

      <div className="grid shrink-0 grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Education */}
        <Panel className="shrink-0 lg:col-span-2">
          <CardHead title="Education" sub="Your academic background" />
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <FormField label="College / institution">
                <FormInput value={draft.collegeName} onChange={(e) => onField('collegeName', e.target.value)} placeholder="e.g. Delhi Technological University" />
              </FormField>
            </div>
            <FormField label="Education level">
              <FormSelect value={draft.educationLevel} onChange={(v) => onField('educationLevel', v)} placeholder="Select level" options={educationLevels} />
            </FormField>
            <FormField label="Degree">
              <FormSelect value={draft.degree} onChange={(v) => onField('degree', v)} placeholder="Select degree" options={degreeOptions} />
            </FormField>
            <FormField label="Branch">
              <FormSelect value={draft.branch} onChange={(v) => onField('branch', v)} placeholder="Select branch" options={branchOptions} />
            </FormField>
            <FormField label="Graduation year">
              <FormInput type="number" value={draft.graduationYear} onChange={(e) => onField('graduationYear', e.target.value)} placeholder="e.g. 2028" />
            </FormField>
            <FormField label="Major / focus area">
              <FormInput value={draft.major} onChange={(e) => onField('major', e.target.value)} placeholder="e.g. AI, Marketing, Finance" />
            </FormField>
            <FormField label="Graduation status">
              <FormSelect value={draft.graduationStatus} onChange={(v) => onField('graduationStatus', v)} placeholder="Select status" options={graduationStatusOptions} />
            </FormField>
          </div>
        </Panel>

        {/* Links */}
        <Panel className="shrink-0">
          <CardHead title="Links" sub="How people find your work" />
          <div className="mt-3 flex flex-col gap-3">
            <FormField label="GitHub profile link">
              <FormInput value={draft.githubUrl} onChange={(e) => onField('githubUrl', e.target.value)} placeholder="https://github.com/yourname" />
            </FormField>
            <FormField label="LinkedIn URL">
              <FormInput value={draft.linkedinUrl} onChange={(e) => onField('linkedinUrl', e.target.value)} placeholder="https://linkedin.com/in/..." />
            </FormField>
            <ResumeField draft={draft} onField={onField} />
          </div>
        </Panel>
      </div>

      {/* Skills & interests */}
      <Panel className="shrink-0">
        <CardHead title="Skills & interests" sub="What you're good at and where you want to go" />
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <div>
            <p className="mb-2 text-[12.5px] font-bold uppercase tracking-wide text-[#9a9a97]">Career interests</p>
            <div className="flex flex-wrap gap-2">
              {visibleInterests.map((interest) => (
                <FormChip key={interest} active={draft.careerInterests.includes(interest)} onClick={() => onToggleList('careerInterests', interest)}>{interest}</FormChip>
              ))}
            </div>
            <div className="mt-2.5 flex gap-2">
              <FormInput value={customInterest} onChange={(e) => setCustomInterest(e.target.value)} placeholder="Add interest…" />
              <button type="button" onClick={() => { onAddCustom('careerInterests', customInterest); setCustomInterest(''); }} className="shrink-0 rounded-[14px] bg-[#161616] px-3.5 text-[13.5px] font-bold text-white transition hover:bg-[#2a2a2a]">Add</button>
            </div>
          </div>
          <div>
            <p className="mb-2 text-[12.5px] font-bold uppercase tracking-wide text-[#9a9a97]">Current skills</p>
            <div className="flex flex-wrap gap-1.5">
              {visibleSkills.map((skill) => (
                <FormChip key={skill} active={draft.currentSkills.includes(skill)} onClick={() => onToggleList('currentSkills', skill)}>{skill}</FormChip>
              ))}
            </div>
            <div className="mt-2.5 flex gap-2">
              <FormInput value={customSkill} onChange={(e) => setCustomSkill(e.target.value)} placeholder="Add skill…" />
              <button type="button" onClick={() => { onAddCustom('currentSkills', customSkill); setCustomSkill(''); }} className="shrink-0 rounded-[14px] bg-[#161616] px-3.5 text-[13.5px] font-bold text-white transition hover:bg-[#2a2a2a]">Add</button>
            </div>
          </div>
        </div>
        <div className="mt-4 grid gap-3 border-t border-[#111827]/8 pt-4 sm:grid-cols-2">
          <FormField label="Target role">
            <FormInput value={draft.targetRole} onChange={(e) => onField('targetRole', e.target.value)} placeholder="e.g. Frontend Engineer" />
          </FormField>
          <FormField label="Target company (optional)">
            <FormInput value={draft.targetCompany} onChange={(e) => onField('targetCompany', e.target.value)} placeholder="e.g. Notion" />
          </FormField>
        </div>
      </Panel>

      {/* Experience */}
      <Panel className="shrink-0">
        <CardHead
          title="Experience"
          sub={`${draft.experiences.length} ${draft.experiences.length === 1 ? 'entry' : 'entries'}`}
          action={<button type="button" onClick={onAddExperience} className="inline-flex items-center gap-1.5 rounded-full bg-[#161616] px-3 py-1.5 text-[13px] font-bold text-white transition hover:bg-[#2a2a2a]">{icons.plus} Add</button>}
        />
        <div className="mt-3 flex flex-col gap-3">
          {draft.experiences.length === 0 && (
            <p className="rounded-[16px] border border-dashed border-white/70 bg-white/40 px-4 py-6 text-center text-[13.5px] font-semibold text-[#9a9a97]">No experience added yet. Click Add to create one.</p>
          )}
          {draft.experiences.map((experience) => (
            <div key={experience.id} className="rounded-[18px] border border-white/70 bg-white/70 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="grid flex-1 gap-3 sm:grid-cols-2">
                  <FormField label="Title">
                    <FormInput value={experience.title} onChange={(e) => onExperienceField(experience.id, 'title', e.target.value)} placeholder="e.g. Frontend Intern" />
                  </FormField>
                  <FormField label="Company / organization">
                    <FormInput value={experience.company} onChange={(e) => onExperienceField(experience.id, 'company', e.target.value)} placeholder="e.g. Campus AI Club" />
                  </FormField>
                </div>
                <button type="button" onClick={() => onRemoveExperience(experience.id)} title="Remove" className="mt-6 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-white/70 bg-white/70 text-[#5a5a58] transition hover:text-[#161616]">{icons.close}</button>
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <FormField label="Employment type">
                  <FormSelect value={experience.experienceType} onChange={(v) => onExperienceField(experience.id, 'experienceType', v)} placeholder="Select type" options={employmentTypes} />
                </FormField>
                <FormField label="Location">
                  <FormInput value={experience.location} onChange={(e) => onExperienceField(experience.id, 'location', e.target.value)} placeholder="e.g. Remote, Delhi" />
                </FormField>
                <FormField label="Start date">
                  <FormInput type="date" value={experience.startDate} onChange={(e) => onExperienceField(experience.id, 'startDate', e.target.value)} />
                </FormField>
                <FormField label="End date">
                  <FormInput type="date" value={experience.endDate} onChange={(e) => onExperienceField(experience.id, 'endDate', e.target.value)} disabled={experience.currentlyWorking} />
                </FormField>
              </div>
              <label className="mt-3 flex items-center gap-2 text-[13.5px] font-semibold text-[#4a4a48]">
                <input type="checkbox" checked={experience.currentlyWorking} onChange={(e) => onExperienceField(experience.id, 'currentlyWorking', e.target.checked)} className="h-3.5 w-3.5 accent-[#161616]" />
                Currently working here
              </label>
              <div className="mt-3">
                <FormField label="Description">
                  <FormTextArea value={experience.description} onChange={(e) => onExperienceField(experience.id, 'description', e.target.value)} placeholder="What did you work on?" />
                </FormField>
              </div>
              <div className="mt-3">
                <ExperienceSkillsField experience={experience} onExperienceField={onExperienceField} />
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>

      {/* Profile strength — the same completion checklist the (unused)
          dashboard prototype computed, surfaced here as a live sidebar
          instead of sitting on a route nothing links to. Ties directly to
          the draft being edited, so it updates as you type instead of
          being a static decoration. */}
      <aside className="hidden w-[300px] shrink-0 xl:block">
        <Panel className="sticky top-0">
          <CardHead title="Profile strength" sub="How complete your profile is" />
          <div className="mt-4 flex items-center gap-4">
            <div
              className="relative flex h-16 w-16 shrink-0 items-center justify-center rounded-full"
              style={{ background: `conic-gradient(#5c63ff ${strengthPct * 3.6}deg, #ece9fd 0deg)` }}
            >
              <div className="flex h-[52px] w-[52px] items-center justify-center rounded-full bg-white text-[13px] font-black text-[#1a1a1a]">
                {strengthPct}%
              </div>
            </div>
            <p className="text-[12.5px] font-semibold leading-snug text-[#6a6a68]">
              {strengthDone} of {strengthSections.length} sections filled in.
            </p>
          </div>
          <div className="mt-5 flex flex-col gap-2.5 border-t border-[#111827]/8 pt-4">
            {strengthSections.map((section) => (
              <div key={section.label} className="flex items-center gap-2.5 text-[13px] font-semibold text-[#3a3a38]">
                <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${section.done ? 'bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-white' : 'border border-[#d8d8d4] text-transparent'}`}>
                  {icons.check}
                </span>
                {section.label}
              </div>
            ))}
          </div>
        </Panel>
      </aside>
    </div>
  );
}

// Memoized so switching tabs never re-renders a body whose props are
// unchanged — only the shell chrome and visibility wrappers update.
const SidebarContentBodyMemo = React.memo(SidebarContentBody);
const SavedBodyMemo = React.memo(SavedBody);
const ProfileBodyMemo = React.memo(ProfileBody);

// Same reasoning, one level deeper: these four are now permanently mounted
// inside SidebarContentBody (see the Career AI content-pane stack) instead
// of being conditionally rendered, so SidebarContentBody re-renders on
// every `active`/search keystroke. None of these take props that change
// (three take none at all; AI Coach's `onNavigateTab` is a stable setState
// function), so without memo, every fast click would still re-render all
// four full report/report-sized trees on every keystroke — memoizing them
// is what makes rapid back-and-forth clicking stay smooth instead of janky.
const ProfileAnalysisDashboardMemo = React.memo(ProfileAnalysisDashboard);
const CareerRoadmapDashboardMemo = React.memo(CareerRoadmapDashboard);
const CareerSimulationDashboardMemo = React.memo(CareerSimulationDashboard);
const CareerCoachDashboardMemo = React.memo(CareerCoachDashboard);

// ---------- shell ----------

const VIEW_ROUTES = { discover: '/discover', 'career-ai': '/career-ai', profile: '/profile', saved: '/saved' };

function AppShell({ view: initialView }) {
  const [status, setStatus] = useState('loading');
  const [profile, setProfile] = useState(null);
  const [user, setUser] = useState(null);
  const [profileDraft, setProfileDraft] = useState(() => normalizeProfile(null));
  const [profileSaveState, setProfileSaveState] = useState('idle');
  const [profileSaveMessage, setProfileSaveMessage] = useState('');
  const [draftSyncedFor, setDraftSyncedFor] = useState(null);
  // savedItems is the single source of truth for bookmarks (full opportunity
  // rows); savedIds is just a derived id-only Set for fast "is this card
  // saved?" lookups on cards outside the Saved tab. Keeping both in sync by
  // hand (instead of having the Saved tab re-fetch from Supabase whenever
  // savedIds changes) avoids a real race: an unsave's DELETE and a refetch
  // fired at the same moment could have the refetch win and show the row
  // again before the delete had actually committed.
  const [savedItems, setSavedItems] = useState([]);
  const [savedIds, setSavedIds] = useState(new Set());
  const [savedStatus, setSavedStatus] = useState('loading');
  // Opportunities the user has marked as applied — id-only, same shape as
  // savedIds, but one-directional: there's no "Applied" list/undo UI yet,
  // so unlike savedItems there's no full-row counterpart to keep in sync.
  const [appliedIds, setAppliedIds] = useState(new Set());
  // Ids currently mid-exit-animation: added the instant a toggle fires (so
  // the card can animate out immediately), then swept into/out of the real
  // appliedIds only after the CSS transition finishes — see toggleApplied.
  const [pendingAppliedIds, setPendingAppliedIds] = useState(new Set());
  // Bottom-center confirmation pill, iOS-app-install style. `key` forces a
  // fresh mount (so the fade/slide-in replays) even if the same message
  // fires twice in a row.
  const [toast, setToast] = useState({ visible: false, message: '', key: 0 });
  const toastTimerRef = useRef(null);

  const showToast = useCallback((message) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast((prev) => ({ visible: true, message, key: prev.key + 1 }));
    toastTimerRef.current = setTimeout(() => {
      setToast((prev) => ({ ...prev, visible: false }));
    }, 2200);
  }, []);
  // View is owned locally so a tab click flips it synchronously — the active
  // pill and visible pane update on the same frame as the click, without
  // routing through the parent App component.
  const [view, setView] = useState(initialView);
  const [syncedInitial, setSyncedInitial] = useState(initialView);
  // Account dropdown (avatar in the top-right of the header) — closed by
  // default, toggled on click, dismissed on an outside click or Escape.
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const accountMenuRef = useRef(null);

  // Follow external navigation (in-content links that change the route prop).
  if (initialView !== syncedInitial) {
    setSyncedInitial(initialView);
    setView(initialView);
  }

  useEffect(() => {
    if (!accountMenuOpen) return undefined;
    const onPointerDown = (event) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target)) {
        setAccountMenuOpen(false);
      }
    };
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setAccountMenuOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [accountMenuOpen]);

  const loadSaved = useCallback(async () => {
    setSavedStatus('loading');
    try {
      const rows = await loadSavedOpportunities();
      setSavedItems(rows);
      setSavedIds(new Set(rows.map((r) => r.id)));
      setSavedStatus('ready');
    } catch {
      setSavedStatus('error');
    }
  }, []);

  // Best-effort: a failure here just means an already-applied opportunity
  // might briefly reappear until the next successful load, not a broken
  // page — so unlike loadSaved there's no error state to surface.
  const loadApplied = useCallback(async () => {
    try {
      const ids = await loadAppliedOpportunityIds();
      setAppliedIds(ids);
    } catch {
      // non-fatal, see comment above
    }
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const currentUser = session?.user ?? null;
      if (!active) return;
      if (!currentUser) { setCacheScope(null); setStatus('signed-out'); return; }
      // Must happen before anything reads/writes the Career AI cache (the
      // dashboards' own lazy useState initializers run as soon as they
      // mount) — see localCache.js for why an unscoped cache would leak a
      // previous account's data on a shared device.
      setCacheScope(currentUser.id);
      setUser(currentUser);
      const loaded = await loadOnboardingProfile();
      if (!active) return;
      setProfile(loaded || {});
      setStatus('ready');
      loadSaved();
      loadApplied();
    })();
    return () => { active = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Client-side route protection is only ever a UX convenience here — the
  // real enforcement is Supabase RLS on every table this app reads/writes.
  // What this effect adds on top of the initial getSession() check above is
  // *staying* correct: if the session is revoked or expires while someone
  // is already inside a protected screen (signed out in another tab, token
  // refresh fails), supabase-js emits SIGNED_OUT and this drops the app back
  // to the same "sign in to continue" screen the initial load uses, instead
  // of continuing to render a screen for a session that no longer exists.
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'SIGNED_OUT') {
        setCacheScope(null);
        setUser(null);
        setProfile(null);
        setStatus('signed-out');
      }
    });
    return () => subscription.unsubscribe();
  }, []);

  // Keep local view in sync with browser back/forward.
  useEffect(() => {
    const onPop = () => {
      const path = window.location.pathname;
      const matched = Object.keys(VIEW_ROUTES).find((v) => VIEW_ROUTES[v] === path);
      if (matched) setView(matched);
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const goToView = (next) => {
    if (next === view) return;
    if (VIEW_ROUTES[next] && window.location.pathname !== VIEW_ROUTES[next]) {
      window.history.pushState({}, '', VIEW_ROUTES[next]);
    }
    setView(next);
  };

  // Optimistic toggle: update savedIds (fast lookup) and savedItems (full
  // rows, what the Saved tab renders) immediately, write to Supabase in the
  // background, and roll both back if the write actually fails. Updating
  // savedItems directly — instead of having the Saved tab re-fetch from the
  // DB — means an unsave can never "flash back" from a refetch racing an
  // in-flight DELETE.
  const toggleSaved = useCallback((item) => {
    const isSaved = savedIds.has(item.id);

    setSavedIds((prev) => {
      const next = new Set(prev);
      if (isSaved) next.delete(item.id); else next.add(item.id);
      return next;
    });
    setSavedItems((prev) => (
      isSaved ? prev.filter((i) => i.id !== item.id) : [item, ...prev.filter((i) => i.id !== item.id)]
    ));

    const revert = () => {
      setSavedIds((prev) => {
        const next = new Set(prev);
        if (isSaved) next.add(item.id); else next.delete(item.id);
        return next;
      });
      setSavedItems((prev) => (
        isSaved ? [item, ...prev.filter((i) => i.id !== item.id)] : prev.filter((i) => i.id !== item.id)
      ));
    };

    const write = isSaved ? unsaveOpportunity(item.id) : saveOpportunity(item.id);
    write.catch(revert);
  }, [savedIds]);

  // Two-directional, same optimistic-then-persist-then-rollback-on-failure
  // shape as toggleSaved, but with a two-phase commit so the card gets a
  // chance to animate out first: the instant a toggle fires, the id goes
  // into pendingAppliedIds (which makes the card play its exit animation —
  // see OpportunityCard's `exiting` prop) and a toast confirms where it
  // went. Only after that transition has had time to finish (matching the
  // 300ms duration on the card) does the real appliedIds flip, which is
  // what actually moves the card between lists. The Supabase write races
  // alongside the animation rather than waiting for it, so the two are
  // independent: a failed write cancels the pending commit and reverts
  // everything, whether or not the animation has already played.
  const toggleApplied = useCallback((item) => {
    const isApplied = appliedIds.has(item.id);
    let committed = false;

    setPendingAppliedIds((prev) => new Set(prev).add(item.id));
    showToast(isApplied ? `Moved back to ${categoryLabelByKey[item.category] || 'its category'}` : 'Moved to Applied');

    const clearPending = () => {
      setPendingAppliedIds((prev) => {
        if (!prev.has(item.id)) return prev;
        const next = new Set(prev);
        next.delete(item.id);
        return next;
      });
    };

    const flipApplied = (toApplied) => {
      setAppliedIds((prev) => {
        const next = new Set(prev);
        if (toApplied) next.add(item.id); else next.delete(item.id);
        return next;
      });
    };

    const timer = setTimeout(() => {
      committed = true;
      clearPending();
      flipApplied(!isApplied);
    }, 320);

    const write = isApplied ? unmarkOpportunityApplied(item.id) : markOpportunityApplied(item.id);
    write.catch(() => {
      clearTimeout(timer);
      clearPending();
      // If the timer already fired before the write rejected, appliedIds
      // has the new value — undo it. If it hasn't fired yet, appliedIds was
      // never touched, so there's nothing to undo there.
      if (committed) flipApplied(isApplied);
    });
  }, [appliedIds, showToast]);

  // useCallback keeps these identities stable so ProfileBodyMemo can skip
  // re-rendering when the user switches away and back.
  const updateDraftField = useCallback((field, value) => setProfileDraft((current) => ({ ...current, [field]: value })), []);

  const toggleDraftList = useCallback((field, value) => setProfileDraft((current) => {
    const exists = current[field].includes(value);
    return { ...current, [field]: exists ? current[field].filter((v) => v !== value) : [...current[field], value] };
  }), []);

  const addDraftCustom = useCallback((field, value) => {
    const clean = value.trim();
    if (!clean) return;
    setProfileDraft((current) => ({
      ...current,
      [field]: current[field].includes(clean) ? current[field] : [...current[field], clean],
    }));
  }, []);

  const addDraftExperience = useCallback(() => setProfileDraft((current) => ({
    ...current,
    experiences: [...current.experiences, { id: crypto.randomUUID(), title: '', company: '', experienceType: '', location: '', startDate: '', endDate: '', currentlyWorking: false, description: '', skillsUsed: [] }],
  })), []);

  const removeDraftExperience = useCallback((id) => setProfileDraft((current) => ({
    ...current,
    experiences: current.experiences.filter((exp) => exp.id !== id),
  })), []);

  const updateDraftExperienceField = useCallback((id, field, value) => setProfileDraft((current) => ({
    ...current,
    experiences: current.experiences.map((exp) => (exp.id === id ? { ...exp, [field]: value } : exp)),
  })), []);

  const handleSaveProfile = async () => {
    setProfileSaveState('saving');
    setProfileSaveMessage('');
    try {
      await saveOnboardingProfile(profileDraft);
      const reloaded = await loadOnboardingProfile();
      setProfile(reloaded || {});
      setProfileSaveState('saved');
      setProfileSaveMessage('Saved to your profile.');
    } catch (error) {
      setProfileSaveState('error');
      setProfileSaveMessage(error.message || 'Something went wrong while saving.');
    }
  };

  const handleLogout = async () => {
    setAccountMenuOpen(false);
    setCacheScope(null);
    await supabase.auth.signOut();
    window.location.assign('/');
  };

  if (status === 'loading') return (
    <StatusScreen>
      <div className="flex flex-col items-center gap-4">
        <div className="h-9 w-9 animate-spin rounded-full border-[3px] border-[#ded9ff] border-t-[#5c63ff]" />
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#9a9a97]">Loading…</p>
      </div>
    </StatusScreen>
  );
  if (status === 'signed-out') {
    return (
      <StatusScreen>
        <p className="text-lg font-semibold">You need to sign in to continue.</p>
        <a href="/" className="mt-5 inline-block rounded-full bg-[#161616] px-5 py-2.5 text-sm font-bold text-white transition hover:bg-[#2a2a2a]">Go to login</a>
      </StatusScreen>
    );
  }

  // Reset the editable draft from the latest saved profile every time the
  // Profile tab is freshly entered (not on every re-render while editing).
  // This runs during render rather than in an effect, matching React's
  // documented "adjusting state when a prop changes" pattern.
  if (view === 'profile' && draftSyncedFor !== 'profile') {
    setDraftSyncedFor('profile');
    setProfileDraft(normalizeProfile(profile));
    setProfileSaveState('idle');
    setProfileSaveMessage('');
  } else if (view !== 'profile' && draftSyncedFor !== null) {
    setDraftSyncedFor(null);
  }

  const fullName = profile.fullName || user?.user_metadata?.full_name || user?.user_metadata?.name || profile.collegeName || 'Builder';
  const avatarUrl = user?.user_metadata?.avatar_url || user?.user_metadata?.picture;

  const navTabs = [
    { label: 'Discover', icon: icons.analytics, target: 'discover', active: view === 'discover' },
    { label: 'Career AI', icon: icons.pulse, target: 'career-ai', active: view === 'career-ai' },
    { label: 'Profile', icon: icons.data, target: 'profile', active: view === 'profile' },
  ];

  const isDiscover = view === 'discover';
  const isCareerAi = view === 'career-ai';
  const isProfile = view === 'profile';
  const isSaved = view === 'saved';
  const eyebrow = isDiscover ? 'Discover · Opportunities' : isCareerAi ? 'Career AI · Tools' : isSaved ? 'Saved · Bookmarks' : 'Profile · Edit';
  const heading = isDiscover ? 'Find your next move' : isCareerAi ? 'Plan with Career AI' : isSaved ? 'Your saved opportunities' : 'Your profile';
  // Discover, Career AI, and Profile pick up the landing page's theme —
  // but the Hero's more saturated diagonal gradient read as too pink once
  // rendered full-screen, so this uses the FAQ section's much lighter,
  // mostly-white cream/lavender wash instead (still "the landing page
  // theme," just its subtler variant) — Dashboard and Saved keep the
  // original flat wash since only these three were asked to match it.
  const useLandingTheme = isDiscover || isCareerAi || isProfile;

  return (
    // `h-dvh`, not `h-screen` (= a flat 100vh): on mobile Safari/Chrome the
    // address bar shows and hides as you scroll, and 100vh is sized for
    // the *largest* case (bar hidden) — so a chunk of every pane's bottom
    // content (the Learning Hub info card included) was sitting behind
    // real browser chrome and getting visually trimmed. `dvh` tracks the
    // actual visible viewport instead.
    <div className={`relative h-dvh overflow-hidden text-[#1a1a1a] ${useLandingTheme ? 'bg-[linear-gradient(180deg,#fffdf9_0%,#fff8f2_42%,#f8f6ff_100%)]' : 'bg-[#eaeae7]'}`}>
      {/* ambient wash so the glass has color to refract. Promoted to its own
          GPU layer (transform-gpu) and marked static so the expensive large
          blurs are painted once and never re-rendered when panes switch. */}
      <div className="pointer-events-none absolute inset-0 transform-gpu" style={{ willChange: 'transform' }}>
        {/* FAQ section's warm-peach + lavender wash, used app-wide now — no
            more lime/green blobs anywhere in the shell. */}
        <div className="absolute -left-24 -top-24 h-[380px] w-[380px] rounded-full bg-[#c9bbff] opacity-25 blur-[120px]" />
        <div className="absolute right-[-80px] top-[10%] h-[340px] w-[340px] rounded-full bg-[#bcd6ff] opacity-30 blur-[130px]" />
        <div className="absolute bottom-[-120px] left-1/3 h-[420px] w-[420px] rounded-full bg-[#ffe2b0] opacity-25 blur-[130px]" />
        <div className="absolute bottom-0 right-1/4 h-[300px] w-[300px] rounded-full bg-[#ffd9a8] opacity-20 blur-[120px]" />
      </div>

      {/* The Discover/Career AI/Profile switcher lived only in the header nav
          (`hidden md:flex`), with nothing standing in for it below md — there
          was no way to switch views at all on a phone. A fixed bottom tab
          bar is the standard mobile pattern for a small, primary nav like
          this one; it stays out of the header's way (which is already tight
          on mobile) and is always reachable regardless of scroll position.
          The container below reserves matching bottom padding so content
          never sits behind it. */}
      <nav
        className="fixed inset-x-0 bottom-0 z-50 flex items-center justify-around border-t border-white/70 bg-white/90 px-2 pt-2 backdrop-blur-xl md:hidden"
        style={{ paddingBottom: 'max(0.5rem, env(safe-area-inset-bottom))' }}
      >
        {navTabs.map((t) => (
          <button
            key={t.label}
            type="button"
            onClick={() => goToView(t.target)}
            className={`flex flex-1 flex-col items-center gap-1 rounded-2xl py-1.5 text-[10.5px] font-bold transition ${t.active ? 'text-[#161616]' : 'text-[#9a9a97]'}`}
          >
            <span className={`flex h-8 w-8 items-center justify-center rounded-full transition ${t.active ? 'bg-[#161616] text-white' : 'text-[#9a9a97]'}`}>
              {t.icon}
            </span>
            {t.label}
          </button>
        ))}
      </nav>

      <div className="relative z-10 mx-auto flex h-full max-w-[1440px] flex-col px-6 pb-20 pt-5 sm:px-10 sm:pb-6 sm:pt-6">
        {/* Top nav */}
        <header className="flex shrink-0 items-center justify-between gap-4">
          <div className="flex items-end gap-3">
            {/* Real brand asset (public/logo.svg), shown as-is with no
                badge/tile wrapper. Sized up (was h-9/h-10) so it reads at
                the same visual weight as the solid-black "Discover" pill
                sitting right next to it instead of looking tiny by
                comparison. items-end + a small nudge lines the wordmark's
                own baseline up with the pill buttons' text, same fix as
                the landing header. */}
            <a href="/" className="flex items-end">
              <img src="/logo.svg" alt="OwnMove" className="h-12 w-auto translate-y-[2px] sm:h-14 sm:translate-y-[3px]" />
            </a>
            <nav className="hidden items-center gap-2 md:flex">
              {navTabs.map((t) => (
                <button
                  key={t.label}
                  type="button"
                  onClick={() => goToView(t.target)}
                  // The old hover (bg-white/75 -> white/80) was a 5%
                  // opacity nudge — essentially invisible. An opaque white
                  // fill, a solid border, a lift, and a shadow make it
                  // actually register, matching the Categories sidebar's
                  // hover treatment.
                  className={`inline-flex items-center gap-2 rounded-full border px-4 py-2.5 text-[13.5px] font-bold transition-all duration-200 ${
                    t.active
                      ? 'border-transparent bg-[#161616] text-white shadow-[0_10px_20px_-10px_rgba(0,0,0,0.45)]'
                      : 'border-white/70 bg-white/75 backdrop-blur-md text-[#4a4a48] hover:-translate-y-[1px] hover:border-white hover:bg-white hover:text-[#161616] hover:shadow-[0_12px_24px_-14px_rgba(40,50,30,0.45)]'
                  }`}
                >
                  {t.icon}{t.label}
                </button>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-2.5">

            <button
              type="button"
              title="Saved"
              onClick={() => goToView('saved')}
              className={`relative flex h-9 w-9 items-center justify-center rounded-full border transition ${
                isSaved ? 'border-white/10 bg-[#161616] text-white' : 'border-white/70 bg-white/75 backdrop-blur-md text-[#3a3a38] hover:bg-white/80 hover:text-[#161616]'
              }`}
            >
              {icons.bookmark}
              {savedIds.size > 0 && (
                <span className={`absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full px-1 text-[8.5px] font-black text-white ${isSaved ? 'bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)]' : 'bg-[#161616]'}`}>
                  {savedIds.size}
                </span>
              )}
            </button>
            <div className="relative" ref={accountMenuRef}>
              <button
                type="button"
                onClick={() => setAccountMenuOpen((open) => !open)}
                title="Account"
                aria-haspopup="menu"
                aria-expanded={accountMenuOpen}
                className="block rounded-full transition focus:outline-none focus-visible:ring-2 focus-visible:ring-[#7b62e8] focus-visible:ring-offset-2"
              >
                {avatarUrl ? <img src={avatarUrl} alt={fullName} className="h-9 w-9 rounded-full object-cover ring-2 ring-white" /> : <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#161616] text-xs font-black text-white">{fullName.charAt(0).toUpperCase()}</div>}
              </button>
              {accountMenuOpen && (
                <div
                  role="menu"
                  className="absolute right-0 top-[calc(100%+10px)] z-50 w-56 overflow-hidden rounded-[18px] border border-white/70 bg-white/95 py-1.5 shadow-[0_20px_48px_-16px_rgba(40,50,30,0.35)] backdrop-blur-xl"
                >
                  <div className="border-b border-black/5 px-4 py-3">
                    <p className="truncate text-[13px] font-black text-[#1a1a1a]">{fullName}</p>
                    {user?.email && <p className="truncate text-[11.5px] font-medium text-[#9a9a97]">{user.email}</p>}
                  </div>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => { setAccountMenuOpen(false); goToView('profile'); }}
                    className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-[13px] font-bold text-[#3a3a38] transition hover:bg-black/5"
                  >
                    {icons.user}
                    Profile
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={handleLogout}
                    className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-[13px] font-bold text-[#b34747] transition hover:bg-[#fdf2f2]"
                  >
                    {icons.logout}
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Title row */}
        <div className="mt-5 flex shrink-0 flex-wrap items-center justify-between gap-y-2.5 gap-x-3">
          <div className="flex items-center gap-3">
            <div>
              <p className="text-[11px] font-semibold text-[#9a9a97]">{eyebrow}</p>
              <h1 className="text-[22px] font-black leading-none tracking-tight sm:text-[25px]">{heading}</h1>
            </div>
          </div>
          {isProfile && (
            <div className="flex flex-wrap items-center gap-2">
              {profileSaveMessage && (
                <span className={`rounded-full px-3 py-1.5 text-[12px] font-semibold ${profileSaveState === 'error' ? 'border border-red-200 bg-red-50 text-red-600' : 'border border-white/70 bg-white/75 backdrop-blur-md text-[#4a4a48]'}`}>
                  {profileSaveMessage}
                </span>
              )}
              <button
                type="button"
                onClick={handleSaveProfile}
                disabled={profileSaveState === 'saving'}
                className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-[#161616] px-3.5 py-1.5 text-[12px] font-bold text-white transition hover:bg-[#2a2a2a] disabled:opacity-50"
              >
                {profileSaveState === 'saving' ? icons.refresh : icons.check}
                {profileSaveState === 'saving' ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          )}
        </div>

        {/* Body: every pane is mounted once and stacked. Switching only
            flips opacity — a compositor-only operation (no layout, no repaint),
            so left↔right switching is instant with zero lag. `transform-gpu`
            promotes each pane to its own GPU layer so the flip stays on the
            compositor thread. */}
        <div className="relative mt-5 min-h-0 flex-1">

          <div className={`absolute inset-0 flex flex-col transform-gpu ${isDiscover ? 'z-10' : 'pointer-events-none opacity-0'}`}>
            <SidebarContentBodyMemo items={categories} sectionLabel="Categories" initialKey="for-you" mode="opportunities" profile={profile} savedIds={savedIds} onToggleSaved={toggleSaved} appliedIds={appliedIds} onToggleApplied={toggleApplied} pendingAppliedIds={pendingAppliedIds} />
          </div>
          <div className={`absolute inset-0 flex flex-col transform-gpu ${isCareerAi ? 'z-10' : 'pointer-events-none opacity-0'}`}>
            <SidebarContentBodyMemo items={careerAiOptions} sectionLabel="Tools" initialKey="ai-coach" profile={profile} locked />
          </div>
          <div className={`absolute inset-0 flex flex-col transform-gpu ${isProfile ? 'z-10' : 'pointer-events-none opacity-0'}`}>
            <ProfileBodyMemo
              draft={profileDraft}
              onField={updateDraftField}
              onToggleList={toggleDraftList}
              onAddCustom={addDraftCustom}
              onAddExperience={addDraftExperience}
              onRemoveExperience={removeDraftExperience}
              onExperienceField={updateDraftExperienceField}
            />
          </div>
          <div className={`absolute inset-0 flex flex-col transform-gpu ${isSaved ? 'z-10' : 'pointer-events-none opacity-0'}`}>
            <SavedBodyMemo items={savedItems} status={savedStatus} onRetry={loadSaved} onToggleSaved={toggleSaved} profile={profile} appliedIds={appliedIds} onToggleApplied={toggleApplied} onBrowseDiscover={() => goToView('discover')} />
          </div>
        </div>
      </div>

      {/* App-install-style confirmation pill for the applied/disconnect
          toggle. `key` remounts it on every showToast call so the fade+rise
          replays even for the same message fired twice in a row; the
          visible flag then drives the fade-out via the transition classes
          rather than unmounting immediately, so it always animates both
          ways instead of popping. */}
      <div
        key={toast.key}
        aria-live="polite"
        className={`pointer-events-none fixed inset-x-0 bottom-6 z-50 flex justify-center transition-all duration-300 ease-out ${
          toast.visible ? 'translate-y-0 opacity-100' : 'translate-y-3 opacity-0'
        }`}
      >
        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-[#161616]/95 px-4 py-2.5 text-[13px] font-bold text-white shadow-[0_12px_32px_-8px_rgba(0,0,0,0.5)] backdrop-blur-md">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/15">{icons.check}</span>
          {toast.message}
        </div>
      </div>
    </div>
  );
}

export default AppShell;
