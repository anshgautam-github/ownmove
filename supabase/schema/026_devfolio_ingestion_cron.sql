-- Schedules the Devfolio hackathon ingestion route
-- (`POST /api/v1/ingestion/run/devfolio` on the deployed FastAPI backend --
-- see `backend/app/api/v1/routes/ingestion.py`) to run every 3 days via
-- Supabase's own `pg_cron` + `pg_net` extensions. No new backend
-- infrastructure (no Celery, no Redis, no separate scheduler service) --
-- Supabase's Postgres instance is the "always-on" piece that wakes the
-- Render-hosted backend on a schedule, since the backend itself is not
-- guaranteed to be running continuously (free/low-tier Render Web
-- Services can spin down between requests).
--
-- WHY THIS CALLS `/ingestion/run/devfolio` DIRECTLY, NOT `/ingestion/run-due`:
-- `/ingestion/run-due` only runs a source when `JobRegistry.due_sources()`
-- says it's due, which is computed from `JobRegistry._last_run_at` (see
-- `backend/app/ingestion/jobs/registry.py`) -- a PLAIN IN-MEMORY DICT on a
-- process-wide singleton, never persisted to the database or disk. Every
-- time the Render process restarts (a redeploy, a crash, or the free
-- tier's own spin-down-on-idle / cold-start-on-request behavior) that
-- state resets to "never run", which would make `run-due` unreliable as
-- the thing enforcing a true 3-day cadence in production -- it could fire
-- far more often than every 3 days depending on how often Render recycles
-- the process. `/ingestion/run/devfolio` has no such dependency: it always
-- runs on demand, right now, regardless of any in-memory schedule state
-- (see `run_source()` in that same routes file) -- so an EXTERNAL,
-- durable scheduler (this file) is what actually owns the "every 3 days"
-- cadence, not the backend's own in-memory `ScheduleConfig`.
--
-- SECRET HANDLING -- READ BEFORE RUNNING THIS FILE:
-- This file deliberately contains NO raw secret value anywhere. It reads
-- the ingestion admin key at run time from Supabase Vault
-- (`vault.decrypted_secrets`), by name only. Before running this file for
-- the first time, store the real key ONCE, interactively, directly in the
-- Supabase SQL Editor (NOT as part of this committed file, and not from
-- any script that gets saved to disk or committed to git):
--
--   select vault.create_secret(
--     'PASTE_YOUR_REAL_X-INGESTION-ADMIN-KEY_VALUE_HERE',
--     'devfolio_ingestion_admin_key',
--     'X-Ingestion-Admin-Key for POST /api/v1/ingestion/run/devfolio on Render'
--   );
--
-- Run that single statement by itself in the SQL Editor, then discard it
-- (don't save that version anywhere). Everything below only ever
-- references the secret by its name, 'devfolio_ingestion_admin_key' --
-- never its value.
--
-- Also update `_devfolio_ingestion_url` just below to your actual Render
-- URL before running this file. That URL is not sensitive (it's a public
-- HTTPS endpoint requiring the header above to do anything), so it's fine
-- to commit as plain text.
--
-- Idempotent / safe to re-run (matches this repo's existing seeds/
-- convention): unschedules any prior job of the same name first, so
-- running this file twice updates the one job rather than creating a
-- duplicate.

create extension if not exists pg_cron with schema extensions;
create extension if not exists pg_net with schema extensions;

do $$
begin
  if exists (select 1 from cron.job where jobname = 'devfolio-ingestion-every-3-days') then
    perform cron.unschedule('devfolio-ingestion-every-3-days');
  end if;
end $$;

-- Cron expressions in Supabase-managed pg_cron run in UTC. Verify this for
-- your own project with:  select * from pg_settings where name = 'cron.timezone';
-- '0 12 */3 * *' = 12:00 UTC, on day-of-month 3, 6, 9, ... 30. This is the
-- closest practical approximation of "every 3 days" that standard cron
-- syntax can express -- see this change's accompanying notes for the small
-- (1-day, at most) drift this introduces at some month boundaries, which
-- is not worth a more complex solution for a hackathon-listing refresh.
select cron.schedule(
  'devfolio-ingestion-every-3-days',
  '0 12 */3 * *',
  $$
  select net.http_post(
    url := 'https://YOUR-RENDER-APP.onrender.com/api/v1/ingestion/run/devfolio',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Ingestion-Admin-Key', (
        select decrypted_secret
        from vault.decrypted_secrets
        where name = 'devfolio_ingestion_admin_key'
      )
    ),
    timeout_milliseconds := 300000
  ) as request_id;
  $$
);

-- Verification queries (see chat for the full walkthrough):
--   select * from cron.job where jobname = 'devfolio-ingestion-every-3-days';
--   select * from cron.job_run_details order by start_time desc limit 5;
--   select id, status_code, content, created from net._http_response order by created desc limit 5;
