// @ts-check
/** Fallback limits when Supabase is not configured (local dev). */

export const LOCAL_PLAN_LIMITS = {
  free: {
    job_evaluations_monthly: 10,
    tailored_resumes_monthly: 2,
    recruiter_searches_monthly: 0,
    outreach_drafts_monthly: 0,
    connected_plugins: 0,
    company_sources: 5,
    saved_jobs: 25,
    daily_job_scans: 1,
    ats_verification_monthly: 2,
    ai_analysis: 0,
    advanced_analytics: 0,
    interview_ai: 0,
    priority_processing: 0,
    gmail_job_alerts: 0,
  },
  premium: {
    job_evaluations_monthly: 150,
    tailored_resumes_monthly: 30,
    recruiter_searches_monthly: 20,
    outreach_drafts_monthly: 20,
    connected_plugins: 2,
    company_sources: 50,
    saved_jobs: 250,
    daily_job_scans: 4,
    ats_verification_monthly: null,
    ai_analysis: 1,
    advanced_analytics: 1,
    interview_ai: 1,
    priority_processing: 0,
    gmail_job_alerts: 1,
  },
  pro: {
    job_evaluations_monthly: 500,
    tailored_resumes_monthly: 100,
    recruiter_searches_monthly: 100,
    outreach_drafts_monthly: 100,
    connected_plugins: 10,
    company_sources: 200,
    saved_jobs: null,
    daily_job_scans: 12,
    ats_verification_monthly: null,
    ai_analysis: 1,
    advanced_analytics: 1,
    interview_ai: 1,
    priority_processing: 1,
    gmail_job_alerts: 1,
  },
};

/** @type {Map<string, Map<string, number>>} */
const localUsage = new Map();

/**
 * @param {string} userId
 * @param {string} entitlementId
 * @param {string} periodKey
 * @returns {number}
 */
export function getLocalUsage(userId, entitlementId, periodKey) {
  const key = `${userId}:${entitlementId}:${periodKey}`;
  return localUsage.get(key) || 0;
}

/**
 * @param {string} userId
 * @param {string} entitlementId
 * @param {string} periodKey
 * @param {number} delta
 */
export function addLocalUsage(userId, entitlementId, periodKey, delta = 1) {
  const key = `${userId}:${entitlementId}:${periodKey}`;
  const prev = localUsage.get(key) || 0;
  localUsage.set(key, prev + delta);
}

export default { LOCAL_PLAN_LIMITS, getLocalUsage, addLocalUsage };
