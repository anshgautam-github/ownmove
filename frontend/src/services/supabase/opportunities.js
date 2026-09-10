import { supabase } from './client';

// Defense-in-depth: the ingestion pipeline already rejects any apply_url
// that isn't a valid http(s) URL before it reaches the database (see
// backend/app/ingestion/utils/validation.py's `_looks_like_url`), but this
// table is still writable directly via Supabase (dashboard, future admin
// tooling, a manual correction) without going through that pipeline, so the
// frontend shouldn't trust apply_url unconditionally when it decides what
// to open in the browser.
const SAFE_URL_SCHEME = /^https?:\/\//i;

function sanitizeApplyUrl(url) {
  if (typeof url !== 'string' || !SAFE_URL_SCHEME.test(url.trim())) {
    return '';
  }
  return url.trim();
}

export function fromRow(row) {
  return {
    id: row.id,
    category: row.category,
    title: row.title,
    organization: row.organization || '',
    logoUrl: row.logo_url || '',
    description: row.description || '',
    location: row.location || '',
    isRemote: !!row.is_remote,
    applyUrl: sanitizeApplyUrl(row.apply_url),
    tags: row.tags || [],
    deadline: row.application_deadline || null,
    postedAt: row.posted_at,
    duration: row.duration || '',
    eligibleYears: row.eligible_years || [],
  };
}

// category can be a real category ('internships', 'hackathons', ...), or the
// virtual buckets 'for-you' / 'all', which both mean "no category filter" —
// ranking/highlighting for 'for-you' happens client-side against the user's
// profile tags, not via a different query.
//
// Called with no category at all, this is now the ONLY fetch Discover ever
// makes (see AppShell.jsx's `SidebarContentBody`): every category's list is
// derived client-side by filtering this one result set, rather than each
// category running its own separate query. The limit is raised accordingly
// — it used to cap each individual category's own query at 40, but now it
// caps the combined result across every category, so it needs enough room
// to avoid quietly showing fewer rows per category than before.
export async function loadOpportunities(category) {
  let query = supabase
    .from('opportunities')
    .select('*')
    .eq('is_active', true)
    .order('posted_at', { ascending: false });

  if (category && category !== 'all' && category !== 'for-you') {
    query = query.eq('category', category).limit(40);
  } else {
    query = query.limit(400);
  }

  const { data, error } = await query;
  if (error) throw new Error(error.message);
  return (data || []).map(fromRow);
}
