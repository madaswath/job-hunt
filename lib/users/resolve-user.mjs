// @ts-check
/**
 * Map Clerk identity → app_users row in Supabase.
 */
import { getSupabaseAdmin } from '../db/supabase-admin.mjs';

/**
 * @typedef {object} AppUser
 * @property {string} id
 * @property {string} clerkUserId
 * @property {string | null} email
 * @property {string} planId
 */

/**
 * @param {{ clerkUserId: string, email?: string | null }} auth
 * @returns {Promise<AppUser | null>}
 */
export async function resolveAppUser(auth) {
  const supabase = getSupabaseAdmin();
  if (!supabase) {
    return {
      id: `local:${auth.clerkUserId}`,
      clerkUserId: auth.clerkUserId,
      email: auth.email || null,
      planId: 'free',
    };
  }

  const { data: existing, error: fetchErr } = await supabase
    .from('app_users')
    .select('id, clerk_user_id, email')
    .eq('clerk_user_id', auth.clerkUserId)
    .maybeSingle();

  if (fetchErr) {
    console.error('resolveAppUser fetch:', fetchErr.message);
    return null;
  }

  let userRow = existing;
  if (!userRow) {
    const { data: inserted, error: insertErr } = await supabase
      .from('app_users')
      .insert({
        clerk_user_id: auth.clerkUserId,
        email: auth.email || null,
      })
      .select('id, clerk_user_id, email')
      .single();
    if (insertErr) {
      console.error('resolveAppUser insert:', insertErr.message);
      return null;
    }
    userRow = inserted;
  }

  const planId = await getActivePlanId(supabase, userRow.id);

  return {
    id: userRow.id,
    clerkUserId: userRow.clerk_user_id,
    email: userRow.email,
    planId,
  };
}

/**
 * @param {import('@supabase/supabase-js').SupabaseClient} supabase
 * @param {string} userId
 * @returns {Promise<string>}
 */
async function getActivePlanId(supabase, userId) {
  const now = new Date().toISOString();

  const { data: founder } = await supabase
    .from('founder_plans')
    .select('plan_id, expires_at')
    .eq('user_id', userId)
    .maybeSingle();

  if (founder?.plan_id && (!founder.expires_at || founder.expires_at > now)) {
    return founder.plan_id;
  }

  const { data: sub } = await supabase
    .from('subscriptions')
    .select('plan_id, status, current_period_end')
    .eq('user_id', userId)
    .in('status', ['active', 'trialing'])
    .order('updated_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  if (sub?.plan_id) {
    if (!sub.current_period_end || sub.current_period_end > now) {
      return sub.plan_id;
    }
  }

  return 'free';
}

export default { resolveAppUser };
