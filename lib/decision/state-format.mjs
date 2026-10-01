// @ts-check
/**
 * Compact STATE payloads for Jev (token-efficient, no prose generation).
 */

/**
 * @param {object} job
 */
export function formatJobState(job) {
  return {
    title: job.role?.title,
    company: job.company?.name,
    location: job.location?.text,
    remote: job.location?.remote,
    employment_type: job.role?.employmentType,
    seniority_hint: job.role?.seniority,
    skills: (job.requirements?.skills || []).slice(0, 24),
    salary_max: job.compensation?.max,
    currency: job.compensation?.currency,
    description_excerpt: (job.description || '').slice(0, 1200),
    url: job.source?.url || job.canonical_url,
  };
}

/**
 * @param {object} profile
 */
export function formatProfileState(profile) {
  return {
    headline: profile.candidate?.headline || profile.narrative?.headline,
    target_roles: profile.target_roles?.primary || profile.target_roles,
    location: profile.location,
    needs_sponsorship: profile.location?.needs_sponsorship,
    compensation_minimum: profile.compensation?.minimum,
    superpowers: (profile.narrative?.superpowers || []).slice(0, 8),
    years_experience: profile.candidate?.years_experience,
  };
}

export default { formatJobState, formatProfileState };
