import React, { useState } from 'react';

const faqData = {
  "Getting Started": [
    { q: "What is OwnMove?", a: "OwnMove is a career platform that helps you discover relevant opportunities, understand where your profile stands, and figure out what to do next." },
    { q: "Who is OwnMove for?", a: "OwnMove is built primarily for students and early-career professionals looking for internships, programs, fellowships, and clearer direction in their careers." },
    { q: "How do I get started?", a: "Create an account and tell us about your goals, interests, skills, education, projects, and experience. OwnMove uses this information to personalize your experience across the platform." },
    { q: "What if I don't know which career or role I want yet?", a: "That's completely fine. You can start by sharing your interests and current skills, then use OwnMove to explore opportunities and career directions that may fit you." }
  ],
  "Discover": [
    { q: "What kind of opportunities can I find on OwnMove?", a: "You can discover internships, fellowships, student programs, competitions, scholarships, and other career-building opportunities available through companies and organizations." },
    { q: "How does OwnMove decide which opportunities fit me?", a: "OwnMove considers information from your profile, such as your interests, skills, experience, education, and career goals, to surface opportunities that are more relevant to you." },
    { q: "Does OwnMove only show internships and jobs?", a: "No. OwnMove is designed to surface opportunities beyond traditional job listings, including programs, fellowships, competitions, scholarships, and other ways to build your career." },
    { q: "Does OwnMove submit applications for me?", a: "No. OwnMove helps you discover and evaluate opportunities, but you remain in control of your applications and submit them through the appropriate application process." }
  ],
  "Career AI": [
    { q: "What can Career AI help me with?", a: "Career AI includes tools for analyzing your profile, building a personalized career roadmap, comparing career decisions, and getting guidance from your AI Coach." },
    { q: "How is the Career Roadmap personalized?", a: "Your roadmap is built around your target role and the skills, projects, education, and experience already in your profile, so it can focus on what you actually need to work on next." },
    { q: "What does Profile Analysis tell me?", a: "Profile Analysis looks at how your current profile aligns with your target direction and highlights strengths, important gaps, and areas that could make your profile stronger." },
    { q: "What is the AI Coach for?", a: "The AI Coach helps when you're unsure about your next move. It can help you think through opportunities, career choices, priorities, and other decisions using information already available in your OwnMove profile." }
  ],
  "Account & Privacy": [
    { q: "How do I create an OwnMove account?", a: "Select Sign Up and create your account using one of the available sign-in methods. You'll then be guided through a short profile setup." },
    { q: "Can I update my profile later?", a: "Yes. You can update your skills, goals, projects, experience, and other profile information as your career evolves." },
    { q: "Why does OwnMove ask for information about my profile?", a: "Your profile helps OwnMove make its opportunity recommendations and Career AI guidance more relevant to your goals and current experience." },
    { q: "Can I delete my account?", a: "Yes. You can request account deletion along with your associated personal data through account settings or the available support process." }
  ]
}

