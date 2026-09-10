-- ---------------------------------------------------------------------------
-- Redesigns the Profile Analysis output into a "Career Intelligence Report":
-- see backend/app/profile_analysis/schemas/analysis.py and
-- backend/app/profile_analysis/README.md for the full rationale behind each
-- section. Five new jsonb columns, additive only (same convention as every
-- other migration on this table) — nothing is dropped or renamed.
--
-- profile_diagnosis        replaces the old "Executive Summary"/recruiter_view
-- career_signals            replaces career_dna (no more personality archetype)
-- profile_contradictions     replaces career_blind_spots (broader: any stated
--                            goal vs. observed evidence mismatch, not just a
--                            skill-category mismatch)
-- score_breakdown            new — the itemized, auditable math behind
--                            overall_score (see utils/scoring.py)
-- evidence_credibility       replaces evidence_scores (credibility verdict +
--                            missing evidence, not a bare skill rating)
--
-- The old columns (career_dna, recruiter_view, career_blind_spots,
-- evidence_scores) are left in place, nullable, holding whatever history
-- already exists — nothing currently reads or writes them. A row saved
-- before this migration simply won't parse into the current
-- ProfileAnalysisResponse; the backend treats that the same as "no analysis
-- yet" rather than crashing (see analysis_service.py).
-- ---------------------------------------------------------------------------

alter table public.profile_analysis
  add column if not exists profile_diagnosis jsonb,
  add column if not exists career_signals jsonb,
  add column if not exists profile_contradictions jsonb,
  add column if not exists score_breakdown jsonb,
  add column if not exists evidence_credibility jsonb;
