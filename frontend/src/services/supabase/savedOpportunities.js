import { supabase } from './client';
import { fromRow } from './opportunities';

// All reads/writes are scoped to the signed-in user via Supabase RLS on
// public.saved_opportunities (user_id = auth.uid()), so this file never has
// to pass a user id around explicitly — the session cookie/JWT does that.
async function currentUserId() {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.user?.id ?? null;
}

// Lightweight: just the set of opportunity ids the user has saved, for
// showing the filled/unfilled bookmark state on cards without fetching
// full listing data twice.
export async function loadSavedOpportunityIds() {
  const userId = await currentUserId();
  if (!userId) return new Set();

  const { data, error } = await supabase
    .from('saved_opportunities')
    .select('opportunity_id')
    .eq('user_id', userId);

  if (error) throw new Error(error.message);
  return new Set((data || []).map((row) => row.opportunity_id));
}

// Full rows (joined against opportunities) for the Saved page.
export async function loadSavedOpportunities() {
  const userId = await currentUserId();
  if (!userId) return [];

  const { data, error } = await supabase
    .from('saved_opportunities')
    .select('created_at, opportunities(*)')
    .eq('user_id', userId)
    .order('created_at', { ascending: false });

  if (error) throw new Error(error.message);
  return (data || [])
    .filter((row) => row.opportunities)
    .map((row) => fromRow(row.opportunities));
}

export async function saveOpportunity(opportunityId) {
  const userId = await currentUserId();
  if (!userId) throw new Error('Sign in to save opportunities.');

  const { error } = await supabase
    .from('saved_opportunities')
    .insert({ user_id: userId, opportunity_id: opportunityId });

  // 23505 = unique_violation — already saved, not a real error for our purposes.
  if (error && error.code !== '23505') throw new Error(error.message);
}

export async function unsaveOpportunity(opportunityId) {
  const userId = await currentUserId();
  if (!userId) throw new Error('Sign in to manage saved opportunities.');

  const { error } = await supabase
    .from('saved_opportunities')
    .delete()
    .eq('user_id', userId)
    .eq('opportunity_id', opportunityId);

  if (error) throw new Error(error.message);
}
