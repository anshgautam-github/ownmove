import React, { useMemo, useState } from 'react';
import { supabase } from '../../services/supabase/client';
import { safeSetItem } from '../../utils/safeStorage';

// This section is not a job board — it surfaces credible programs,
// fellowships, student communities, ambassador programs, open-source
// initiatives, learning programs, and career-building opportunities that
// students don't typically find through normal job boards. Every entry
// below is a real, currently-operating program; none of the copy claims
// live application windows, stipends, or acceptance rates that can't be
// verified, since those details change independently of this page.
const opportunityPrograms = [
  {
    id: 'google',
    companyName: 'Google',
    logoUrl: 'https://www.google.com/s2/favicons?domain=google.com&sz=128',
    fallbackLabel: 'G',
    fallbackColor: '#4285F4',
    programName: 'Google Summer of Code',
    programType: 'Open Source',
    description: 'A global program where contributors work on real open-source projects with mentoring from participating open-source organizations.',
    highlight: 'Build real open-source software with experienced mentors.',
    tags: ['Open Source', 'Mentorship', 'Software Development'],
    verificationStatus: 'verified',
  },
  {
    id: 'microsoft',
    companyName: 'Microsoft',
    logoUrl: 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=128',
    fallbackLabel: 'M',
    fallbackColor: '#737373',
    programName: 'Microsoft Student Ambassadors',
    programType: 'Student Community',
    description: 'A global student community for learning Microsoft technologies, developing technical and leadership skills, and helping other students learn through campus communities.',
    highlight: 'Grow your technical skills while helping others grow theirs.',
    tags: ['Leadership', 'Technology', 'Community'],
    verificationStatus: 'verified',
  },
  {
    id: 'amazon',
    companyName: 'Amazon',
    logoUrl: 'https://www.google.com/s2/favicons?domain=amazon.com&sz=128',
    fallbackLabel: 'A',
    fallbackColor: '#FF9900',
    programName: 'Amazon ML Summer School',
    programType: 'Machine Learning',
    description: 'A learning program for eligible students in India interested in strengthening their foundations in machine learning through sessions led by Amazon scientists.',
    highlight: 'Learn machine learning concepts from scientists working in the field.',
    tags: ['Machine Learning', 'Learning', 'AI'],
    verificationStatus: 'verified',
  },
  {
    id: 'aws',
    companyName: 'AWS',
    logoUrl: 'https://www.google.com/s2/favicons?domain=aws.amazon.com&sz=128',
    fallbackLabel: 'AWS',
    fallbackColor: '#FF9900',
    programName: 'AWS Cloud Clubs — Cloud Club Captain',
    programType: 'Cloud + Student Leadership',
    description: 'A student-led community initiative where Cloud Club Captains help students learn cloud technologies by building communities and organizing technical activities.',
    highlight: 'Build your cloud knowledge while leading a student community.',
    tags: ['Cloud', 'Leadership', 'Community'],
    verificationStatus: 'verified',
  },
  {
    id: 'ibm',
    companyName: 'IBM',
    logoUrl: 'https://www.google.com/s2/favicons?domain=ibm.com&sz=128',
    fallbackLabel: 'IBM',
    fallbackColor: '#0530AD',
    programName: 'IBM Z Student Ambassador',
    programType: 'Student Leadership',
    description: 'A student-focused initiative associated with IBM Z that helps students build technical knowledge, share learning, and engage their campus communities around enterprise technology.',
    highlight: 'Turn technical learning into leadership and community impact.',
    tags: ['IBM Z', 'Leadership', 'Community'],
    verificationStatus: 'verified',
  },
  {
    id: 'github',
    companyName: 'GitHub',
    logoSlug: 'github',
    fallbackLabel: 'gh',
    fallbackColor: '#171321',
    programName: 'GitHub Campus Experts',
    programType: 'Developer Community',
    description: 'A student leadership program that trains students to build stronger technical communities through workshops, events, open-source collaboration, and peer learning.',
    highlight: 'Become someone who helps build the developer community around you.',
    tags: ['Developer Community', 'Open Source', 'Leadership'],
    verificationStatus: 'verified',
  },
  {
    id: 'nvidia',
    companyName: 'NVIDIA',
    logoSlug: 'nvidia',
    fallbackLabel: 'N',
    fallbackColor: '#76B900',
    programName: 'NVIDIA Deep Learning Institute',
    programType: 'AI / Technical Learning',
    description: 'Technical training and hands-on learning resources covering areas like accelerated computing, deep learning, generative AI, and related NVIDIA technologies.',
    highlight: 'Build practical skills in modern accelerated computing and AI.',
    tags: ['AI', 'Deep Learning', 'GPU Computing'],
    verificationStatus: 'verified',
  },
  {
    id: 'salesforce',
    companyName: 'Salesforce',
    logoUrl: 'https://www.google.com/s2/favicons?domain=salesforce.com&sz=128',
    fallbackLabel: 'SF',
    fallbackColor: '#00A1E0',
    programName: 'Trailblazer Connect',
    programType: 'Student Community',
    description: 'A student community where you can build Salesforce ecosystem knowledge, learn relevant technologies, and connect with mentors and other students through events and learning resources.',
    highlight: "Learn the ecosystem and turn that knowledge into community impact.",
    tags: ['Salesforce', 'Community', 'Learning'],
    verificationStatus: 'verified',
  },
  {
    id: 'mercedes-benz',
    companyName: 'Mercedes-Benz',
    logoUrl: 'https://www.google.com/s2/favicons?domain=mercedes-benz.com&sz=128',
    fallbackLabel: 'MB',
    fallbackColor: '#6B7280',
    programName: 'beVisioneers: The Mercedes-Benz Fellowship',
    programType: 'Sustainability Fellowship',
    description: 'A multi-year fellowship supporting young people working on environmental challenges through learning, mentoring, community, and project development.',
    highlight: 'Turn an environmental idea into meaningful real-world action.',
    tags: ['Sustainability', 'Fellowship', 'Mentorship'],
    verificationStatus: 'verified',
  },
  {
    id: 'linux-foundation',
    companyName: 'Linux Foundation',
    logoSlug: 'linuxfoundation',
    fallbackLabel: 'LF',
    fallbackColor: '#003366',
    programName: 'LFX Mentorship',
    programType: 'Open Source Mentorship',
    description: 'A mentorship program that connects participants with open-source projects, where they gain practical experience working alongside experienced project mentors.',
    highlight: 'Move from learning open source to contributing to real projects.',
    tags: ['Open Source', 'Mentorship', 'Engineering'],
    verificationStatus: 'verified',
  },
  {
    id: 'cncf',
    companyName: 'CNCF',
    logoSlug: 'cncf',
    fallbackLabel: 'C',
    fallbackColor: '#446CFF',
    programName: 'CNCF Mentoring Initiatives',
    programType: 'Cloud Native / Open Source',
    description: 'Mentoring opportunities that help contributors gain experience with cloud-native and open-source technologies while working on projects within the CNCF ecosystem.',
    highlight: 'Learn cloud-native engineering by contributing to its ecosystem.',
    tags: ['Cloud Native', 'Open Source', 'Mentorship'],
    verificationStatus: 'verified',
  },
  {
    id: 'mlh',
    companyName: 'Major League Hacking',
    logoSlug: 'majorleaguehacking',
    fallbackLabel: 'MLH',
    fallbackColor: '#E2373E',
    programName: 'MLH Fellowship',
    programType: 'Engineering Fellowship',
    description: 'A structured technical fellowship where participants gain practical software engineering and collaboration experience through project-based work.',
    highlight: 'Build alongside other developers in an intensive technical environment.',
    tags: ['Engineering', 'Open Source', 'Fellowship'],
    verificationStatus: 'verified',
  },
  {
    id: 'apple',
    companyName: 'Apple',
    logoSlug: 'apple',
    fallbackLabel: 'A',
    fallbackColor: '#111111',
    programName: 'Swift Student Challenge',
    programType: 'Student Developer Challenge',
    description: 'An annual challenge that gives student developers an opportunity to demonstrate creativity and technical skills by building an app playground with Swift.',
    highlight: 'Turn an idea into something you can build and showcase with Swift.',
    tags: ['Swift', 'App Development', 'Student Challenge'],
    verificationStatus: 'verified',
  },
  {
    id: 'uber',
    companyName: 'Uber',
    logoSlug: 'uber',
    fallbackLabel: 'U',
    fallbackColor: '#000000',
    programName: 'Uber Career Prep',
    programType: 'Early-Career Development',
    description: 'A career-development initiative that supports students from historically underrepresented backgrounds in technology through technical development, mentorship, and career preparation.',
    highlight: 'Strengthen the skills that sit between learning computer science and entering industry.',
    tags: ['Software Engineering', 'Mentorship', 'Career Development'],
    verificationStatus: 'verified',
  },
];

