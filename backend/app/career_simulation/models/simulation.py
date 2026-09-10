"""Row shapes for public.career_simulations.

Kept separate from schemas/simulation.py on purpose (same rule
profile_analysis and career_roadmap follow — see app/models/base.py's
docstring): this describes what Postgres actually stores. Unlike
`career_roadmaps` (one row per user, upserted), `career_simulations` is
append-only: every simulation run (and every comparison) inserts a new row,
written in two phases — `CareerSimulationInsert` at the start (status
'pending'), then `CareerSimulationComplete` or `CareerSimulationFail` once
the generator has run. This mirrors profile_analysis's insert-based history
more than career_roadmap's single-row-per-user upsert.

Matches the exact DDL supplied for this feature:

    create table career_simulations (
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
      constraint career_simulations_profile_id_fkey foreign key (profile_id)
        references profiles (id) on delete cascade,
      constraint career_simulations_status_check check (status = any (array['pending','completed','failed'])),
      constraint career_simulations_type_check check (simulation_type = any (array[
        'build_project','gain_experience','learn_skill','certification',
        'open_source','change_target_role','compare_moves'])),
      constraint career_simulations_verdict_check check (
        verdict is null or verdict = any (array['high_value','useful','limited_value','low_value']))
    );

Note there is deliberately no `updated_at` column here (unlike
`career_roadmaps`) — a simulation row is written once as pending and once
more on completion/failure, never edited afterward, so there is nothing an
`updated_at` timestamp would need to track."""

from datetime import datetime

from app.models.base import DBModel


class CareerSimulationRow(DBModel):
    id: str
    profile_id: str
    simulation_type: str
    target_role: str
    scenario_title: str
    scenario_input: dict
    result: dict | None = None
    verdict: str | None = None
    status: str
    model_used: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class CareerSimulationInsert(DBModel):
    """What the repository sends to create the initial `pending` row,
    before the generator has run — see `simulation_service.py`'s two-phase
    create -> generate -> complete/fail flow."""

    profile_id: str
    simulation_type: str
    target_role: str
    scenario_title: str
    scenario_input: dict
    status: str = "pending"


class CareerSimulationComplete(DBModel):
    """What the repository sends to update a row from `pending` to
    `completed`, once the generator has produced a result."""

    result: dict
    verdict: str | None = None
    model_used: str
    status: str = "completed"
    completed_at: datetime


class CareerSimulationFail(DBModel):
    """What the repository sends when the generator raises — a row that
    stays a permanent, visible `failed` record rather than being silently
    dropped, so a user's "Recent Simulations" list can honestly show a
    failed attempt rather than making it disappear."""

    status: str = "failed"
