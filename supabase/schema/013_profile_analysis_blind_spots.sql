-- ---------------------------------------------------------------------------
-- Adds `career_blind_spots` to `profile_analysis` — a new analysis section,
-- distinct from `missing_signals`. Missing Signals says "you don't have
-- GitHub" (an absence); Career Blind Spots says "you're spending effort on
-- things that won't move your stated target role" (a misdirection). See
-- backend/app/profile_analysis/schemas/analysis.py's CareerBlindSpot and
-- backend/app/profile_analysis/README.md for the full rationale.
--
-- Nullable and additive, same as every other analysis-section column on this
-- table — existing rows simply have `null` here, which the frontend renders
-- as "not enough evidence to assess" (an empty array), not an error.
-- ---------------------------------------------------------------------------

alter table public.profile_analysis
  add column if not exists career_blind_spots jsonb;