// Every logo tries its real brand mark first — either a simpleicons.org
// CDN slug, or (for brands not in that set) a direct logoUrl. If that
// image ever fails to load, it falls back to a plain colored monogram
// instead of the browser's broken-image glyph. Deliberately NOT setting
// crossOrigin/referrerPolicy here: those force the browser into CORS mode,
// and a plain <img> displaying a picture (no canvas pixel reads happening)
// never needs CORS — requesting it anyway silently kills the image on any
// host that doesn't echo back permissive CORS headers, which is exactly
// what was happening to the Wikimedia/favicon swaps below.
function LogoMark({ slug, logoUrl, alt, fallbackLabel, fallbackColor, size = 'sm' }) {
  const [failed, setFailed] = useState(false);

  const dimensions = {
    sm: { box: 'h-5 w-5', text: 'text-[0.55rem]' },
    md: { box: 'h-12 w-12', text: 'text-[0.95rem]' },
    lg: { box: 'h-11 w-11', text: 'text-[0.8rem]' },
  }[size];

  if (failed) {
    return (
      <div
        className={`flex ${dimensions.box} shrink-0 items-center justify-center rounded-[7px] font-bold leading-none text-white`}
        style={{ backgroundColor: fallbackColor }}
      >
        <span className={dimensions.text}>{fallbackLabel}</span>
      </div>
    );
  }

  // logoUrl (Google's public favicon service, keyed by the company's real
  // domain) takes priority over the simpleicons CDN slug. A handful of
  // real-world brands (Microsoft, Amazon, AWS, IBM, Salesforce,
  // Mercedes-Benz) simply aren't in the simpleicons set, and Google's own
  // simpleicons mark isn't the real multi-color wordmark either — the
  // favicon service always returns each domain's actual live icon.
  const imageSrc = logoUrl || `https://cdn.simpleicons.org/${slug}`;

  return (
    <img
      src={imageSrc}
      alt={alt}
      className={`${dimensions.box} shrink-0 object-contain`}
      onError={() => setFailed(true)}
    />
  );
}

