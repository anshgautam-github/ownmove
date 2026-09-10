-- ---------------------------------------------------------------------------
-- Embedding invalidation triggers — the one schema addition this feature
-- needed beyond the embedding/search_vector columns already added directly
-- on public.profiles / public.opportunities.
--
-- Why this exists: the product spec for the "For You" recommender requires
-- that profile/opportunity embeddings only regenerate "when relevant
-- fields change, or the embedding is missing" — never on every request.
-- Detecting "missing" is trivial (`embedding is null`). Detecting "changed"
-- needs *something* to compare against, and there's no source_hash/
-- updated_at column tracking that for embeddings specifically (the
-- separate profile_embeddings/opportunity_embeddings tables in
-- schema/006_ai_embeddings.sql had one — `source_hash` — but that design
-- was superseded by the direct-column approach these embedding/
-- search_vector columns represent, and was apparently never applied to
-- the live database).
--
-- Rather than add a new hash/timestamp column (a bigger, more invasive
-- schema change), these triggers reuse "missing" as the only signal the
-- application needs to check: whenever an UPDATE actually changes one of
-- the fields the embedding is built from (see backend/app/ai/embeddings/
-- generator.py's build_profile_document() / build_opportunity_document(),
-- which these two field lists must stay in sync with), the trigger just
-- clears the embedding back to NULL. EmbeddingService then regenerates it
-- lazily the next time it's needed — see backend/app/services/
-- embedding_service.py.
--
-- Same trigger-based pattern already used for search_vector on both
-- tables, just clearing a column instead of computing one.
-- ---------------------------------------------------------------------------

create or replace function public.invalidate_profile_embedding()
returns trigger
language plpgsql
as $$
begin
  if (
    new.target_role is distinct from old.target_role
    or new.target_company is distinct from old.target_company
    or new.career_interests is distinct from old.career_interests
    or new.current_skills is distinct from old.current_skills
    or new.headline is distinct from old.headline
    or new.bio is distinct from old.bio
    or new.degree is distinct from old.degree
    or new.branch is distinct from old.branch
    or new.major is distinct from old.major
  ) then
    new.embedding := null;
  end if;
  return new;
end;
$$;

drop trigger if exists profiles_invalidate_embedding on public.profiles;
create trigger profiles_invalidate_embedding
  before update on public.profiles
  for each row
  execute function public.invalidate_profile_embedding();

create or replace function public.invalidate_opportunity_embedding()
returns trigger
language plpgsql
as $$
begin
  if (
    new.title is distinct from old.title
    or new.organization is distinct from old.organization
    or new.category is distinct from old.category
    or new.description is distinct from old.description
    or new.tags is distinct from old.tags
    or new.duration is distinct from old.duration
  ) then
    new.embedding := null;
  end if;
  return new;
end;
$$;

drop trigger if exists opportunities_invalidate_embedding on public.opportunities;
create trigger opportunities_invalidate_embedding
  before update on public.opportunities
  for each row
  execute function public.invalidate_opportunity_embedding();
