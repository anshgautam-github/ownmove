-- ---------------------------------------------------------------------------
-- Row Level Security
--
-- RLS is the real security boundary for this product. The browser holds an
-- anon key and talks to PostgREST directly, so ANY row not protected by a
-- policy is effectively public. Every table below therefore has RLS enabled
-- and an explicit policy per operation.
--
-- The FastAPI backend does not weaken this: it forwards the user's JWT and
-- queries as that user, so the same policies apply. Only the service-role key
-- (server-side, background jobs) bypasses RLS.
-- ---------------------------------------------------------------------------

-- ============================ profiles =====================================
alter table public.profiles enable row level security;

drop policy if exists "Users can read their own profile" on public.profiles;
create policy "Users can read their own profile"
  on public.profiles for select to authenticated
  using (id = auth.uid());

drop policy if exists "Users can insert their own profile" on public.profiles;
create policy "Users can insert their own profile"
  on public.profiles for insert to authenticated
  with check (id = auth.uid());

drop policy if exists "Users can update their own profile" on public.profiles;
create policy "Users can update their own profile"
  on public.profiles for update to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());

-- =========================== experiences ===================================
alter table public.experiences enable row level security;

-- Ownership is indirect (via profiles), hence the subquery on profile_id.
drop policy if exists "Users can read their own experiences" on public.experiences;
create policy "Users can read their own experiences"
  on public.experiences for select to authenticated
  using (profile_id = auth.uid());

drop policy if exists "Users can insert their own experiences" on public.experiences;
create policy "Users can insert their own experiences"
  on public.experiences for insert to authenticated
  with check (profile_id = auth.uid());

drop policy if exists "Users can update their own experiences" on public.experiences;
create policy "Users can update their own experiences"
  on public.experiences for update to authenticated
  using (profile_id = auth.uid())
  with check (profile_id = auth.uid());

-- The app replaces experience rows wholesale on save, so delete is required.
drop policy if exists "Users can delete their own experiences" on public.experiences;
create policy "Users can delete their own experiences"
  on public.experiences for delete to authenticated
  using (profile_id = auth.uid());

-- ========================== opportunities ==================================
alter table public.opportunities enable row level security;

-- Curated content: readable by any signed-in user, writable by nobody through
-- the API. Listings are managed with the service-role key / Supabase dashboard.
-- Add an admin write policy here if you later build an admin UI.
drop policy if exists "Opportunities are readable by authenticated users" on public.opportunities;
create policy "Opportunities are readable by authenticated users"
  on public.opportunities for select to authenticated
  using (is_active = true);

-- ======================= saved_opportunities ===============================
alter table public.saved_opportunities enable row level security;

-- Scoped to the caller on every operation, so one user can never read, add to,
-- or delete from another user's saved list.
drop policy if exists "Users can view their own saved opportunities" on public.saved_opportunities;
create policy "Users can view their own saved opportunities"
  on public.saved_opportunities for select to authenticated
  using (user_id = auth.uid());

drop policy if exists "Users can save opportunities" on public.saved_opportunities;
create policy "Users can save opportunities"
  on public.saved_opportunities for insert to authenticated
  with check (user_id = auth.uid());

drop policy if exists "Users can remove their saved opportunities" on public.saved_opportunities;
create policy "Users can remove their saved opportunities"
  on public.saved_opportunities for delete to authenticated
  using (user_id = auth.uid());
