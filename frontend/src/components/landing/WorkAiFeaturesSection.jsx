import React from 'react';

// Small numbered badge (reusing the same gradient-circle idiom already used
// for the "considered" list in IntelligenceSection) instead of a checkmark
// repeated on every single line. A checkmark reads as "task complete" —
// fine for a checklist, but odd for three lines describing capabilities —
// and three identical checkmarks stacked per card is exactly the kind of
// generic list-bullet pattern that makes a section feel templated. A number
// gives each line an actual reason to have a badge (it's the Nth thing this
// column does) and reads as more deliberate.
const NumberBadge = ({ index }) => (
  <div className="mt-[1px] flex h-[19px] w-[19px] shrink-0 items-center justify-center rounded-full bg-[linear-gradient(135deg,#364cf6_0%,#af46f8_100%)] text-[10px] font-semibold text-white shadow-[0_3px_8px_rgba(101,89,227,0.28)]">
    {index + 1}
  </div>
);

// The three icons used to each carry their own ad-hoc 3-stop gradient
// (salmon/purple/blue, orange-red/purple/blue, pink/purple/blue) — close
// enough to look like they were supposed to match, but different enough
// that side by side they read as inconsistent, and none of them are the
// blue-to-violet gradient used everywhere else on the site (the "Explore
// More" button, headings, CTAs). Unifying all three to that same gradient
// makes this section feel like part of the same product instead of a
// separately-generated block.
const SearchIconGradient = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="url(#workFeaturesGrad)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-11 h-11 mx-auto mb-2">
    <defs>
      <linearGradient id="workFeaturesGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#364cf6" />
        <stop offset="100%" stopColor="#af46f8" />
      </linearGradient>
    </defs>
    <circle cx="11" cy="11" r="8"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
  </svg>
);

const PenIconGradient = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="url(#workFeaturesGrad)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-11 h-11 mx-auto mb-2">
    <path d="M12 20h9"></path>
    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
  </svg>
);

const GearIconGradient = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="url(#workFeaturesGrad)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-11 h-11 mx-auto mb-2">
    <circle cx="12" cy="12" r="3"></circle>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
  </svg>
);

const workFeaturesData = [
  {
    icon: <SearchIconGradient />,
    title: "Discover what fits you",
    subtitle: "Opportunities worth knowing about",
    items: [
      <><span className="font-[600] text-black">Discover</span> internships, programs, fellowships, scholarships, and competitions</>,
      <><span className="font-[600] text-black">See</span> opportunities that align with your profile and goals</>,
      <><span className="font-[600] text-black">Find</span> opportunities you might not have known to search for</>
    ]
  },
  {
    icon: <PenIconGradient />,
    title: "Understand where you stand",
    subtitle: "Know what to work on next",
    items: [
      <><span className="font-[600] text-black">See</span> how your profile aligns with the direction you&apos;re targeting</>,
      <><span className="font-[600] text-black">Identify</span> the skills and experience that could strengthen your profile</>,
      <><span className="font-[600] text-black">Turn</span> your target role into a personalized Career Roadmap</>
    ]
  },
  {
    icon: <GearIconGradient />,
    title: "Make better career decisions",
    subtitle: "With Career AI",
    items: [
      <><span className="font-[600] text-black">Ask</span> your AI Coach for guidance when you&apos;re unsure what to do next</>,
      <><span className="font-[600] text-black">Compare</span> different career paths and choices with Career Simulation</>,
      <><span className="font-[600] text-black">Get</span> guidance shaped around your goals, profile, and current direction</>
    ]
  }
];

function WorkAiFeaturesSection() {
  return (
    <section className="bg-[linear-gradient(180deg,#ffffff_0%,#f8fbff_100%)] py-24 px-6 lg:px-8 flex flex-col items-center">
      <div className="max-w-[1100px] w-full text-center">
        <h2 className="text-[2.2rem] md:text-[2.6rem] font-medium text-[#111827] tracking-[-0.02em]">
          Everything you need to make your next move.
        </h2>
        
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
          {workFeaturesData.map((feature, i) => (
            <div key={i} className="flex flex-col items-center text-center">
              {feature.icon}
              <div className="text-[1.2rem] font-semibold text-[#111827] mt-1 tracking-[-0.01em]">{feature.title}</div>
              <div className="text-[1.2rem] text-[#8C93A6] mb-8">{feature.subtitle}</div>
              
              <div className="w-full bg-[linear-gradient(180deg,#fafbff_0%,#f4f8ff_100%)] rounded-[16px] p-6 lg:p-8 flex flex-col gap-4 text-left border border-[#eef2fb] shadow-[0_16px_34px_rgba(145,154,204,0.06)] flex-grow">
                {feature.items.map((item, j) => (
                  <div key={j} className="flex items-start gap-2.5 text-[0.88rem] text-[#4B5563] leading-[1.5]">
                    <NumberBadge index={j} />
                    <div>{item}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default WorkAiFeaturesSection;
