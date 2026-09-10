-- ---------------------------------------------------------------------------
-- RLS for coach_conversations and coach_messages.
--
-- Same ownership pattern as every other Career AI table: written by the
-- backend ON BEHALF OF the requesting user, using that user's own JWT (see
-- ai_coach/services/repository.py) — never the service-role key.
--
-- coach_conversations has `profile_id` directly, so its policies are a
-- simple `profile_id = auth.uid()` check like career_simulations'.
-- coach_messages has NO `profile_id` column of its own — ownership is
-- transitive through `conversation_id -> coach_conversations.profile_id` —
-- so its policies use an EXISTS subquery against coach_conversations
-- instead of a direct column comparison.
-- ---------------------------------------------------------------------------

alter table public.coach_conversations enable row level security;

drop policy if exists "Users can read their own coach conversations" on public.coach_conversations;
create policy "Users can read their own coach conversations"
  on public.coach_conversations for select to authenticated
  using (profile_id = auth.uid());

drop policy if exists "Users can create their own coach conversations" on public.coach_conversations;
create policy "Users can create their own coach conversations"
  on public.coach_conversations for insert to authenticated
  with check (profile_id = auth.uid());

drop policy if exists "Users can update their own coach conversations" on public.coach_conversations;
create policy "Users can update their own coach conversations"
  on public.coach_conversations for update to authenticated
  using (profile_id = auth.uid())
  with check (profile_id = auth.uid());

drop policy if exists "Users can delete their own coach conversations" on public.coach_conversations;
create policy "Users can delete their own coach conversations"
  on public.coach_conversations for delete to authenticated
  using (profile_id = auth.uid());

alter table public.coach_messages enable row level security;

drop policy if exists "Users can read messages in their own conversations" on public.coach_messages;
create policy "Users can read messages in their own conversations"
  on public.coach_messages for select to authenticated
  using (
    exists (
      select 1 from public.coach_conversations c
      where c.id = coach_messages.conversation_id and c.profile_id = auth.uid()
    )
  );

drop policy if exists "Users can create messages in their own conversations" on public.coach_messages;
create policy "Users can create messages in their own conversations"
  on public.coach_messages for insert to authenticated
  with check (
    exists (
      select 1 from public.coach_conversations c
      where c.id = coach_messages.conversation_id and c.profile_id = auth.uid()
    )
  );

-- No update/delete policy on coach_messages: a message is immutable once
-- written; deleting a conversation cascades to its messages instead.
