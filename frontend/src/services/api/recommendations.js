import { api } from './client';
import { endpoints } from './endpoints';
import { fromRow } from '../supabase/opportunities';

/**
 * "For You" — talks to the FastAPI hybrid recommendation engine
 * (backend/app/services/recommendation_service.py) instead of the
 * client-side tag-overlap sort AppShell used before this existed.
 *
 * The backend's `RecommendedOpportunity.opportunity` is a Pydantic
 * `Opportunity` built straight from the raw Supabase row (see
 * backend/app/schemas/opportunity.py), so its field names are the same
 * snake_case as opportunities table rows — `fromRow()` from
 * services/supabase/opportunities.js is reused as-is rather than writing a
 * second, parallel mapper that could drift from it.
 */
function fromRecommendedOpportunity(item) {
  return {
    ...fromRow(item.opportunity),
    matchScore: item.score,
    matchReasons: (item.reasons || []).map((r) => r.detail || r.factor).filter(Boolean),
  };
}

/** Ranked recommendations for the signed-in user. Never throws for "no
 * profile signal yet" — the backend falls back to recent active listings
 * in that case (see recommendation_service.py's fallback_recent path) — so
 * callers only need to handle genuine network/auth failures. */
export async function loadForYouRecommendations() {
  const response = await api.get(endpoints.recommendations.forYou);
  return (response?.items || []).map(fromRecommendedOpportunity);
}

/** Force a recompute (bypasses whatever's cached in public.recommendations
 * server-side) — not wired to any UI yet, exposed for a future "Refresh
 * matches" action. */
export async function refreshForYouRecommendations() {
  const response = await api.post(endpoints.recommendations.refresh);
  return (response?.items || []).map(fromRecommendedOpportunity);
}
