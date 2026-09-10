"""Row shapes for public.coach_conversations and public.coach_messages.

Kept separate from schemas/coach.py on purpose (same rule every other
Career AI module follows — see app/models/base.py's docstring). Matches
the exact DDL supplied for this feature:

    create table coach_conversations (
      id uuid not null default gen_random_uuid (),
      profile_id uuid not null,
      title text null,
      conversation_type text null,
      created_at timestamp with time zone not null default now(),
      updated_at timestamp with time zone not null default now(),
      constraint coach_conversations_pkey primary key (id),
      constraint coach_conversations_profile_id_fkey foreign key (profile_id)
        references profiles (id) on delete cascade,
      constraint coach_conversations_type_check check (
        conversation_type is null or conversation_type = any (array[
          'decision','prioritization','evaluation','problem_solving',
          'preparation','general']))
    );

    create table coach_messages (
      id uuid not null default gen_random_uuid (),
      conversation_id uuid not null,
      role text not null,
      content text not null,
      structured_content jsonb null,
      created_at timestamp with time zone not null default now(),
      constraint coach_messages_pkey primary key (id),
      constraint coach_messages_conversation_id_fkey foreign key (conversation_id)
        references coach_conversations (id) on delete cascade,
      constraint coach_messages_role_check check (role = any (array['user','assistant']))
    );

`coach_conversations` is NOT append-only history in the profile_analysis
sense and NOT one-row-per-user in the career_roadmaps sense — it is a
normal parent/child pair: one conversation row, many message rows,
`updated_at` bumped on the conversation each time a message is added (so
`coach_conversations_profile_idx`'s `updated_at desc` ordering surfaces the
most recently active conversation first in the history list)."""

from datetime import datetime

from app.models.base import DBModel


class CoachConversationRow(DBModel):
    id: str
    profile_id: str
    title: str | None = None
    conversation_type: str | None = None
    created_at: datetime
    updated_at: datetime


class CoachConversationInsert(DBModel):
    profile_id: str
    title: str | None = None
    conversation_type: str | None = None


class CoachMessageRow(DBModel):
    id: str
    conversation_id: str
    role: str
    content: str
    structured_content: dict | None = None
    created_at: datetime


class CoachMessageInsert(DBModel):
    conversation_id: str
    role: str
    content: str
    structured_content: dict | None = None
