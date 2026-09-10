import React, { useState, useRef, useEffect } from 'react';
import { saveOnboardingProfile, loadOnboardingProfile, uploadResume, validateResumeFile } from '../services/supabase/profiles';
import { supabase } from '../services/supabase/client';

const educationLevels = ['High school', 'Diploma', 'Undergraduate', 'Graduate', 'Postgraduate', 'Bootcamp', 'Self-taught'];
const degreeOptions = ['B.Tech', 'B.E.', 'B.Sc', 'BCA', 'BBA', 'BA', 'MBA', 'M.Tech', 'M.Sc', 'Diploma', 'Other'];
const branchOptions = ['Computer Science', 'Information Technology', 'Electronics', 'Mechanical', 'Civil', 'Data Science', 'Design', 'Business', 'Other'];
const graduationStatusOptions = ['Currently studying', 'Graduated', 'On a gap year', 'Dropped out'];
const careerInterestOptions = ['AI/ML', 'Frontend', 'Backend', 'Full Stack', 'Product', 'Data Science', 'Cybersecurity', 'Cloud', 'UI/UX', 'Marketing', 'Founder'];
const skillOptions = ['React', 'JavaScript', 'Python', 'Node.js', 'SQL', 'Git', 'Figma', 'Excel', 'ML', 'Communication', 'Leadership', 'Writing'];
const employmentTypes = ['Internship', 'Part-time', 'Full-time', 'Freelance', 'Volunteer', 'Campus role', 'Project'];
const steps = ['Identity', 'Interests', 'Experience', 'Finish'];

const emptyExperience = {
  title: '',
  company: '',
  experienceType: '',
  location: '',
  startDate: '',
  endDate: '',
  currentlyWorking: false,
  description: '',
  skillsUsed: [],
};

const initialProfile = {
  fullName: '',
  headline: '',
  bio: '',
  city: '',
  country: '',
  collegeName: '',
  educationLevel: '',
  degree: '',
  branch: '',
  major: '',
  graduationYear: '',
  graduationStatus: '',
  careerInterests: [],
  currentSkills: [],
  targetRole: '',
  targetCompany: '',
  experiences: [],
  githubUrl: '',
  linkedinUrl: '',
  resumeUrl: '',
};

