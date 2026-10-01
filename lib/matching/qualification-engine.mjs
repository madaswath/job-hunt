// @ts-check
/**
 * lib/matching/qualification-engine.mjs
 * Hard qualification rules and exclusionary filters.
 * Prevents spending LLM tokens on postings that fail fundamental criteria.
 */

/**
 * @typedef {import('../schemas/job-schema.mjs').RejectionReason} RejectionReason
 */

/**
 * Evaluates hard criteria against user profile constraints.
 *
 * @param {object} job - Canonical Job object
 * @param {object} profile - User Profile (from config/profile.yml)
 * @returns {{ qualified: boolean, reason: RejectionReason | null, details: string }}
 */
export function qualifyJob(job, profile = {}) {
  const candidateLoc = profile.location || {};
  const compConfig = profile.compensation || {};
  const targetRoles = profile.target_roles || {};

  const titleLower = (job.role?.title || '').toLowerCase();
  const descLower = (job.description || '').toLowerCase();
  const locTextLower = (job.location?.text || '').toLowerCase();

  // 1. Hard Seniority Floor: exclude intern / student / junior if candidate is senior
  const isSeniorCandidate = (targetRoles.primary || []).some(
    (/** @type {string} */ r) => /senior|staff|lead|principal|architect|director|head/i.test(r)
  ) || (profile.candidate?.headline || '').toLowerCase().includes('senior');

  if (isSeniorCandidate) {
    if (/\b(intern|internship|trainee|apprentice|entry[\s-]level|junior|graduate program)\b/i.test(titleLower)) {
      return {
        qualified: false,
        reason: 'TOO_JUNIOR',
        details: `Role title "${job.role?.title}" indicates junior/internship level for senior profile.`,
      };
    }
  }

  // 2. Contract role exclusion if candidate only seeks Full-Time
  const excludeContract = profile.preferences?.exclude_contract ?? true;
  if (excludeContract) {
    if (
      job.role?.employmentType === 'Contract' ||
      /\b(3-month contract|6-month contract|c2c only|corp-to-corp|w2 contract only|temp role)\b/i.test(descLower)
    ) {
      return {
        qualified: false,
        reason: 'CONTRACT_ROLE',
        details: 'Contract/temporary roles are excluded based on full-time profile preference.',
      };
    }
  }

  // 3. Visa & Sponsorship hard blocker
  const needsSponsorship = candidateLoc.needs_sponsorship === true;
  const authorizedCountries = (candidateLoc.authorized_in || []).map((/** @type {string} */ c) => c.toLowerCase());

  if (needsSponsorship) {
    const jobCountry = (job.location?.country || '').toLowerCase();
    const isAuthorizedLocation = authorizedCountries.some((c) => jobCountry.includes(c) || locTextLower.includes(c));

    if (!isAuthorizedLocation) {
      if (
        /\b(no visa sponsorship|unable to sponsor|must be authorized to work without sponsorship|us citizen only|security clearance required)\b/i.test(
          descLower
        )
      ) {
        return {
          qualified: false,
          reason: 'SPONSORSHIP_UNAVAILABLE',
          details: 'Posting explicitly requires existing authorization or security clearance with no sponsorship.',
        };
      }
    }
  }

  // 4. Remote / Location Incompatibility Check
  const allowRelocation = profile.preferences?.allow_relocation ?? false;
  const preferredRemote = (compConfig.location_flexibility || '').toLowerCase().includes('remote') ||
    profile.preferences?.remote_only === true;

  if (preferredRemote && !allowRelocation) {
    // If candidate wants remote and job is explicitly non-remote onsite in another city/country
    const isJobRemote = job.location?.remote || /\b(remote|work from home|wfh|anywhere)\b/i.test(locTextLower);
    const isSameCity = candidateLoc.city && locTextLower.includes(candidateLoc.city.toLowerCase());
    const isSameCountry = candidateLoc.country && locTextLower.includes(candidateLoc.country.toLowerCase());

    if (!isJobRemote && !isSameCity && !isSameCountry && job.location?.onsite) {
      if (/\b(100% on-site|must be located in|relocation required|office based)\b/i.test(descLower)) {
        return {
          qualified: false,
          reason: 'RELOCATION_REQUIRED',
          details: `Role is on-site in "${job.location?.text}" but profile specifies remote without relocation.`,
        };
      }
    }
  }

  // 5. Compensation Floor check
  let minSalaryFloor = null;
  if (compConfig.minimum) {
    const numericMatch = compConfig.minimum.replace(/[^0-9]/g, '');
    if (numericMatch) minSalaryFloor = parseInt(numericMatch, 10);
    if (compConfig.minimum.toUpperCase().includes('K') && minSalaryFloor < 1000) {
      minSalaryFloor *= 1000;
    }
  }

  if (minSalaryFloor && job.compensation?.max) {
    // If advertised max salary is strictly below candidate's walk-away minimum
    if (job.compensation.interval === 'year' && job.compensation.max < minSalaryFloor * 0.75) {
      return {
        qualified: false,
        reason: 'SALARY_TOO_LOW',
        details: `Advertised compensation max (${job.compensation.currency} ${job.compensation.max}) is below walk-away floor (${minSalaryFloor}).`,
      };
    }
  }

  return {
    qualified: true,
    reason: null,
    details: 'Passed all hard qualification gates.',
  };
}

export default qualifyJob;
