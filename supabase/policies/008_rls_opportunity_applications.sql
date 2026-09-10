-- ---------------------------------------------------------------------------
-- RLS for opportunity_applications — same shape as saved_opportunities'
-- policies in policies/001_rls.sql. A new numbered file rather than editing
-- 001 directly, matching this repo's "add new numbered files rather than
-- editing applied ones" convention (see supabase/README.md).
-- ---------------------------------------------------------------------------

alter table public.opportunity_applications enable row level security;

drop policy if exists "Users can view their own applied opportunities" on public.opportunity_applications;
create policy "Users can view their own applied opportunities"
  on public.opportunity_applications for select to authenticated
  using (user_id = auth.uid());

drop policy if exists "Users can mark opportunities as applied" on public.opportunity_applications;
create policy "Users can mark opportunities as applied"
  on public.opportunity_applications for insert to authenticated
  with check (user_id = auth.uid());

drop policy if exists "Users can unmark their applied opportunities" on public.opportunity_applications;
create policy "Users can unmark their applied opportunities"
  on public.opportunity_applications for delete to authenticated
  using (user_id = auth.uid());
