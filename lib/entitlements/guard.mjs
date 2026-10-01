// @ts-check
import {
  checkEntitlement,
  incrementUsage,
  planLimitErrorBody,
  FEATURE_ENTITLEMENTS,
  getPlanLimit,
} from './service.mjs';

/**
 * @param {object} params
 * @param {import('../users/resolve-user.mjs').AppUser} params.user
 * @param {keyof typeof FEATURE_ENTITLEMENTS} params.featureKey
 * @returns {Promise<{ ok: true, check: object } | { ok: false, status: number, body: object }>}
 */
export async function requireEntitlement({ user, featureKey }) {
  const entitlementId = FEATURE_ENTITLEMENTS[featureKey];
  if (!entitlementId) {
    return { ok: false, status: 500, body: { success: false, error: 'Unknown feature' } };
  }

  const check = await checkEntitlement({
    userId: user.id,
    planId: user.planId,
    entitlementId,
    feature: featureKey,
  });

  if (!check.allowed) {
    return {
      ok: false,
      status: 402,
      body: { success: false, ...planLimitErrorBody(check) },
    };
  }

  return { ok: true, check };
}

/**
 * @param {object} params
 * @param {import('../users/resolve-user.mjs').AppUser} params.user
 * @param {keyof typeof FEATURE_ENTITLEMENTS} params.featureKey
 * @param {object} [params.metadata]
 */
export async function recordEntitlementUse({ user, featureKey, metadata = {} }) {
  const entitlementId = FEATURE_ENTITLEMENTS[featureKey];
  const planLimit = await getPlanLimit(user.planId, entitlementId);
  await incrementUsage({
    userId: user.id,
    entitlementId,
    period: planLimit?.period || 'month',
    feature: featureKey,
    metadata,
  });
}

export default { requireEntitlement, recordEntitlementUse };
