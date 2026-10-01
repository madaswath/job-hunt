// @ts-check
/**
 * Entitlements: resolve plan limits, check usage, increment counters, emit 402 payloads.
 */
import { getSupabaseAdmin } from '../db/supabase-admin.mjs';
import { periodKeyFor } from './period.mjs';
import { LOCAL_PLAN_LIMITS, getLocalUsage, addLocalUsage } from './local-limits.mjs';

/** Maps API features → entitlement ids */
export const FEATURE_ENTITLEMENTS = {
  job_evaluation: 'job_evaluations_monthly',
  resume_generation: 'tailored_resumes_monthly',
  recruiter_search: 'recruiter_searches_monthly',
  outreach_draft: 'outreach_drafts_monthly',
  ats_verification: 'ats_verification_monthly',
  job_scan: 'daily_job_scans',
  ai_analysis: 'ai_analysis',
};

/**
 * @param {string} planId
 * @param {string} entitlementId
 * @returns {Promise<{ limit: number | null, period: string, enabled: boolean } | null>}
 */
/**
 * @param {string} planId
 * @param {string} entitlementId
 * @returns {Promise<{ limit: number | null, period: string, enabled: boolean } | null>}
 */
export async function getPlanLimit(planId, entitlementId) {
  const supabase = getSupabaseAdmin();
  if (!supabase) {
    const plan = LOCAL_PLAN_LIMITS[planId] || LOCAL_PLAN_LIMITS.free;
    if (!(entitlementId in plan)) return { limit: 0, period: 'month', enabled: false };
    const raw = plan[entitlementId];
    const period =
      entitlementId === 'daily_job_scans'
        ? 'day'
        : entitlementId === 'saved_jobs' || entitlementId === 'company_sources' || entitlementId === 'connected_plugins'
          ? 'lifetime'
          : 'month';
    return {
      limit: raw === null ? null : Number(raw),
      period,
      enabled: raw !== 0,
    };
  }

  const { data, error } = await supabase
    .from('plan_entitlements')
    .select('limit_value, limit_period, enabled')
    .eq('plan_id', planId)
    .eq('entitlement_id', entitlementId)
    .maybeSingle();

  if (error || !data) {
    return { limit: 0, period: 'month', enabled: false };
  }

  return {
    limit: data.limit_value === null ? null : Number(data.limit_value),
    period: data.limit_period || 'month',
    enabled: data.enabled !== false,
  };
}

/**
 * @param {string} userId
 * @param {string} entitlementId
 * @param {string} period
 * @returns {Promise<number>}
 */
async function getUsage(userId, entitlementId, period) {
  const periodKey = periodKeyFor(/** @type {'month'|'day'|'lifetime'} */ (period));
  if (userId.startsWith('local:')) {
    return getLocalUsage(userId, entitlementId, periodKey);
  }

  const supabase = getSupabaseAdmin();
  if (!supabase) return getLocalUsage(userId, entitlementId, periodKey);

  const { data } = await supabase
    .from('usage_counters')
    .select('used')
    .eq('user_id', userId)
    .eq('entitlement_id', entitlementId)
    .eq('period_key', periodKey)
    .maybeSingle();

  return data?.used ? Number(data.used) : 0;
}

/**
 * @param {{ userId: string, planId: string, entitlementId: string, feature?: string, quantity?: number, metadata?: object }} params
 * @returns {Promise<{ allowed: boolean, used: number, limit: number | null, upgrade_plan?: string, soft?: boolean }>}
 */
export async function checkEntitlement({ userId, planId, entitlementId, feature }) {
  const mode = process.env.ENTITLEMENTS_MODE || 'soft';
  if (mode === 'off') {
    return { allowed: true, used: 0, limit: null };
  }

  const planLimit = await getPlanLimit(planId, entitlementId);
  if (!planLimit?.enabled) {
    const blocked = { allowed: false, used: 0, limit: 0, upgrade_plan: planId === 'free' ? 'premium' : 'pro' };
    if (mode === 'soft') return { ...blocked, allowed: true, soft: true };
    return blocked;
  }

  if (planLimit.limit === null) {
    return { allowed: true, used: 0, limit: null };
  }

  const used = await getUsage(userId, entitlementId, planLimit.period);
  if (used >= planLimit.limit) {
    const blocked = {
      allowed: false,
      used,
      limit: planLimit.limit,
      upgrade_plan: planId === 'free' ? 'premium' : 'pro',
      feature: feature || entitlementId,
    };
    if (mode === 'soft') return { ...blocked, allowed: true, soft: true };
    return blocked;
  }

  return { allowed: true, used, limit: planLimit.limit };
}

/**
 * @param {{ userId: string, entitlementId: string, period: string, quantity?: number, feature?: string, metadata?: object }} params
 */
export async function incrementUsage({ userId, entitlementId, period, quantity = 1, feature, metadata = {} }) {
  const periodKey = periodKeyFor(/** @type {'month'|'day'|'lifetime'} */ (period));

  if (userId.startsWith('local:') || !getSupabaseAdmin()) {
    addLocalUsage(userId, entitlementId, periodKey, quantity);
    return;
  }

  const supabase = getSupabaseAdmin();
  const { data: row } = await supabase
    .from('usage_counters')
    .select('id, used')
    .eq('user_id', userId)
    .eq('entitlement_id', entitlementId)
    .eq('period_key', periodKey)
    .maybeSingle();

  const nextUsed = (row?.used ? Number(row.used) : 0) + quantity;

  if (row?.id) {
    await supabase.from('usage_counters').update({ used: nextUsed, updated_at: new Date().toISOString() }).eq('id', row.id);
  } else {
    await supabase.from('usage_counters').insert({
      user_id: userId,
      entitlement_id: entitlementId,
      period_key: periodKey,
      used: nextUsed,
    });
  }

  await supabase.from('usage_events').insert({
    user_id: userId,
    entitlement_id: entitlementId,
    feature: feature || entitlementId,
    quantity,
    metadata,
  });
}

/**
 * @param {string} planId
 * @returns {Promise<Record<string, { limit: number | null, period: string, used: number }>>}
 */
export async function getUsageSummary(userId, planId) {
  const entitlements = Object.values(FEATURE_ENTITLEMENTS);
  const unique = [...new Set(entitlements)];
  /** @type {Record<string, { limit: number | null, period: string, used: number }>} */
  const summary = {};

  for (const ent of unique) {
    const planLimit = await getPlanLimit(planId, ent);
    const used = planLimit ? await getUsage(userId, ent, planLimit.period) : 0;
    summary[ent] = {
      limit: planLimit?.limit ?? null,
      period: planLimit?.period || 'month',
      used,
    };
  }
  return summary;
}

/**
 * @param {object} checkResult
 * @returns {object}
 */
export function planLimitErrorBody(checkResult) {
  return {
    code: 'PLAN_LIMIT_REACHED',
    feature: checkResult.feature,
    used: checkResult.used,
    limit: checkResult.limit,
    upgrade_plan: checkResult.upgrade_plan || 'premium',
  };
}

export default {
  FEATURE_ENTITLEMENTS,
  checkEntitlement,
  incrementUsage,
  getUsageSummary,
  planLimitErrorBody,
};