function FaqSection({ preview = false }) {
  const [activeCategory, setActiveCategory] = useState("Getting Started");
  const [openIndex, setOpenIndex] = useState(0);
  const currentFaqs = faqData[activeCategory] || [];

  if (preview) {
    const previewFaqs = faqData["Getting Started"].slice(0, 3);

    return (
      <section className="h-[100svh] overflow-hidden bg-[linear-gradient(180deg,#fffdf9_0%,#fff8f2_42%,#f8f6ff_100%)] px-6 lg:px-8 text-[#131114]">
        <div className="max-w-[1240px] w-full mx-auto grid lg:grid-cols-[1fr_1.3fr] gap-12 lg:gap-24 items-start pt-28">
          <div className="flex flex-col">
            <h2 className="text-[3.8rem] font-semibold tracking-tight leading-none text-black">FAQs</h2>
            <p className="mt-5 text-[1.12rem] text-[#6B7280] leading-[1.6] max-w-[420px]">
              Everything you need to know about OwnMove, from discovering opportunities to planning your next move.
            </p>
            <div className="mt-8 flex flex-wrap gap-x-3 gap-y-3.5 max-w-[480px]">
              {Object.keys(faqData).map((cat, i) => (
                <div
                  key={i}
                  className={`py-[10px] px-5 rounded-[40px] text-[0.85rem] border ${
                    i === 0
                      ? 'bg-black text-white border-black font-medium shadow-[0_10px_24px_rgba(0,0,0,0.08)]'
                      : 'bg-white/70 text-black border-[#111827]/12'
                  }`}
                >
                  {cat}
                </div>
              ))}
            </div>
          </div>

        <div className="flex min-h-[520px] flex-col justify-start gap-10">
          <div className="flex min-h-[312px] flex-col pr-4">
              {previewFaqs.map((faq, i) => (
                <div key={i} className="border-b border-[#E5E7EB] py-[22px]">
                  <div className="w-full flex items-center justify-between text-left text-[1.18rem] text-[#111827]">
                    {faq.q}
                    <span className="text-[1.8rem] text-[#111827] font-light leading-none relative top-[-1px]">
                      {i === 0 ? '−' : '+'}
                    </span>
                  </div>
                  <div
                    className={`grid transition-[grid-template-rows,opacity,margin] duration-300 ease-out ${
                      i === 0 ? 'mt-3 grid-rows-[1fr] opacity-100' : 'mt-0 grid-rows-[0fr] opacity-0'
                    }`}
                  >
                    <div className="overflow-hidden">
                      <div className="text-[#79808B] text-[0.98rem] leading-[1.65] whitespace-pre-line pr-10">
                        {faq.a}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="relative overflow-hidden rounded-[24px] border border-[#ebe4ff] bg-[linear-gradient(135deg,#ffffff_0%,#faf6ff_38%,#f4f7ff_100%)] px-8 py-7 shadow-[0_20px_50px_rgba(96,86,176,0.08)] bg-clip-padding">
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_18%,rgba(255,224,187,0.38),transparent_28%),radial-gradient(circle_at_82%_18%,rgba(154,127,255,0.16),transparent_24%),linear-gradient(120deg,rgba(255,255,255,0.12),rgba(255,255,255,0)_48%)]" />
              <div className="pointer-events-none absolute right-[-28px] top-[-26px] h-28 w-28 rounded-full bg-[radial-gradient(circle,rgba(166,125,255,0.18)_0%,rgba(166,125,255,0.04)_58%,transparent_72%)] blur-2xl" />
              <div className="relative z-10 flex min-h-[176px] flex-col justify-between">
                <h3 className="text-[1.3rem] font-medium text-black">Still have questions?</h3>
                <p className="mt-2 text-[#4B5563] text-[0.95rem] leading-[1.6] max-w-[580px]">
                  We&apos;re here to help if there&apos;s something we haven&apos;t answered.
                </p>
                <div className="mt-7 flex w-full items-end justify-start">
                  <a
                    href="mailto:ownmovee@gmail.com"
                    className="inline-flex items-center gap-2 rounded-[14px] bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] px-5 py-3 text-[0.95rem] font-medium text-white shadow-[0_14px_28px_rgba(101,89,227,0.22)] transition hover:translate-y-[-1px] hover:shadow-[0_18px_34px_rgba(101,89,227,0.26)]"
                  >
                    Contact Support
                    <span className="text-base leading-none">→</span>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    )
  }

  return (
    // h-screen/min-h-screen only made sense at the lg two-column layout this
    // was designed around. Below lg the grid stacks to one column (category
    // list, then the full FAQ list, then the support card, all vertically),
    // which is taller than one screen — flex+justify-center in a fixed
    // h-screen box would just overflow it instead of laying out normally.
    <section className="flex flex-col justify-center py-16 lg:h-screen lg:min-h-screen lg:py-0 bg-[linear-gradient(180deg,#fffdf9_0%,#fff8f2_42%,#f8f6ff_100%)] px-6 lg:px-8 text-[#131114]">
      <div className="max-w-[1240px] w-full mx-auto grid lg:grid-cols-[1fr_1.3fr] gap-12 lg:gap-24 items-start shrink-0">

        {/* Left Column */}
        <div className="flex flex-col">
          <h2 className="text-[3.8rem] font-semibold tracking-tight leading-none text-black">FAQs</h2>
          <p className="mt-5 text-[1.12rem] text-[#6B7280] leading-[1.6] max-w-[420px]">
            Everything you need to know about OwnMove, from discovering opportunities to planning your next move.
          </p>
          <div className="mt-8 flex flex-wrap gap-x-3 gap-y-3.5 max-w-[480px]">
            {Object.keys(faqData).map((cat, i) => (
              <button
                key={i}
                type="button"
                disabled={preview}
                aria-pressed={cat === activeCategory}
                onClick={() => {
                  setActiveCategory(cat);
                  setOpenIndex(0);
                }}
                className={`group relative overflow-hidden py-[10px] px-5 rounded-[40px] text-[0.85rem] border transition-all duration-300 ease-out active:scale-[0.985] ${
                  cat === activeCategory
                  ? 'bg-black text-white border-black font-medium shadow-[0_12px_28px_rgba(0,0,0,0.12)]'
                    : 'bg-white/70 text-black border-[#111827]/12 hover:bg-white hover:shadow-[0_10px_24px_rgba(17,24,39,0.05)]'
                }`}
              >
                <span
                  className={`pointer-events-none absolute inset-0 rounded-full transition-all duration-300 ease-out ${
                    cat === activeCategory
                      ? 'bg-[linear-gradient(135deg,rgba(255,255,255,0.06),rgba(255,255,255,0))] opacity-100'
                      : 'bg-[linear-gradient(135deg,rgba(123,98,232,0.08),rgba(92,99,255,0.04))] opacity-0 group-hover:opacity-100'
                  }`}
                />
                <span className="relative z-10">{cat}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Right Column */}
        <div key={activeCategory} className="faq-content-swap flex min-h-[520px] flex-col justify-start gap-10">
          <div className="flex min-h-[312px] flex-col pr-4">
            {currentFaqs.map((faq, i) => {
              const isOpen = openIndex === i;
              const questionId = `faq-question-${activeCategory}-${i}`;
              const panelId = `faq-panel-${activeCategory}-${i}`;
              return (
                <div key={i} className="border-b border-[#E5E7EB] py-[22px]">
                  <button
                    type="button"
                    disabled={preview}
                    id={questionId}
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    onClick={() => setOpenIndex(isOpen ? -1 : i)}
                    className="w-full flex items-center justify-between text-left text-[1.18rem] text-[#111827] bg-transparent outline-none"
                  >
                    {faq.q}
                    <span className="text-[1.8rem] text-[#111827] font-light leading-none relative top-[-1px]">
                      {isOpen ? '−' : '+'}
                    </span>
                  </button>
                  <div
                    id={panelId}
                    role="region"
                    aria-labelledby={questionId}
                    className={`grid transition-[grid-template-rows,opacity,margin] duration-300 ease-out ${
                      isOpen ? 'mt-3 grid-rows-[1fr] opacity-100' : 'mt-0 grid-rows-[0fr] opacity-0'
                    }`}
                  >
                    <div className="overflow-hidden">
                      <div className="text-[#79808B] text-[0.98rem] leading-[1.65] whitespace-pre-line pr-10">
                        {faq.a}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="relative overflow-hidden rounded-[24px] border border-[#ebe4ff] bg-[linear-gradient(135deg,#ffffff_0%,#faf6ff_38%,#f4f7ff_100%)] px-8 py-7 shadow-[0_20px_50px_rgba(96,86,176,0.08)] bg-clip-padding">
             <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_18%,rgba(255,224,187,0.38),transparent_28%),radial-gradient(circle_at_82%_18%,rgba(154,127,255,0.16),transparent_24%),linear-gradient(120deg,rgba(255,255,255,0.12),rgba(255,255,255,0)_48%)]" />
             <div className="pointer-events-none absolute right-[-28px] top-[-26px] h-28 w-28 rounded-full bg-[radial-gradient(circle,rgba(166,125,255,0.18)_0%,rgba(166,125,255,0.04)_58%,transparent_72%)] blur-2xl" />

             {/* The card's text tops out around 580px but the card itself
                 stretches the full right column width, so everything past
                 the paragraph was bare gradient — same "empty pocket" issue
                 fixed in a couple of other sections today. A small support
                 badge sitting on top of the existing blur gives that blur an
                 actual reason to be there instead of just being an unlabeled
                 glow, and echoes "Contact Support" visually. */}
             <div className="pointer-events-none absolute right-6 top-6 z-10 flex h-11 w-11 items-center justify-center rounded-full bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-white shadow-[0_10px_22px_rgba(101,89,227,0.28)] sm:right-8 sm:top-7">
               <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                 <path d="M4 12a8 8 0 1 1 3.2 6.4L4 19.5l1.1-3.2A7.96 7.96 0 0 1 4 12Z" />
                 <path d="M8.5 12h.01M12 12h.01M15.5 12h.01" />
               </svg>
             </div>

             <div className="relative z-10 flex min-h-[176px] flex-col justify-between">
                <h3 className="max-w-[400px] text-[1.3rem] font-medium text-black">Still have questions?</h3>
                <p className="mt-2 text-[#4B5563] text-[0.95rem] leading-[1.6] max-w-[580px]">
                  We&apos;re here to help if there&apos;s something we haven&apos;t answered.
                </p>
                <div className="mt-7 flex w-full items-end justify-start">
                  <a
                    href="mailto:ownmovee@gmail.com"
                    className="inline-flex items-center gap-2 rounded-[14px] bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] px-5 py-3 text-[0.95rem] font-medium text-white shadow-[0_14px_28px_rgba(101,89,227,0.22)] transition hover:translate-y-[-1px] hover:shadow-[0_18px_34px_rgba(101,89,227,0.26)]"
                  >
                    Contact Support
                    <span className="text-base leading-none">→</span>
                  </a>
                </div>
             </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default FaqSection;
