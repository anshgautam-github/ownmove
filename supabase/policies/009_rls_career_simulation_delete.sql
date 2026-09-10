-- career_simulations RLS had SELECT/INSERT/UPDATE (006_rls_career_
-- simulation.sql) but no DELETE policy -- that file's own comment said
-- deletion was out of the "current feature surface" and simulations were
-- permanent records. That's now stale: the frontend ships a live "Delete"
-- action (CareerSimulationDashboard.jsx -> deleteSimulation() ->
-- DELETE /api/v1/career-ai/career-simulation/{id}), so the feature surface
-- does include deletion today. Under RLS, an enabled table with no policy
-- for an operation denies that operation outright regardless of the
-- application query's own .eq() filters -- so this delete button has been
-- silently no-op'ing (backend reports 204 success, row never actually
-- removed). This adds the missing policy; see the matching fix in
-- career_simulation/services/repository.py's delete_simulation, which now
-- raises NotFoundError instead of silently succeeding when nothing was
-- actually deleted.
drop policy if exists "Users can delete their own simulations" on public.career_simulations;
create policy "Users can delete their own simulations"
  on public.career_simulations for delete to authenticated
  using (profile_id = auth.uid());
