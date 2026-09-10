-- roadmap_activity's original INSERT policy ("Users can create their own
-- roadmap activity", 005_rls_career_roadmap.sql) only checked
-- `user_id = auth.uid()` -- it never verified the referenced roadmap_id
-- actually belongs to that same user, unlike coach_messages' correct
-- transitive EXISTS pattern for its parent conversation
-- (007_rls_ai_coach.sql). Without this, a user who knows (or guesses)
-- another user's career_roadmaps.id could insert a fabricated activity row
-- against it. The app's own legitimate write always passes a roadmap_id
-- that already belongs to the same user (career_roadmap/services/
-- repository.py's log_activity is called right after that same user's own
-- save_roadmap), so this tightening cannot break the existing write path.
drop policy if exists "Users can create their own roadmap activity" on public.roadmap_activity;
create policy "Users can create their own roadmap activity"
  on public.roadmap_activity for insert to authenticated
  with check (
    user_id = auth.uid()
    and exists (
      select 1 from public.career_roadmaps
      where career_roadmaps.id = roadmap_activity.roadmap_id
        and career_roadmaps.user_id = auth.uid()
    )
  );
