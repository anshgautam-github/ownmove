-- ---------------------------------------------------------------------------
-- Replaces "Evidence Credibility" with "Recruiter Signals" on
-- profile_analysis. See backend/app/profile_analysis/schemas/analysis.py's
-- RecruiterSignal docstring for the full rationale: the old section's
-- verified/partially_verified language implied this platform checks the
-- actual contents of a GitHub repo, resume file, or LinkedIn profile — it
-- never did. Recruiter Signals makes no verification claim: it names what a
-- recruiter is likely to notice scanning the profile itself, with a named
-- status tier (Strong/Moderate/Limited/Missing/Unknown) instead of an
-- invented confidence percentage.
--
-- Additive only, same convention as every other migration on this table.
-- The old `evidence_credibility` column (added in migration 014) is left in
-- place, nullable, holding whatever history already exists — nothing
-- currently reads or writes it.
-- ---------------------------------------------------------------------------

alter table public.profile_analysis
  add column if not exists recruiter_signals jsonb;
