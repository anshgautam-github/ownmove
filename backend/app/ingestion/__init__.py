"""Opportunity Ingestion Framework.

A self-contained vertical slice, same convention as `app.profile_analysis`,
`app.career_roadmap`, `app.career_simulation` and `app.ai_coach` — it owns its
own `models/services/utils`, rather than spreading across the top-level
`app/models`, `app/services`, `app/utils` layers.

This module is the FRAMEWORK only. See `README.md` in this directory for the
full design; in short:

- `models/`   Typed, pipeline-internal DTOs (discovered URLs, raw extracted
              content, normalized opportunities, validation/run results).
              These are NOT database rows — see the README for why this
              deviates from the repo-wide `schemas/` vs `models/` split.
- `agents/`   `BaseOpportunityAgent` — the interface every source-specific
              scraper implements — plus `AgentRegistry`, the single place new
              sources register themselves.
- `pipeline/` `IngestionPipeline` — orchestrates discover -> extract ->
              normalize -> validate for any agent. Shared by every source.
- `jobs/`     Configurable per-agent schedules (`ScheduleConfig`) and a
              registry of them. No scheduler daemon is wired up yet.
- `services/` `IngestionService` — runs agents through the pipeline (never
              touches Supabase). `OpportunityService` — the ONLY layer
              allowed to talk to Supabase for opportunity ingestion:
              validates, deduplicates (by fingerprint and by
              source/source_id), inserts/updates, and queues AI
              enrichment for what `IngestionService` produces.
- `utils/`    Retry, rate limiting, structured logging, fingerprinting, and
              validation helpers reused by every agent and by
              `OpportunityService`.

No source-specific crawler lives here yet. `IngestionPipeline.run()` itself
still never touches the database — it returns normalized, validated
`NormalizedOpportunity` objects in memory; persisting them is
`OpportunityService`'s job, called separately, so an agent/crawler never
needs any database logic of its own (see README "No crawler talks to
Supabase").
"""