// DB values can be null/number; form inputs need '' / string so nothing
// renders as an uncontrolled input and nothing shows literal "null".
function profileFromExisting(existing) {
  return {
    fullName: existing.fullName || '',
    headline: existing.headline || '',
    bio: existing.bio || '',
    city: existing.city || '',
    country: existing.country || '',
    collegeName: existing.collegeName || '',
    educationLevel: existing.educationLevel || '',
    degree: existing.degree || '',
    branch: existing.branch || '',
    major: existing.major || '',
    graduationYear: existing.graduationYear != null ? String(existing.graduationYear) : '',
    graduationStatus: existing.graduationStatus || '',
    careerInterests: existing.careerInterests || [],
    currentSkills: existing.currentSkills || [],
    targetRole: existing.targetRole || '',
    targetCompany: existing.targetCompany || '',
    experiences: (existing.experiences || []).map((experience) => ({
      id: experience.id,
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
    githubUrl: existing.githubUrl || '',
    linkedinUrl: existing.linkedinUrl || '',
    resumeUrl: existing.resumeUrl || '',
  };
}

function Field({ label, children }) {
  return (
    <div className="block">
      <span className="mb-1.5 block text-sm font-medium text-[#131114]">{label}</span>
      {children}
    </div>
  );
}

function TextInput(props) {
  return (
    <input
      {...props}
      className="h-10 w-full rounded-[12px] border border-[#DFE2E7] bg-white px-4 py-2 text-sm text-[#131114] outline-none transition placeholder:text-[#9AA0AA] focus:border-[#131114] focus:shadow-[0_0_0_3px_rgba(19,17,20,0.08)]"
    />
  );
}

function SelectInput({ value, onChange, placeholder, options }) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (e, option) => {
    e.preventDefault();
    e.stopPropagation();
    onChange(option);
    setIsOpen(false);
  };

  return (
    <div className="relative w-full" ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex h-10 w-full items-center justify-between rounded-[12px] border bg-white px-4 py-2 text-sm text-[#131114] outline-none transition-all duration-200 cursor-pointer ${
          isOpen
            ? 'border-[#7b62e8] shadow-[0_0_0_3px_rgba(123,98,232,0.1)]'
            : 'border-[#DFE2E7] hover:border-[#b0b5c1]'
        }`}
      >
        <span className={value ? 'text-[#131114]' : 'text-[#9AA0AA]'}>
          {value || placeholder}
        </span>
        <svg
          className={`h-4 w-4 text-[#79808B] transition-transform duration-200 ${isOpen ? 'rotate-180 text-[#7b62e8]' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth="2.5"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute left-0 right-0 z-50 mt-1.5 max-h-60 overflow-y-auto rounded-[14px] border border-[#111827]/8 bg-white/95 p-1.5 shadow-[0_12px_30px_rgba(101,89,227,0.12)] backdrop-blur-md">
          {options.map((option) => {
            const isSelected = value === option;
            return (
              <button
                key={option}
                type="button"
                onClick={(e) => handleSelect(e, option)}
                className={`flex w-full items-center justify-between rounded-[10px] px-3.5 py-2 text-left text-sm font-medium transition cursor-pointer ${
                  isSelected
                    ? 'bg-[#7b62e8] text-white'
                    : 'text-[#131114] hover:bg-[#7b62e8]/8 hover:text-[#7b62e8]'
                }`}
              >
                <span>{option}</span>
                {isSelected && (
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth="3"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TextArea(props) {
  return (
    <textarea
      {...props}
      className="min-h-16 w-full resize-none rounded-[14px] border border-[#DFE2E7] bg-white px-4 py-3 text-sm leading-5 text-[#131114] outline-none transition placeholder:text-[#9AA0AA] focus:border-[#131114] focus:shadow-[0_0_0_3px_rgba(19,17,20,0.08)]"
    />
  );
}

function Chip({ active, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-200 ease-out ${
        active
          ? 'border-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-white shadow-[0_8px_16px_rgba(101,89,227,0.15)]'
          : 'border-[#111827]/12 bg-white/70 text-black hover:bg-white hover:shadow-[0_6px_16px_rgba(17,24,39,0.04)]'
      }`}
    >
      {children}
    </button>
  );
}
function ProgressBars({ step, onStep }) {
  return (
    <div className="grid grid-cols-4 gap-3" aria-label="Onboarding progress">
      {steps.map((item, index) => (
        <button
          key={item}
          type="button"
          onClick={() => onStep(index)}
          className="h-1.5 overflow-hidden rounded-full bg-[#E5E7EB] hover:bg-[#d9dce2]"
          aria-label={`Go to ${item}`}
        >
          <span
            className="block h-full rounded-full bg-black transition-[width] duration-500 ease-out"
            style={{ width: index <= step ? '100%' : '0%' }}
          />
        </button>
      ))}
    </div>
  );
}

function CelebrationOverlay() {
  return (
    <div className="fixed inset-0 z-[80] grid place-items-center bg-[#fff8f2]/75 backdrop-blur-sm">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {Array.from({ length: 34 }).map((_, index) => (
          <span
            key={index}
            className="confetti-piece absolute left-1/2 top-1/2 h-2 w-1.5 rounded-full"
            style={{
              '--x': `${Math.cos(index * 0.73) * (150 + (index % 5) * 24)}px`,
              '--y': `${Math.sin(index * 0.73) * (120 + (index % 7) * 18)}px`,
              animationDelay: `${index * 18}ms`,
              backgroundColor: ['#11131a', '#ffe0bb', '#9a7fff', '#7b62e8', '#ffc1b2'][index % 5],
            }}
          />
        ))}
      </div>
      <div className="relative overflow-hidden rounded-[24px] border border-[#ebe4ff] bg-[linear-gradient(135deg,#ffffff_0%,#faf6ff_38%,#f4f7ff_100%)] px-8 py-6 text-center shadow-[0_20px_50px_rgba(96,86,176,0.12)]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_18%,rgba(255,224,187,0.38),transparent_28%),radial-gradient(circle_at_82%_18%,rgba(154,127,255,0.16),transparent_24%),linear-gradient(120deg,rgba(255,255,255,0.12),rgba(255,255,255,0)_48%)]" />
        <div className="relative z-10">
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#79808B]">Success</p>
          <p className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-black">Profile saved!</p>
          <p className="mt-1 text-xs text-[#6B7280]">Opening your dashboard...</p>
        </div>
      </div>
    </div>
  );
}

function OnboardingScreen() {
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState({ ...initialProfile });
  const [experienceDraft, setExperienceDraft] = useState({ ...emptyExperience });
  const [customInterest, setCustomInterest] = useState('');
  const [customSkill, setCustomSkill] = useState('');
  const [customExperienceSkill, setCustomExperienceSkill] = useState('');
  const [saveState, setSaveState] = useState('idle');
  const [saveMessage, setSaveMessage] = useState('');
  const [showCelebration, setShowCelebration] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [resumeFile, setResumeFile] = useState(null);
  const [resumeError, setResumeError] = useState('');

  useEffect(() => {
    let active = true;

    (async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const user = session?.user ?? null;

      if (!active) return;

      if (!user) {
        setIsLoadingProfile(false);
        return;
      }

      const existing = await loadOnboardingProfile();
      if (!active) return;

      if (existing) {
        setProfile(profileFromExisting(existing));
      }
      setIsLoadingProfile(false);
    })();

    return () => {
      active = false;
    };
  }, []);

  const canGoNext = step < steps.length - 1;
  const visibleCareerInterests = [
    ...careerInterestOptions,
    ...profile.careerInterests.filter((interest) => !careerInterestOptions.includes(interest)),
  ];
  const visibleSkillOptions = [
    ...skillOptions,
    ...profile.currentSkills.filter((skill) => !skillOptions.includes(skill)),
  ];

  const updateProfile = (field, value) => {
    setProfile((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const updateExperience = (field, value) => {
    setExperienceDraft((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const toggleExperienceSkill = (skill) => {
    setExperienceDraft((current) => {
      const exists = current.skillsUsed.includes(skill);
      return {
        ...current,
        skillsUsed: exists ? current.skillsUsed.filter((s) => s !== skill) : [...current.skillsUsed, skill],
      };
    });
  };

  const addExperienceCustomSkill = (value) => {
    const clean = value.trim();
    if (!clean) return;
    setExperienceDraft((current) => ({
      ...current,
      skillsUsed: current.skillsUsed.includes(clean) ? current.skillsUsed : [...current.skillsUsed, clean],
    }));
    setCustomExperienceSkill('');
  };

  const toggleListValue = (field, value) => {
    setProfile((current) => {
      const exists = current[field].includes(value);
      return {
        ...current,
        [field]: exists
          ? current[field].filter((item) => item !== value)
          : [...current[field], value],
      };
    });
  };

  const addCustomValue = (field, value, reset) => {
    const cleanValue = value.trim();
    if (!cleanValue) return;
    setProfile((current) => ({
      ...current,
      [field]: current[field].includes(cleanValue) ? current[field] : [...current[field], cleanValue],
    }));
    reset('');
  };

  const addExperience = () => {
    const hasContent = Object.values(experienceDraft).some((value) => {
      if (typeof value === 'boolean') return false;
      if (Array.isArray(value)) return value.length > 0;
      return value.trim();
    });

    if (!hasContent) return;

    setProfile((current) => ({
      ...current,
      experiences: [
        ...current.experiences,
        {
          ...experienceDraft,
          id: crypto.randomUUID(),
        },
      ],
    }));
    setExperienceDraft({ ...emptyExperience });
  };

  const removeExperience = (id) => {
    setProfile((current) => ({
      ...current,
      experiences: current.experiences.filter((experience) => experience.id !== id),
    }));
  };

  const handleResumeSelect = (event) => {
    const file = event.target.files?.[0] || null;
    setResumeError('');

    if (file) {
      const validationError = validateResumeFile(file);
      if (validationError) {
        setResumeError(validationError);
        event.target.value = '';
        return;
      }
    }

    setResumeFile(file);
  };

  const handleSubmit = async () => {
    setSaveState('saving');
    setSaveMessage('');

    try {
      let profileToSave = profile;

      if (resumeFile) {
        setSaveMessage('Uploading resume...');
        const { path } = await uploadResume(resumeFile);
        profileToSave = { ...profile, resumeUrl: path };
        setProfile(profileToSave);
        setSaveMessage('');
      }

      await saveOnboardingProfile(profileToSave);
      setSaveState('saved');
      setSaveMessage('Profile saved. Opening your dashboard...');
      setShowCelebration(true);
      window.setTimeout(() => {
        window.location.assign('/discover');
      }, 1600);
    } catch (error) {
      setSaveState('error');
      setSaveMessage(error.message || 'Something went wrong while saving.');
    }
  };

  // Lets someone move on without filling anything in — onboarding never
  // wrote to the DB until this point (handleSubmit is the only writer), so
  // skipping is just "go to the dashboard now" with nothing to undo.
  const handleSkip = () => {
    window.location.assign('/discover');
  };

  if (isLoadingProfile) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#fffdf9_0%,#fff8f2_42%,#f8f6ff_100%)] text-[#131114]">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#79808B]">Loading your profile…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf9_0%,#fff8f2_42%,#f8f6ff_100%)] text-[#131114]">
      {showCelebration && <CelebrationOverlay />}
      <section className="mx-auto flex w-full max-w-[820px] flex-col px-5 pt-12 pb-16 sm:px-8 sm:pt-20 sm:pb-24">
        {/* Header with Logo */}
        <header className="mb-5 flex shrink-0 items-center justify-between gap-2.5">
          <div className="flex items-center gap-2.5">
            <div className="relative h-5 w-5">
              <span className="absolute left-0 top-0 h-3 w-3 border-[3px] border-black" />
              <span className="absolute bottom-0 right-0 h-3 w-3 border-[3px] border-black bg-[#fffdf9]" />
            </div>
            <span className="text-base font-semibold tracking-tight text-black">OwnMove</span>
          </div>

          {/* Quiet, always-available exit from onboarding — a pill rather
              than a plain text link so it reads as a real, tappable action
              instead of stray copy, but kept low-contrast/outlined (vs. the
              solid purple Continue/Finish button below) so it never
              competes with actually completing the profile. */}
          <button
            type="button"
            onClick={handleSkip}
            className="group flex shrink-0 items-center gap-1 rounded-full border border-[#E5E7EB] bg-white/70 py-1.5 pl-3.5 pr-2.5 text-xs font-semibold text-[#6B7280] backdrop-blur-sm transition hover:border-[#DFE2E7] hover:bg-white hover:text-black"
          >
            Skip for now
            <svg
              className="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="2.5"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
        </header>

        {/* Progress Bars */}
        <div className="mb-5 shrink-0">
          <ProgressBars step={step} onStep={setStep} />
        </div>

        {/* Step Header */}
        <div className="mb-6 shrink-0">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#79808B]">
            Step {step + 1} of {steps.length}
          </p>
          <h1 className="mt-2 text-[clamp(1.4rem,2.5vw,1.85rem)] font-semibold leading-[1.1] tracking-tight text-black">
            {step === 0 && 'Tell us about yourself'}
            {step === 1 && 'Choose your interests and skills'}
            {step === 2 && 'Add your experience'}
            {step === 3 && 'Finish your profile'}
          </h1>
          <p className="mt-2 max-w-[700px] text-sm leading-6 text-[#6B7280]">
            {step === 0 && 'A quick intro plus your academic background — this is what personalizes your career roadmap.'}
            {step === 1 && 'Pick the tracks and skills that describe you, and the role you’re aiming for. Add your own if something is missing.'}
            {step === 2 && 'Add experiences like LinkedIn: role, organization, dates, and what you worked on.'}
            {step === 3 && 'Add the final links and resume so your dashboard starts with the right context.'}
          </p>
        </div>

        {/* Form Content */}
        <div className="space-y-4">
            {step === 0 && (
              <>
                <Field label="Full name">
                  <TextInput value={profile.fullName} onChange={(event) => updateProfile('fullName', event.target.value)} placeholder="e.g. Ansh Gautam" />
                </Field>

                <Field label="Headline">
                  <TextInput value={profile.headline} onChange={(event) => updateProfile('headline', event.target.value)} placeholder="e.g. Aspiring Frontend Engineer" />
                </Field>

                <Field label="Short bio">
                  <TextArea value={profile.bio} onChange={(event) => updateProfile('bio', event.target.value)} placeholder="A couple of lines about who you are and what you're working toward." />
                </Field>

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="City">
                    <TextInput value={profile.city} onChange={(event) => updateProfile('city', event.target.value)} placeholder="e.g. Delhi" />
                  </Field>

                  <Field label="Country">
                    <TextInput value={profile.country} onChange={(event) => updateProfile('country', event.target.value)} placeholder="e.g. India" />
                  </Field>
                </div>

                <div className="border-t border-[#E5E7EB] pt-4">
                  <h2 className="mb-2.5 text-sm font-semibold text-[#131114]">Education</h2>

                  <Field label="College name">
                    <TextInput value={profile.collegeName} onChange={(event) => updateProfile('collegeName', event.target.value)} placeholder="e.g. Delhi Technological University" />
                  </Field>

                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    <Field label="Current education level">
                      <SelectInput
                        value={profile.educationLevel}
                        onChange={(value) => updateProfile('educationLevel', value)}
                        placeholder="Select education level"
                        options={educationLevels}
                      />
                    </Field>

                    <Field label="Degree">
                      <SelectInput
                        value={profile.degree}
                        onChange={(value) => updateProfile('degree', value)}
                        placeholder="Select degree"
                        options={degreeOptions}
                      />
                    </Field>
                  </div>

                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    <Field label="Branch">
                      <SelectInput
                        value={profile.branch}
                        onChange={(value) => updateProfile('branch', value)}
                        placeholder="Select branch"
                        options={branchOptions}
                      />
                    </Field>

                    <Field label="Graduation year">
                      <TextInput type="number" min="2024" max="2040" value={profile.graduationYear} onChange={(event) => updateProfile('graduationYear', event.target.value)} placeholder="e.g. 2028" />
                    </Field>
                  </div>

                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    <Field label="Major">
                      <TextInput value={profile.major} onChange={(event) => updateProfile('major', event.target.value)} placeholder="e.g. AI, Marketing, Finance" />
                    </Field>

                    <Field label="Graduation status">
                      <SelectInput
                        value={profile.graduationStatus}
                        onChange={(value) => updateProfile('graduationStatus', value)}
                        placeholder="Select status"
                        options={graduationStatusOptions}
                      />
                    </Field>
                  </div>
                </div>
              </>
            )}

            {step === 1 && (
              <>
                <div>
                  <h2 className="text-sm font-semibold mb-2.5 text-[#131114]">Career interests</h2>
                  <div className="flex flex-wrap gap-1.5">
                    {visibleCareerInterests.map((interest) => (
                      <Chip key={interest} active={profile.careerInterests.includes(interest)} onClick={() => toggleListValue('careerInterests', interest)}>
                        {interest}
                      </Chip>
                    ))}
                  </div>
                  <div className="mt-3 flex gap-2">
                    <TextInput value={customInterest} onChange={(event) => setCustomInterest(event.target.value)} placeholder="Add interest..." />
                    <button type="button" onClick={() => addCustomValue('careerInterests', customInterest, setCustomInterest)} className="h-10 shrink-0 rounded-[12px] bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] px-4 text-sm font-semibold text-white shadow-[0_8px_16px_rgba(101,89,227,0.14)] transition hover:translate-y-[-0.5px]">
                      Add
                    </button>
                  </div>
                </div>

                <div className="border-t border-[#E5E7EB] pt-4">
                  <h2 className="text-sm font-semibold mb-2.5 mt-4 text-[#131114]">Current skills</h2>
                  <div className="flex flex-wrap gap-1.5">
                    {visibleSkillOptions.map((skill) => (
                      <Chip key={skill} active={profile.currentSkills.includes(skill)} onClick={() => toggleListValue('currentSkills', skill)}>
                        {skill}
                      </Chip>
                    ))}
                  </div>
                  <div className="mt-3 flex gap-2">
                    <TextInput value={customSkill} onChange={(event) => setCustomSkill(event.target.value)} placeholder="Add another skill" />
                    <button type="button" onClick={() => addCustomValue('currentSkills', customSkill, setCustomSkill)} className="h-10 shrink-0 rounded-[12px] bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] px-4 text-sm font-semibold text-white shadow-[0_8px_16px_rgba(101,89,227,0.14)] transition hover:translate-y-[-0.5px]">
                      Add
                    </button>
                  </div>
                </div>

                <div className="border-t border-[#E5E7EB] pt-4">
                  <h2 className="mb-2.5 mt-4 text-sm font-semibold text-[#131114]">Career goals</h2>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label="Target role">
                      <TextInput value={profile.targetRole} onChange={(event) => updateProfile('targetRole', event.target.value)} placeholder="e.g. Frontend Engineer" />
                    </Field>

                    <Field label="Target company (optional)">
                      <TextInput value={profile.targetCompany} onChange={(event) => updateProfile('targetCompany', event.target.value)} placeholder="e.g. Notion" />
                    </Field>
                  </div>
                </div>
              </>
            )}

            {step === 2 && (
              <>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Title">
                    <TextInput value={experienceDraft.title} onChange={(event) => updateExperience('title', event.target.value)} placeholder="e.g. Frontend Intern" />
                  </Field>

                  <Field label="Company or organization">
                    <TextInput value={experienceDraft.company} onChange={(event) => updateExperience('company', event.target.value)} placeholder="e.g. Campus AI Club" />
                  </Field>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Employment type">
                    <SelectInput
                      value={experienceDraft.experienceType}
                      onChange={(value) => updateExperience('experienceType', value)}
                      placeholder="Select type"
                      options={employmentTypes}
                    />
                  </Field>

                  <Field label="Location">
                    <TextInput value={experienceDraft.location} onChange={(event) => updateExperience('location', event.target.value)} placeholder="e.g. Remote, Delhi" />
                  </Field>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Start date">
                    <TextInput type="date" value={experienceDraft.startDate} onChange={(event) => updateExperience('startDate', event.target.value)} />
                  </Field>

                  <Field label="End date">
                    <TextInput type="date" value={experienceDraft.endDate} onChange={(event) => updateExperience('endDate', event.target.value)} disabled={experienceDraft.currentlyWorking} />
                  </Field>
                </div>

                <label className="flex items-center gap-2 text-sm font-medium text-[#131114]">
                  <input
                    type="checkbox"
                    checked={experienceDraft.currentlyWorking}
                    onChange={(event) => updateExperience('currentlyWorking', event.target.checked)}
                    className="h-4 w-4 accent-[#7b62e8]"
                  />
                  I am currently working here
                </label>

                <Field label="Description">
                  <TextArea value={experienceDraft.description} onChange={(event) => updateExperience('description', event.target.value)} placeholder="Share what you worked on, what you learned, and your impact." />
                </Field>

                <div>
                  <h2 className="mb-2.5 text-sm font-semibold text-[#131114]">Skills used in this role</h2>
                  <div className="flex flex-wrap gap-1.5">
                    {skillOptions.map((skill) => (
                      <Chip key={skill} active={experienceDraft.skillsUsed.includes(skill)} onClick={() => toggleExperienceSkill(skill)}>
                        {skill}
                      </Chip>
                    ))}
                    {experienceDraft.skillsUsed.filter((skill) => !skillOptions.includes(skill)).map((skill) => (
                      <Chip key={skill} active onClick={() => toggleExperienceSkill(skill)}>
                        {skill}
                      </Chip>
                    ))}
                  </div>
                  <div className="mt-3 flex gap-2">
                    <TextInput value={customExperienceSkill} onChange={(event) => setCustomExperienceSkill(event.target.value)} placeholder="Add another skill" />
                    <button type="button" onClick={() => addExperienceCustomSkill(customExperienceSkill)} className="h-10 shrink-0 rounded-[12px] bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] px-4 text-sm font-semibold text-white shadow-[0_8px_16px_rgba(101,89,227,0.14)] transition hover:translate-y-[-0.5px]">
                      Add
                    </button>
                  </div>
                </div>

                <button type="button" onClick={addExperience} className="h-10 w-full rounded-[12px] bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] text-sm font-semibold text-white shadow-[0_8px_16px_rgba(101,89,227,0.14)] transition hover:translate-y-[-0.5px]">
                  Add experience
                </button>

                {profile.experiences.length > 0 && (
                  <div className="space-y-2 border-t border-[#E5E7EB] pt-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#79808B]">Added experiences ({profile.experiences.length})</p>
                    {profile.experiences.map((experience) => (
                      <div key={experience.id} className="rounded-[12px] border border-[#111827]/12 bg-white/70 px-4 py-3">
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-semibold text-[#131114]">{experience.title || 'Untitled'}</p>
                            <p className="mt-1 text-xs text-[#6B7280]">
                              {[experience.company, experience.experienceType, experience.location].filter(Boolean).join(' • ') || 'Details not added'}
                            </p>
                            {experience.skillsUsed?.length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-1">
                                {experience.skillsUsed.map((skill) => (
                                  <span key={skill} className="rounded-full border border-[#111827]/10 bg-white px-2 py-0.5 text-[10.5px] font-semibold text-[#4a4a48]">{skill}</span>
                                ))}
                              </div>
                            )}
                          </div>
                          <button type="button" onClick={() => removeExperience(experience.id)} className="shrink-0 text-xs font-semibold text-[#79808B] transition hover:text-black">
                            ✕
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {step === 3 && (
              <>
                <Field label="GitHub profile link">
                  <TextInput value={profile.githubUrl} onChange={(event) => updateProfile('githubUrl', event.target.value)} placeholder="https://github.com/yourname" />
                </Field>

                <Field label="LinkedIn profile link">
                  <TextInput value={profile.linkedinUrl} onChange={(event) => updateProfile('linkedinUrl', event.target.value)} placeholder="https://linkedin.com/in/yourname" />
                </Field>

                <Field label="Resume">
                  <label className="flex h-10 w-full cursor-pointer items-center justify-between rounded-[12px] border border-[#DFE2E7] bg-white px-4 text-sm text-[#131114] transition hover:border-[#b0b5c1]">
                    <span className={resumeFile || profile.resumeUrl ? 'text-[#131114]' : 'text-[#9AA0AA]'}>
                      {resumeFile ? resumeFile.name : profile.resumeUrl ? 'Resume on file — choose a file to replace it' : 'Upload PDF or DOCX (max 5MB)'}
                    </span>
                    <span className="shrink-0 text-xs font-semibold text-[#7b62e8]">Browse</span>
                    <input type="file" accept=".pdf,.doc,.docx" className="hidden" onChange={handleResumeSelect} />
                  </label>
                  {resumeError && <p className="mt-1.5 text-xs font-medium text-red-600">{resumeError}</p>}
                </Field>

                <div className="mt-6 rounded-[18px] border border-[#111827]/12 bg-white/70 p-5 shadow-[0_10px_24px_rgba(17,24,39,0.04)]">
                  <p className="text-sm font-semibold text-black">Ready to launch</p>
                  <p className="mt-2 text-sm leading-6 text-[#6B7280]">
                    We will save your profile to your account and open your dashboard.
                  </p>
                </div>
              </>
            )}
          </div>

        {/* Footer Navigation */}
        <div className="mt-8 flex shrink-0 items-center justify-between border-t border-[#E5E7EB] pt-5">
          <button
            type="button"
            onClick={() => {
              if (step === 0) {
                window.location.assign('/');
              } else {
                setStep((current) => Math.max(current - 1, 0));
              }
            }}
            className="text-sm font-semibold text-[#6B7280] transition hover:text-black"
          >
            Back
          </button>

          {canGoNext ? (
            <button
              type="button"
              onClick={() => setStep((current) => Math.min(current + 1, steps.length - 1))}
              className="rounded-[12px] bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_16px_rgba(101,89,227,0.14)] transition hover:translate-y-[-0.5px]"
            >
              Continue
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={saveState === 'saving'}
              className="rounded-[12px] bg-[linear-gradient(135deg,#7b62e8_0%,#5c63ff_100%)] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_16px_rgba(101,89,227,0.14)] transition hover:translate-y-[-0.5px] disabled:opacity-60"
            >
              {saveState === 'saving' ? 'Saving...' : 'Finish'}
            </button>
          )}
        </div>

        {saveMessage && !showCelebration && (
          <p className={`mt-3 rounded-[12px] px-4 py-2 text-sm font-semibold ${
            saveState === 'error'
              ? 'bg-red-50 text-red-600'
              : 'border border-[#111827]/12 bg-white/70 text-[#6B7280]'
          }`}>
            {saveMessage}
          </p>
        )}
      </section>
    </main>
  );
}

export default OnboardingScreen;
