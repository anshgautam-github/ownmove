-- ---------------------------------------------------------------------------
-- Profiles v2 — additional columns needed for AI profile analysis.
--
-- `resume_url` and `onboarding_completed` used to be added here, but both
-- already exist on the live table (added directly in the Supabase dashboard
-- at some point, never committed) — see the corrected 001_profiles.sql. This
-- file now only adds what's genuinely new. Purely additive either way: no
-- existing column is renamed, retyped or dropped.
-- ---------------------------------------------------------------------------

alter table public.profiles
  add column if not exists resume_text text,
  add column if not exists resume_updated_at timestamptz,
  add column if not exists last_active_at timestamptz;

-- Backfill, kept for any environment where onboarding_completed still has
-- its column default (false) despite the profile already being submitted.
update public.profiles
set onboarding_completed = true
where submitted_at is not null
  and onboarding_completed is distinct from true;

comment on column public.profiles.resume_text is
  'Plain-text extraction of the resume, produced by the backend on upload. '
  'This — not the PDF at resume_url — is what feeds embeddings and RAG, so '
  'the file never has to be re-parsed on every AI call.';
comment on column public.profiles.resume_updated_at is
  'Set when resume_text last changed. Lets the embedding job diff against '
  'profile_embeddings.updated_at to decide whether a re-embed is needed.';
comment on column public.profiles.last_active_at is
  'Updated on login/session refresh. Lets background jobs skip recompute '
  '(embeddings, recommendations) for dormant users. Distinct from '
  'last_profile_analysis, which tracks the AI analysis run, not general '
  'activity.';
