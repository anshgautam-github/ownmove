import { supabase } from './client';

const RESUME_MAX_BYTES = 5 * 1024 * 1024;
const RESUME_ALLOWED_EXTENSIONS = ['pdf', 'doc', 'docx'];
// Not every browser/OS file picker reports a MIME type for every format, so
// this is only checked when one IS present — it's a second check on top of
// the extension, not a replacement for it.
const RESUME_ALLOWED_MIME_TYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];

// Shared by every "upload a resume" UI (Onboarding, Profile edit) so the
// same rules and messages apply everywhere rather than drifting apart.
// Returns a user-facing error string, or null if the file is fine to upload.
export function validateResumeFile(file) {
  if (!file) return 'No file selected.';

  const extension = (file.name.split('.').pop() || '').toLowerCase();
  if (!RESUME_ALLOWED_EXTENSIONS.includes(extension)) {
    return 'Please upload a PDF, DOC, or DOCX file.';
  }

  if (file.type && !RESUME_ALLOWED_MIME_TYPES.includes(file.type)) {
    return "That file doesn't look like a PDF, DOC, or DOCX. Please choose a different file.";
  }

  if (file.size === 0) {
    return 'That file appears to be empty.';
  }

  if (file.size > RESUME_MAX_BYTES) {
    return 'Resume must be under 5MB.';
  }

  return null;
}

function toProfileRow(userId, profile) {
  return {
    id: userId,
    full_name: profile.fullName || null,
    headline: profile.headline || null,
    bio: profile.bio || null,
    city: profile.city || null,
    country: profile.country || null,
    college_name: profile.collegeName || null,
    education_level: profile.educationLevel || null,
    degree: profile.degree || null,
    branch: profile.branch || null,
    major: profile.major || null,
    graduation_year: profile.graduationYear ? Number(profile.graduationYear) : null,
    graduation_status: profile.graduationStatus || null,
    career_interests: profile.careerInterests || [],
    current_skills: profile.currentSkills || [],
    target_role: profile.targetRole || null,
    target_company: profile.targetCompany || null,
    github_url: profile.githubUrl || null,
    linkedin_url: profile.linkedinUrl || null,
    resume_url: profile.resumeUrl || null,
    submitted_at: new Date().toISOString(),
    onboarding_completed: true,
    updated_at: new Date().toISOString(),
  };
}

function toExperienceRows(userId, experiences) {
  return experiences.map((experience) => ({
    profile_id: userId,
    title: experience.title || null,
    company: experience.company || null,
    experience_type: experience.experienceType || null,
    location: experience.location || null,
    start_date: experience.startDate || null,
    end_date: experience.currentlyWorking ? null : experience.endDate || null,
    currently_working: !!experience.currentlyWorking,
    description: experience.description || null,
    skills_used: experience.skillsUsed || [],
  }));
}

function fromProfileRow(row) {
  return {
    fullName: row.full_name,
    email: row.email,
    profilePhoto: row.profile_photo,
    headline: row.headline,
    bio: row.bio,
    city: row.city,
    country: row.country,
    collegeName: row.college_name,
    educationLevel: row.education_level,
    degree: row.degree,
    branch: row.branch,
    major: row.major,
    graduationYear: row.graduation_year,
    graduationStatus: row.graduation_status,
    careerInterests: row.career_interests || [],
    currentSkills: row.current_skills || [],
    targetRole: row.target_role,
    targetCompany: row.target_company,
    githubUrl: row.github_url,
    linkedinUrl: row.linkedin_url,
    resumeUrl: row.resume_url,
    profileScore: row.profile_score,
    aiProfileSummary: row.ai_profile_summary,
    experiences: (row.experiences || []).map((experience) => ({
      id: experience.id,
      title: experience.title,
      company: experience.company,
      experienceType: experience.experience_type,
      location: experience.location,
      startDate: experience.start_date,
      endDate: experience.end_date,
      currentlyWorking: experience.currently_working,
      description: experience.description,
      skillsUsed: experience.skills_used || [],
    })),
  };
}

// Google OAuth (the only sign-in path today) already gives us name, email and
// an avatar — no reason to make the user retype them during onboarding. Only
// fields the profile doesn't already have are filled in from the session, so
// this never clobbers something the user has already edited.
function identityFromSession(user, profile) {
  const metadata = user.user_metadata || {};
  return {
    fullName: profile.fullName || metadata.full_name || metadata.name || '',
    email: profile.email || user.email || '',
    profilePhoto: profile.profilePhoto || metadata.avatar_url || metadata.picture || '',
  };
}

export async function saveOnboardingProfile(profile) {
  const {
    data: { session },
    error: userError,
  } = await supabase.auth.getSession();
  const user = session?.user ?? null;

  if (userError || !user) {
    throw new Error('You need to be signed in to save your profile.');
  }

  const enrichedProfile = { ...profile, ...identityFromSession(user, profile) };
  const profileRow = toProfileRow(user.id, enrichedProfile);
  // auth_provider comes from the Supabase session itself, not the form.
  profileRow.auth_provider = user.app_metadata?.provider || 'email';

  const { error: profileError } = await supabase.from('profiles').upsert(profileRow);
  if (profileError) {
    throw new Error(profileError.message);
  }

  // Replace the experience rows wholesale so edits/removals on resubmit stay in sync.
  const { error: deleteError } = await supabase
    .from('experiences')
    .delete()
    .eq('profile_id', user.id);
  if (deleteError) {
    throw new Error(deleteError.message);
  }

  const experiences = profile.experiences || [];
  if (experiences.length > 0) {
    const { error: experiencesError } = await supabase
      .from('experiences')
      .insert(toExperienceRows(user.id, experiences));
    if (experiencesError) {
      throw new Error(experiencesError.message);
    }
  }

  return { saved: true };
}

export async function loadOnboardingProfile() {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const user = session?.user ?? null;

  if (!user) {
    return null;
  }

  const { data: row, error } = await supabase
    .from('profiles')
    .select('*, experiences(*)')
    .eq('id', user.id)
    .maybeSingle();

  if (error || !row) {
    return null;
  }

  return fromProfileRow(row);
}

// Resumes live in a private bucket at `{user_id}/resume.<ext>` — one file per
// user, so re-uploading naturally replaces the old one (upsert: true) rather
// than accumulating orphaned files. Requires the bucket + policies in
// supabase/policies/003_storage_resumes.sql.
export async function uploadResume(file) {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const user = session?.user ?? null;

  if (!user) {
    throw new Error('You need to be signed in to upload a resume.');
  }

  const extension = file.name.split('.').pop() || 'pdf';
  const path = `${user.id}/resume.${extension}`;

  const { error: uploadError } = await supabase.storage
    .from('resumes')
    .upload(path, file, { upsert: true, contentType: file.type || undefined });

  if (uploadError) {
    throw new Error(uploadError.message);
  }

  return { path };
}

// The bucket is private, so the stored path isn't directly viewable — hand
// back a time-limited signed URL for the "view resume" link in Profile/onboarding.
export async function getResumeSignedUrl(path, expiresInSeconds = 3600) {
  const { data, error } = await supabase.storage
    .from('resumes')
    .createSignedUrl(path, expiresInSeconds);

  if (error) {
    throw new Error(error.message);
  }

  return data.signedUrl;
}