function DemoSection() {
  const [activeId, setActiveId] = useState(null);
  const [draggingId, setDraggingId] = useState(null);
  const [isOverDrop, setIsOverDrop] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [activationKey, setActivationKey] = useState(0);
  const [showDragPrompt, setShowDragPrompt] = useState(false);

  const activeItem = useMemo(() => {
    if (!activeId) return null;
    return opportunityPrograms.find((item) => item.id === activeId) ?? null;
  }, [activeId]);

  const handleEmptyClick = () => {
    if (!activeItem) {
      setShowDragPrompt(true);
      setTimeout(() => setShowDragPrompt(false), 800);
    }
  };

  const activateItem = (id) => {
    setActiveId(id);
    setDraggingId(null);
    setIsOverDrop(false);
    setIsLoadingDetails(true);
    setTimeout(() => {
      setIsLoadingDetails(false);
      setActivationKey((value) => value + 1);
    }, 1000);
  };

  const removeItem = () => {
    setActiveId(null);
    setIsLoadingDetails(false);
  };

  // HowItWorksSection (the next section) rides up over whatever precedes it
  // with a negative top margin (-mt-12 sm:-mt-16) to make its floating
  // rounded card overlap — which quietly eats the same amount off the
  // bottom of that section. LandingPage now renders DemoSection directly
  // before HowItWorksSection, so pb is bumped here (instead of symmetric
  // py) so the visible gap survives that overlap instead of collapsing.
  return (
    <section className={`relative overflow-x-hidden pt-12 pb-[88px] sm:pt-16 sm:pb-[104px] transition-colors duration-700 ease-in-out ${draggingId ? 'bg-[#0a0a0f]' : 'bg-[#fafbfe]'}`} id="demo-section">
      <style>{`
        @keyframes godOrbit1 {
          0% { transform: translate(-50%, -50%) rotate(0deg) translateX(150px) rotate(0deg); }
          100% { transform: translate(-50%, -50%) rotate(360deg) translateX(150px) rotate(-360deg); }
        }
        @keyframes godOrbit2 {
          0% { transform: translate(-50%, -50%) rotate(120deg) translateX(250px) rotate(-120deg); }
          100% { transform: translate(-50%, -50%) rotate(480deg) translateX(250px) rotate(-480deg); }
        }
        @keyframes godOrbit3 {
          0% { transform: translate(-50%, -50%) rotate(240deg) translateX(200px) rotate(-240deg); }
          100% { transform: translate(-50%, -50%) rotate(600deg) translateX(200px) rotate(-600deg); }
        }
        .glass-panel {
          background: rgba(255, 255, 255, 0.7);
          backdrop-filter: blur(32px);
          -webkit-backdrop-filter: blur(32px);
          border: 1px solid rgba(255, 255, 255, 0.9);
          box-shadow: 0 30px 60px rgba(11, 23, 75, 0.08), inset 0 1px 0 rgba(255, 255, 255, 1);
        }
        .glass-button {
          background: rgba(255, 255, 255, 0.6);
          border: 1px solid rgba(235, 238, 245, 0.8);
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .glass-button:hover {
          background: rgba(255, 255, 255, 0.95);
          border-color: rgba(144, 166, 252, 0.4);
          box-shadow: 0 10px 20px rgba(54, 76, 246, 0.08);
          transform: translateY(-1px);
        }
        .glass-button.active {
          background: rgba(255, 255, 255, 1);
          border-color: rgba(54, 76, 246, 0.6);
          box-shadow: 0 10px 25px rgba(54, 76, 246, 0.15), inset 0 0 0 1px rgba(54, 76, 246, 0.1);
        }
        .glow-ring {
          border: 1px solid rgba(54, 76, 246, 0.12);
          box-shadow: 0 0 40px rgba(54, 76, 246, 0.03) inset, 0 0 10px rgba(255, 255, 255, 0.5);
          transition: all 0.5s ease;
        }
        .drop-zone-active {
          border-color: #ff6b00;
          box-shadow: 0 0 80px rgba(255, 107, 0, 0.4), inset 0 0 30px rgba(255, 107, 0, 0.1);
          background: rgba(255, 255, 255, 0.95);
        }
        .g-logo-float {
          animation: gLogoBob 4s ease-in-out infinite;
        }
        @keyframes gLogoBob {
          0%, 100% { transform: translateY(0) translateX(-50%); }
          50% { transform: translateY(-8px) translateX(-50%); }
        }
        .skeleton-pulse {
          animation: skBonePulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        @keyframes skBonePulse {
          0%, 100% { opacity: 1; }
          50% { opacity: .5; }
        }
        @keyframes dropScaleIn {
          0% { transform: scale(0.5); opacity: 0; filter: blur(5px); }
          100% { transform: scale(1); opacity: 1; filter: blur(0); }
        }
        @keyframes wigglePrompt {
          0%, 100% { transform: rotate(0deg) scale(1); }
          25% { transform: rotate(-5deg) scale(1.05); }
          75% { transform: rotate(5deg) scale(1.05); }
        }
        .animate-prompt-wiggle {
          animation: wigglePrompt 0.4s ease-in-out 2;
        }
        @keyframes highlightList {
          0%, 100% { box-shadow: 0 0 0 rgba(54,76,246,0); }
          50% { box-shadow: 0 0 40px rgba(54,76,246,0.3); transform: scale(1.01); }
        }
        .animate-highlight-list {
          animation: highlightList 0.8s ease-in-out;
        }
      `}</style>

      {/* God-Level Animated Orbs Background */}
      <div className={`absolute inset-0 overflow-hidden pointer-events-none z-0 transition-opacity duration-1000 ${draggingId ? 'opacity-100' : 'opacity-0'}`}>
        <div className="absolute left-1/2 top-1/2 h-[750px] w-[750px] rounded-full bg-[radial-gradient(circle,rgba(54,76,246,0.12)_0%,transparent_70%)] blur-[80px]" style={{ animation: 'godOrbit1 20s linear infinite' }}></div>
        <div className="absolute left-1/2 top-1/2 h-[800px] w-[800px] rounded-full bg-[radial-gradient(circle,rgba(0,198,255,0.08)_0%,transparent_70%)] blur-[90px]" style={{ animation: 'godOrbit2 25s linear infinite' }}></div>
        <div className="absolute left-1/2 top-1/2 h-[600px] w-[600px] rounded-full bg-[radial-gradient(circle,rgba(255,100,200,0.06)_0%,transparent_70%)] blur-[70px]" style={{ animation: 'godOrbit3 18s linear infinite' }}></div>
        <div className="absolute inset-0 bg-[linear-gradient(rgba(10,15,44,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(10,15,44,0.02)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_at_center,black_10%,transparent_70%)]"></div>
      </div>

      <div className="relative z-10 mx-auto max-w-[1400px] px-6 sm:px-8 lg:px-10">
        {/* Header Section */}
        <div className={`flex flex-col sm:flex-row sm:items-center sm:justify-between w-full transition-all duration-700 mb-10 ${draggingId ? 'opacity-30' : 'opacity-100'}`}>
          {/* Floor was 2.5rem (40px) — since 4.5vw doesn't overtake that
              floor until the viewport is ~889px wide, every phone and most
              tablets rendered this at a flat 40px, and "Opportunities You
              Probably" (plus the forced <br/>) wrapped into 3-4 chunky lines
              at that size on a narrow screen. 2rem (32px) is still a real
              mobile heading size, just proportionate to the column it's
              actually sitting in below that width. */}
          <h2 className={`text-[clamp(2rem,4.5vw,4.5rem)] font-medium leading-[1.05] tracking-tight transition-colors duration-700 ${draggingId ? 'text-white' : 'text-[#0a0f2c]'}`}>
            Opportunities You Probably <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#364cf6] to-[#af46f8]">Haven&apos;t Heard Of.</span>
          </h2>
          <button
            onClick={async () => {
              const { data } = await supabase.auth.getSession();
              if (data.session) {
                window.location.assign('/discover#programs');
              } else {
                safeSetItem('postLoginRedirect', '/discover#programs');
                window.dispatchEvent(new CustomEvent('open-auth', { detail: 'login' }));
              }
            }}
            className="relative overflow-hidden rounded-full p-[1px] group shadow-[0_10px_30px_rgba(54,76,246,0.2)] mt-6 sm:mt-0 shrink-0"
          >
            <span className="absolute inset-0 bg-gradient-to-r from-[#364cf6] to-[#af46f8] opacity-100 transition-opacity"></span>
            <div className="relative bg-[#364cf6] group-hover:bg-[#2b3ee3] px-8 py-3.5 rounded-full transition-colors">
              <span className="text-base font-semibold text-white">Explore More</span>
            </div>
          </button>
        </div>

        {/* Content Layout */}
        <div className="flex flex-col items-center justify-between gap-x-10 gap-y-12 lg:flex-row lg:items-center lg:gap-x-14">

          {/* Left: Programs Grid — fixed height matching the other two
              columns, with the list scrolling internally. Before,
              this panel only had a min-height, so its 16-item grid pushed
              the box taller than its siblings and past the section's own
              boundary, getting clipped mid-row instead of showing its full
              rounded bottom edge. */}
          <div className={`glass-panel flex w-full flex-col overflow-hidden rounded-[24px] p-6 transition-all origin-center duration-300 lg:w-[480px] lg:p-8 h-[560px] ${showDragPrompt ? 'animate-highlight-list ring-[3px] ring-[#364cf6] ring-offset-4 ring-offset-[#fafbfe]' : ''}`}>
            <div className={`mb-6 shrink-0 text-[0.8rem] font-semibold uppercase tracking-widest pl-2 transition-colors ${showDragPrompt ? 'text-[#364cf6]' : 'text-[#8b91a8]'}`}>
              Companies
            </div>

            {/* grid-rows-7 + h-full stretches every row to fill the panel's
                full height evenly, instead of the rows sizing to their own
                min-height and leaving a leftover gap below the last row. */}
            <div className="grid h-full grid-cols-2 grid-rows-7 gap-3">
              {opportunityPrograms.map((item) => {
                const isPlaceholder = activeId === item.id || draggingId === item.id;

                return (
                  <button
                    key={item.id}
                    type="button"
                    draggable={!isPlaceholder}
                    aria-pressed={activeId === item.id}
                    aria-label={`View ${item.companyName}'s ${item.programName}`}
                    onDragStart={(event) => {
                      if (isPlaceholder) {
                        event.preventDefault();
                        return;
                      }
                      event.dataTransfer.setData('text/plain', item.id);
                      event.dataTransfer.effectAllowed = 'copyMove';
                      // Timeout ensures browser captures the dragged item's UI correctly before changing styles
                      setTimeout(() => setDraggingId(item.id), 0);
                    }}
                    onDragEnd={() => {
                      setDraggingId(null);
                      setIsOverDrop(false);
                    }}
                    onClick={() => {
                      if (!isPlaceholder) activateItem(item.id);
                    }}
                    className={`relative h-full w-full text-left transition-all ${
                      isPlaceholder
                        ? 'rounded-[14px] bg-[#f0f2f8] border-[1.5px] border-dashed border-[#d2d6e3] opacity-40 cursor-default shadow-inner'
                        : 'group flex items-center gap-3.5 rounded-[14px] px-4 glass-button cursor-pointer'
                    }`}
                  >
                    <div className={`flex items-center gap-3 w-full h-full transition-opacity ${isPlaceholder ? 'opacity-0' : 'opacity-100'}`}>
                      <LogoMark
                        slug={item.logoSlug}
                        logoUrl={item.logoUrl}
                        alt={item.companyName}
                        fallbackLabel={item.fallbackLabel}
                        fallbackColor={item.fallbackColor}
                        size="sm"
                      />
                      <span className="min-w-0 flex-1 text-[0.78rem] font-medium leading-tight text-[#4b5575] group-hover:text-[#0a0f2c] transition-colors">
                        {item.companyName}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Center: Drag Target Canvas with Concentric Radiating Rings */}
          <div className="relative flex w-full max-w-[400px] flex-col items-center justify-center min-h-[400px]">

            {/* Center Canvas */}

            {/* Floating Icons Exact Symmetric Wrapper */}
            <div className="relative h-[200px] w-[200px] z-10 flex items-center justify-center">

              <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 mt-[14px] ml-[14px] h-[150px] w-[150px] rounded-full bg-[#ff4400] blur-[30px] transition-all duration-700 z-0 pointer-events-none ${draggingId ? 'opacity-90 scale-110' : 'opacity-0 scale-50'}`}></div>
              <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 mt-[14px] ml-[14px] h-[80px] w-[80px] rounded-full bg-[#ffea00] blur-[15px] transition-all duration-700 z-0 pointer-events-none ${draggingId ? 'opacity-80 scale-100' : 'opacity-0 scale-50'}`}></div>

              {/* glow-ring was already defined in the stylesheet above but
                  never actually attached to anything — meaning the whole
                  middle column had nothing but a small dashed square
                  floating in empty space at rest. Wrapping the drop target
                  in it gives that gap a quiet, intentional presence instead
                  of reading as leftover whitespace, and fades out the moment
                  something real (drag or an active item) is happening. */}
              <div className={`glow-ring absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 mt-[14px] ml-[14px] h-[220px] w-[220px] rounded-full pointer-events-none z-0 transition-opacity duration-500 ${draggingId || activeItem ? 'opacity-0' : 'opacity-100'}`}></div>

              <div
                role="button"
                tabIndex={0}
                aria-label="Drop zone — drag a program here, or use the cards below"
                onClick={handleEmptyClick}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    handleEmptyClick();
                  }
                }}
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 mt-[14px] ml-[14px] flex h-[110px] w-[110px] items-center justify-center cursor-pointer z-20 group focus:outline-none focus-visible:ring-2 focus-visible:ring-[#7b62e8] rounded-[28px]"
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsOverDrop(true);
                }}
                onDragLeave={() => setIsOverDrop(false)}
                onDrop={(event) => {
                  event.preventDefault();
                  const id = event.dataTransfer.getData('text/plain');
                  if (id) activateItem(id);
                }}
              >
                <div className={`absolute inset-0 rounded-[28px] border-[2px] transition-all duration-300 ${
                  showDragPrompt ? 'animate-prompt-wiggle shadow-[0_0_40px_rgba(255,94,0,0.5)] border-[#ff5e00] bg-white' :
                  activeItem ? 'border-transparent bg-white shadow-[0_15px_40px_rgba(54,76,246,0.15)]' :
                  isOverDrop ? 'border-transparent bg-white scale-110 border-solid drop-zone-active shadow-[0_0_50px_rgba(255,94,0,0.4)]' :
                  draggingId ? 'border-transparent bg-white scale-105 border-solid shadow-[0_0_30px_rgba(255,68,0,0.3)]' :
                  'border-[#b6baf6] bg-white/70 group-hover:bg-white/90 backdrop-blur-md border-dashed shadow-[0_15px_40px_rgba(0,0,0,0.03)]'
                }`} />

                <div className="relative z-10 flex h-full w-full items-center justify-center pointer-events-none">
                  {activeItem ? (
                    <div className="absolute inset-0 flex items-center justify-center animate-[dropScaleIn_0.4s_cubic-bezier(0.175,0.885,0.32,1.275)] transition-all pointer-events-auto">
                      <LogoMark
                        slug={activeItem.logoSlug}
                        logoUrl={activeItem.logoUrl}
                        alt={activeItem.companyName}
                        fallbackLabel={activeItem.fallbackLabel}
                        fallbackColor={activeItem.fallbackColor}
                        size="md"
                      />
                      <button
                        onClick={(e) => { e.stopPropagation(); removeItem(); }}
                        className="absolute -top-3 -right-3 flex h-[28px] w-[28px] items-center justify-center rounded-full bg-[#afb3c7] hover:bg-[#8e95ac] shadow-sm transition-colors text-white"
                      >
                        <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" strokeWidth="2.5" fill="none"><path d="M18 6L6 18M6 6l12 12" /></svg>
                      </button>
                    </div>
                  ) : (
                    <svg viewBox="0 0 24 24" fill="none" className={`h-11 w-11 transition-all duration-500 transform ${
                      isOverDrop || draggingId ? 'text-[#0a0f2c] scale-105' : 'text-[#364cf6]/50 scale-100'
                    }`}>
                      <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                </div>
              </div>
          </div>
        </div>

          {/* Right: Program Preview */}
          <div className="w-full lg:w-[480px]">
            <div className={`relative h-full w-full rounded-[20px] transition-colors duration-700 p-8 sm:p-10 min-h-[560px] flex flex-col overflow-hidden border ${
              draggingId ? 'bg-[#272a3f] border-[#3a3d58] shadow-2xl' : 'bg-white text-[#1f2937] shadow-[0_30px_70px_rgba(11,23,75,0.08)] border-[#e5e7eb]'
            }`}>
              {/* This corner wash was a plain mint-green that doesn't appear
                  anywhere else on the site — every other accent (the "Explore
                  More" button, the heading, the drop-zone glow) uses the same
                  blue-to-violet brand gradient, so the one green blob read as
                  an off-brand leftover rather than a deliberate choice. */}
              <div className="absolute top-0 right-0 h-64 w-64 rounded-bl-full bg-gradient-to-bl from-[#eef1ff] via-[#f4ecff] to-transparent opacity-70 pointer-events-none"></div>

              {!activeItem ? (
                <div className="flex-1 flex items-center justify-center text-center px-4 z-10">
                  <p className={`text-xl sm:text-2xl font-light max-w-[280px] leading-relaxed transition-colors duration-700 ${draggingId ? 'text-white/80' : 'text-[#5a658a]'}`}>
                    <span className="inline-block mr-3 text-[#c6a0f6] animate-pulse">◀</span>
                    Drag a company.
                    <br />
                    See what you&rsquo;ve been missing.
                  </p>
                </div>
              ) : isLoadingDetails ? (
                /* Skeleton Loader */
                <div className="flex flex-col h-full z-10 w-full animate-fade-in flex-1">
                  <div className="flex items-center gap-4 mb-8">
                    <div className="h-8 w-8 rounded bg-slate-200 skeleton-pulse"></div>
                    <div className="h-8 w-48 rounded bg-slate-200 skeleton-pulse"></div>
                  </div>
                  <div className="space-y-3 mb-10 w-full">
                    <div className="h-4 w-full bg-slate-200 rounded skeleton-pulse"></div>
                    <div className="h-4 w-[90%] bg-slate-200 rounded skeleton-pulse" style={{animationDelay: '100ms'}}></div>
                    <div className="h-4 w-[75%] bg-slate-200 rounded skeleton-pulse" style={{animationDelay: '200ms'}}></div>
                  </div>
                  <div className="h-6 w-24 bg-slate-200 rounded mb-5 skeleton-pulse" style={{animationDelay: '300ms'}}></div>
                  <div className="space-y-4">
                    <div className="h-[28px] w-full bg-slate-100 rounded flex items-center px-2 skeleton-pulse" style={{animationDelay: '400ms'}}></div>
                    <div className="h-[28px] w-[85%] bg-slate-100 rounded flex items-center px-2 skeleton-pulse" style={{animationDelay: '500ms'}}></div>
                    <div className="h-[28px] w-[95%] bg-slate-100 rounded flex items-center px-2 skeleton-pulse" style={{animationDelay: '600ms'}}></div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col h-full z-10 animate-fade-in" key={activationKey}>
                  <div className="flex items-center gap-3 mb-5">
                    <LogoMark
                      slug={activeItem.logoSlug}
                      logoUrl={activeItem.logoUrl}
                      alt={activeItem.companyName}
                      fallbackLabel={activeItem.fallbackLabel}
                      fallbackColor={activeItem.fallbackColor}
                      size="lg"
                    />
                    <div>
                      <div className="text-[1.05rem] font-semibold leading-tight text-[#111827]">{activeItem.companyName}</div>
                      <div className="text-[0.95rem] leading-tight text-[#4b5575]">{activeItem.programName}</div>
                    </div>
                  </div>

                  <span className="mb-5 inline-flex w-fit items-center rounded-full bg-[#eef1fb] px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-wide text-[#364cf6]">
                    {activeItem.programType}
                  </span>

                  <p className="text-[1.02rem] leading-[1.65] text-[#374151] font-normal">
                    {activeItem.description}
                  </p>

                  <p className="mt-4 text-[1.02rem] leading-[1.65] font-medium text-[#111827]">
                    {activeItem.highlight}
                  </p>

                  <div className="mt-8 text-[0.72rem] font-semibold uppercase tracking-widest text-[#8b91a8]">
                    Why it&apos;s worth knowing
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {activeItem.tags.map((tag) => (
                      <span key={tag} className="rounded-full border border-[#e5e7eb] px-3 py-1 text-[0.78rem] font-medium text-[#4b5575]">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>

    </section>
  );
}

export default DemoSection;
