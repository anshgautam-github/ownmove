-- ---------------------------------------------------------------------------
-- Career Simulation — "what would change in my profile if I did X?"
-- decision-support tool. Distinct from career_roadmap (how to progress) and
-- profile_analysis (current-state diagnosis): this evaluates the
-- INCREMENTAL VALUE of one (or two, compared) hypothetical career actions
-- against the candidate's real, current profile.
--
-- Append-only, like profile_analysis — NOT one-row-per-user like
-- career_roadmaps. Every simulation or comparison run inserts a new row,
-- written in two phases: an initial `status = 'pending'` insert before the
-- LLM call, then an update to `status = 'completed'` (with `result`/
-- `verdict`/`model_used`/`completed_at`) or `status = 'failed'` — see
-- backend/app/career_simulation/services/simulation_service.py.
--
-- `simulation_type` covers seven values (A-G in the product spec):
-- build_project, gain_experience, learn_skill, certification, open_source,
-- change_target_role, and compare_moves (the last is set only when
-- persisting a "compare two moves" result, never sent directly by a
-- create-one request).
--
-- `verdict` is intentionally a flat, lowercase snake_case text column
-- (high_value/useful/limited_value/low_value) or NULL — NULL is used for
-- `compare_moves` rows, where a single headline verdict doesn't apply; the
-- comparison's "better fit" lives inside `result` instead. The richer,
-- UPPERCASE `result.verdict.level` inside the jsonb blob is the generator's
-- literal structured output and is never itself constrained by this
-- column's CHECK — see backend/app/career_simulation/schemas/simulation.py
-- for the full mapping.
--
-- Matches the DDL supplied for this feature exactly (column-for-column,
-- constraint-for-constraint); `if not exists` makes it a safe no-op if the
-- table was already created directly against the live database.
-- ---------------------------------------------------------------------------

create table if not exists career_simulations (
  id uuid not null default gen_random_uuid (),
  profile_id uuid not null,
  simulation_type text not null,
  target_role text not null,
  scenario_title text not null,
  scenario_input jsonb not null default '{}'::jsonb,
  result jsonb null,
  verdict text null,
  status text not null default 'pending'::text,
  model_used text null,
  created_at timestamp with time zone not null default now(),
  completed_at timestamp with time zone null,
  constraint career_simulations_pkey primary key (id),
  constraint career_simulations_profile_id_fkey foreign KEY (profile_id) references profiles (id) on delete CASCADE,
  constraint career_simulations_status_check check (
    (
      status = any (
        array[
          'pending'::text,
          'completed'::text,
          'failed'::text
        ]
      )
    )
  ),
  constraint career_simulations_type_check check (
    (
      simulation_type = any (
        array[
          'build_project'::text,
          'gain_experience'::text,
          'learn_skill'::text,
          'certification'::text,
          'open_source'::text,
          'change_target_role'::text,
          'compare_moves'::text
        ]
      )
    )
  ),
  constraint career_simulations_verdict_check check (
    (
      (verdict is null)
      or (
        verdict = any (
          array[
            'high_value'::text,
            'useful'::text,
            'limited_value'::text,
            'low_value'::text
          ]
        )
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists career_simulations_profile_created_idx on public.career_simulations using btree (profile_id, created_at desc) TABLESPACE pg_default;
