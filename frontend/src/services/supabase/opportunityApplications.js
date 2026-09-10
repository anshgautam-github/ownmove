import { supabase } from './client';

// Same shape as savedOpportunities.js: all reads/writes are scoped to the
// signed-in user via Supabase RLS on public.opportunity_applications
// (user_id = auth.uid()), so this file never has to pass a user id around
// explicitly — the session cookie/JWT does that.
async function currentUserId() {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.user?.id ?? null;
}

// The set of opportunity ids the user has marked as applied — Discover
// filters its lists against this on every load, so an applied opportunity
// stays hidden across sessions/reloads, not just for the rest of the
// current tab.
export async function loadAppliedOpportunityIds() {
  const userId = await currentUserId();
  if (!userId) return new Set();

  const { data, error } = await supabase
    .from('opportunity_applications')
    .select('opportunity_id')
    .eq('user_id', userId);

  if (error) throw new Error(error.message);
  return new Set((data || []).map((row) => row.opportunity_id));
}

export async function markOpportunityApplied(opportunityId) {
  const userId = await currentUserId();
  if (!userId) throw new Error('Sign in to mark opportunities as applied.');

  const { error } = await supabase
    .from('opportunity_applications')
    .insert({ user_id: userId, opportunity_id: opportunityId });

  // 23505 = unique_violation — already marked applied, not a real error.
  if (error && error.code !== '23505') throw new Error(error.message);
}

// Not called anywhere yet — there's no "Applied" list/undo affordance in
// the UI to trigger it from — but kept alongside markOpportunityApplied for
// symmetry, since AppShell.jsx's markApplied() only ever needs to roll back
// its own optimistic local state (the INSERT never committed if it failed,
// so there's nothing in the database to delete).
export async function unmarkOpportunityApplied(opportunityId) {
  const userId = await currentUserId();
  if (!userId) throw new Error('Sign in to manage applied opportunities.');

  const { error } = await supabase
    .from('opportunity_applications')
    .delete()
    .eq('user_id', userId)
    .eq('opportunity_id', opportunityId);

  if (error) throw new Error(error.message);
}
