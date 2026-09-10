-- ---------------------------------------------------------------------------
-- "For You" hybrid recommendation retrieval — two RPCs, one per leg
-- (semantic / keyword), called from
-- backend/app/services/recommendation_repository.py via PostgREST's
-- .rpc(...). Ranking/merging/weighting happens in Python
-- (backend/app/services/ranking.py); these functions only retrieve
-- candidates.
--
-- Both are `language sql stable` (no `security definer`) — deliberately.
-- Per policies/001_rls.sql, RLS is the real security boundary in this
-- product, and a plain SQL function called via RPC runs with the CALLING
-- role's own privileges by default, so it inherits RLS the same as any
-- other PostgREST query the caller could make directly:
--   * public.opportunities' "readable by authenticated, is_active = true"
--     policy applies to the `opportunities` side of both functions, on
--     top of the same filter being applied explicitly below.
--   * public.profiles' "read own row" policy applies to the `profiles`
--     join in match_opportunities_for_profile — so even if a caller passed
--     someone else's p_profile_id, the join simply returns nothing for
--     that id under RLS. There is intentionally no server-side check that
--     p_profile_id belongs to the caller; RLS makes one unnecessary.
--
-- Both accept an optional p_opportunity_id to narrow to a single row —
-- reused by both `GET /recommendations/for-you` (p_opportunity_id = null,
-- ranked top-N) and `POST /recommendations/match` (p_opportunity_id set,
-- scoring one specific listing), rather than maintaining two near-
-- identical functions per leg.
-- ---------------------------------------------------------------------------

create or replace function public.match_opportunities_for_profile(
  p_profile_id uuid,
  p_match_count int default 50,
  p_opportunity_id uuid default null
)
returns table (opportunity_id uuid, similarity double precision)
language sql
stable
as $$
  select
    o.id as opportunity_id,
    1 - (o.embedding <=> p.embedding) as similarity
  from public.opportunities o
  cross join public.profiles p
  where p.id = p_profile_id
    and p.embedding is not null
    and o.embedding is not null
    and o.is_active = true
    and (o.application_deadline is null or o.application_deadline >= current_date)
    and (p_opportunity_id is null or o.id = p_opportunity_id)
  order by o.embedding <=> p.embedding
  limit p_match_count;
$$;

comment on function public.match_opportunities_for_profile is
  'Semantic retrieval leg of the "For You" hybrid recommender: top-N '
  'opportunities by cosine similarity (pgvector <=>) between '
  'opportunities.embedding and the given profile''s embedding. Excludes '
  'inactive and clearly-expired listings; never filters on eligibility '
  '(graduation year, location, etc.) — see backend/app/services/'
  'recommendation_service.py for why.';

create or replace function public.search_opportunities_by_text(
  p_query text,
  p_match_count int default 50,
  p_opportunity_id uuid default null
)
returns table (opportunity_id uuid, rank double precision)
language sql
stable
as $$
  select
    o.id as opportunity_id,
    ts_rank(o.search_vector, to_tsquery('english', p_query)) as rank
  from public.opportunities o
  where p_query is not null
    and p_query <> ''
    and o.search_vector @@ to_tsquery('english', p_query)
    and o.is_active = true
    and (o.application_deadline is null or o.application_deadline >= current_date)
    and (p_opportunity_id is null or o.id = p_opportunity_id)
  order by rank desc
  limit p_match_count;
$$;

comment on function public.search_opportunities_by_text is
  'Keyword retrieval leg of the "For You" hybrid recommender. p_query is a '
  'to_tsquery-syntax OR expression ("word1 | word2 | ...") built in Python '
  'from the profile''s target_role/current_skills/career_interests/'
  'target_company/headline (backend/app/services/ranking.py::'
  'build_keyword_query) — OR rather than the AND that websearch_to_tsquery '
  'would default to, so a profile with many signals still retrieves '
  'candidates sharing just one of them. Matches against opportunities.'
  'search_vector, which this function does not itself maintain (see the '
  'trigger-based setup already in place for that column).';

-- PostgREST/Supabase grants EXECUTE to PUBLIC by default on function
-- creation, which already covers `authenticated`, but that default has
-- been known to get revoked by hardening scripts/tooling elsewhere in
-- this project (see PENTEST_REPORT.md / HARDENING_SUMMARY.md at the repo
-- root) — granting explicitly here means these two RPCs don't silently
-- stop working if that ever happens to this project too.
grant execute on function public.match_opportunities_for_profile(uuid, int, uuid) to authenticated;
grant execute on function public.search_opportunities_by_text(text, int, uuid) to authenticated;
