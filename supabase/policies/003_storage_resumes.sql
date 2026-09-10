-- ---------------------------------------------------------------------------
-- Storage bucket for resume uploads (onboarding "Finish" step).
--
-- Files are stored at `{user_id}/resume.<ext>`, so `(storage.foldername(name))[1]`
-- — the first path segment — is always the owning user's ID. That single
-- convention is what makes every policy below a plain `= auth.uid()` check,
-- same pattern as the table-level RLS in policies/001_rls.sql.
--
-- Private bucket: resumes are not public. The frontend reads them back via
-- `createSignedUrl`, not a public URL.
-- ---------------------------------------------------------------------------

insert into storage.buckets (id, name, public)
values ('resumes', 'resumes', false)
on conflict (id) do nothing;

drop policy if exists "Users can upload their own resume" on storage.objects;
create policy "Users can upload their own resume"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'resumes'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users can replace their own resume" on storage.objects;
create policy "Users can replace their own resume"
  on storage.objects for update to authenticated
  using (
    bucket_id = 'resumes'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users can read their own resume" on storage.objects;
create policy "Users can read their own resume"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'resumes'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users can delete their own resume" on storage.objects;
create policy "Users can delete their own resume"
  on storage.objects for delete to authenticated
  using (
    bucket_id = 'resumes'
    and (storage.foldername(name))[1] = auth.uid()::text
  );
