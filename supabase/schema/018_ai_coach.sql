-- ---------------------------------------------------------------------------
-- AI Coach — context-aware career decision assistant. A conversation
-- (`coach_conversations`) holds many messages (`coach_messages`), unlike
-- career_roadmaps (one row per user) or career_simulations/profile_analysis
-- (flat append-only history) — this is a normal parent/child pair.
--
-- `title`/`conversation_type` start NULL and are filled in once, after the
-- first assistant reply classifies the conversation's intent and (if the
-- generator supplied one) suggests a short title — see
-- backend/app/ai_coach/services/coach_service.py's `_run_turn`.
-- `updated_at` is bumped on every new message so
-- `coach_conversations_profile_idx`'s `updated_at desc` ordering surfaces
-- the most recently active conversation first in the history list.
--
-- `coach_messages.structured_content` holds the full
-- `CoachStructuredResponse` for an assistant message (null for user
-- messages) — the frontend renders decision/problem_solving/evaluation
-- content from this, never from parsing `content` itself.
--
-- Matches the DDL supplied for this feature exactly; `if not exists` makes
-- this a safe no-op if the tables were already created directly against
-- the live database.
-- ---------------------------------------------------------------------------

create table if not exists coach_conversations (
  id uuid not null default gen_random_uuid (),
  profile_id uuid not null,
  title text null,
  conversation_type text null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint coach_conversations_pkey primary key (id),
  constraint coach_conversations_profile_id_fkey foreign KEY (profile_id) references profiles (id) on delete CASCADE,
  constraint coach_conversations_type_check check (
    (
      (conversation_type is null)
      or (
        conversation_type = any (
          array[
            'decision'::text,
            'prioritization'::text,
            'evaluation'::text,
            'problem_solving'::text,
            'preparation'::text,
            'general'::text
          ]
        )
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists coach_conversations_profile_idx on public.coach_conversations using btree (profile_id, updated_at desc) TABLESPACE pg_default;

create table if not exists coach_messages (
  id uuid not null default gen_random_uuid (),
  conversation_id uuid not null,
  role text not null,
  content text not null,
  structured_content jsonb null,
  created_at timestamp with time zone not null default now(),
  constraint coach_messages_pkey primary key (id),
  constraint coach_messages_conversation_id_fkey foreign KEY (conversation_id) references coach_conversations (id) on delete CASCADE,
  constraint coach_messages_role_check check (
    (
      role = any (array['user'::text, 'assistant'::text])
    )
  )
) TABLESPACE pg_default;

create index IF not exists coach_messages_conversation_idx on public.coach_messages using btree (conversation_id, created_at) TABLESPACE pg_default;
