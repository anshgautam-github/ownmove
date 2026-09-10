-- ---------------------------------------------------------------------------
-- RLS for career_simulations.
--
-- Same ownership pattern as profile_analysis (policies/004) and
-- career_roadmap (policies/005): written by the backend ON BEHALF OF the
-- requesting user, using that user's own JWT (see
-- career_simulation/services/repository.py) — never the service-role key.
--
-- career_simulations needs both an INSERT and an UPDATE policy, unlike
-- profile_analysis's insert-only history: the two-phase write (create
-- pending -> generate -> complete/fail) means the SAME row is inserted once
-- and then updated once by the same owning user, never by anyone else.
-- Column name here is `profile_id` (matching the supplied DDL), not
-- `user_id` as in career_roadmaps/roadmap_activity — same ownership
-- semantics (`profiles.id` is `auth.users.id`), just a different column
-- name for this table.
-- ---------------------------------------------------------------------------

alter table public.career_simulations enable row level security;

drop policy if exists "Users can read their own simulations" on public.career_simulations;
create policy "Users can read their own simulations"
  on public.career_simulations for select to authenticated
  using (profile_id = auth.uid());

drop policy if exists "Users can create their own simulations" on public.career_simulations;
create policy "Users can create their own simulations"
  on public.career_simulations for insert to authenticated
  with check (profile_id = auth.uid());

drop policy if exists "Users can update their own simulations" on public.career_simulations;
create policy "Users can update their own simulations"
  on public.career_simulations for update to authenticated
  using (profile_id = auth.uid())
  with check (profile_id = auth.uid());

-- No delete policy: a simulation is a permanent record of what was asked
-- and found, including failed attempts — never deleted from the current
-- feature surface.
