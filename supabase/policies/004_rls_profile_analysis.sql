-- ---------------------------------------------------------------------------
-- RLS for profile_analysis.
--
-- Unlike the AI tables in policies/002_rls_ai.sql (embeddings, recommendations
-- — written only by a trusted backend job via the service-role key),
-- profile_analysis is written by the backend ON BEHALF OF the requesting user,
-- using that user's own JWT (see profile_analysis/services/repository.py).
-- It therefore needs an INSERT policy, not just SELECT — same ownership
-- pattern as `experiences`.
-- ---------------------------------------------------------------------------

alter table public.profile_analysis enable row level security;

drop policy if exists "Users can read their own profile analyses" on public.profile_analysis;
create policy "Users can read their own profile analyses"
  on public.profile_analysis for select to authenticated
  using (profile_id = auth.uid());

drop policy if exists "Users can create their own profile analyses" on public.profile_analysis;
create policy "Users can create their own profile analyses"
  on public.profile_analysis for insert to authenticated
  with check (profile_id = auth.uid());

-- No update/delete policy: analyses are immutable history once written.
