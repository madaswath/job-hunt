// @ts-check
/**
 * lib/schemas/job-schema.mjs
 * Canonical entities and validation schemas for the Career-Ops Product & Workflow Layer.
 */

import { createHash } from 'crypto';
import { normalizeUrl } from '../../url-key.mjs';

/**
 * @typedef {'DISCOVERED' | 'QUALIFIED' | 'REJECTED' | 'REVIEW' | 'APPROVED' | 'APPLIED' | 'SCREEN' | 'INTERVIEW' | 'OFFER' | 'CLOSED'} JobState
 */

/**
 * @typedef {'TOO_JUNIOR' | 'WRONG_LOCATION' | 'SALARY_TOO_LOW' | 'CONTRACT_ROLE' | 'RELOCATION_REQUIRED' | 'TECH_STACK_MISMATCH' | 'NOT_ENOUGH_GENAI' | 'SPONSORSHIP_UNAVAILABLE' | 'POOR_COMPANY_REPUTATION' | 'MANUAL_DISMISS'} RejectionReason
 */

/**
 * @typedef {'JOB_REVIEW' | 'RESUME_APPROVAL' | 'OUTREACH_APPROVAL' | 'APPLICATION_SUBMISSION'} ApprovalTaskType
 */

/**
 * Generates a stable deterministic ID for a job from its URL or company + title.
 * @param {string} url
 * @param {string} [company]
 * @param {string} [title]
 * @returns {string}
 */
export function generateJobId(url, company = '', title = '') {
  const normUrl = normalizeUrl(url);
  if (normUrl) {
    return 'job_' + createHash('sha256').update(normUrl).digest('hex').slice(0, 16);
  }
  const fallbackKey = `${(company || '').trim().toLowerCase()}|${(title || '').trim().toLowerCase()}`;
  return 'job_' + createHash('sha256').update(fallbackKey).digest('hex').slice(0, 16);
}

/**
 * Creates a Canonical Job object.
 * @param {Partial<any>} raw
 * @returns {object}
 */
export function createCanonicalJob(raw = {}) {
  const url = raw.url || raw.source?.url || '';
  const companyName = raw.company?.name || raw.company || raw.company_name || 'Unknown Company';
  const roleTitle = raw.role?.title || raw.title || raw.role || 'Unknown Title';
  const id = raw.id || generateJobId(url, companyName, roleTitle);

  return {
    id,
    source: {
      provider: raw.source?.provider || raw.provider || 'direct',
      sourceId: raw.source?.sourceId || raw.sourceId || '',
      url,
      canonicalUrl: normalizeUrl(url) || url,
    },
    company: {
      name: companyName,
      domain: raw.company?.domain || raw.domain || '',
      logoUrl: raw.company?.logoUrl || raw.logoUrl || '',
    },
    role: {
      title: roleTitle,
      normalizedTitle: raw.role?.normalizedTitle || roleTitle.toLowerCase(),
      seniority: raw.role?.seniority || raw.seniority || 'Unspecified',
      employmentType: raw.role?.employmentType || raw.employmentType || 'Full-time', // Full-time, Contract, Part-time
    },
    location: {
      text: raw.location?.text || raw.location || 'Unspecified',
      country: raw.location?.country || raw.country || '',
      city: raw.location?.city || raw.city || '',
      remote: Boolean(raw.location?.remote ?? raw.remote ?? false),
      hybrid: Boolean(raw.location?.hybrid ?? raw.hybrid ?? false),
      onsite: Boolean(raw.location?.onsite ?? raw.onsite ?? false),
    },
    compensation: {
      currency: raw.compensation?.currency || raw.currency || 'USD',
      min: typeof raw.compensation?.min === 'number' ? raw.compensation.min : (typeof raw.min_salary === 'number' ? raw.min_salary : null),
      max: typeof raw.compensation?.max === 'number' ? raw.compensation.max : (typeof raw.max_salary === 'number' ? raw.max_salary : null),
      interval: raw.compensation?.interval || 'year', // year, month, hour
      rawText: raw.compensation?.rawText || raw.salary || '',
    },
    description: raw.description || raw.body || '',
    requirements: {
      skills: Array.isArray(raw.requirements?.skills) ? raw.requirements.skills : (Array.isArray(raw.skills) ? raw.skills : []),
      mustHaves: Array.isArray(raw.requirements?.mustHaves) ? raw.requirements.mustHaves : [],
      niceToHaves: Array.isArray(raw.requirements?.niceToHaves) ? raw.requirements.niceToHaves : [],
      minExperienceYears: raw.requirements?.minExperienceYears ?? raw.min_exp_years ?? null,
    },
    discoveredAt: raw.discoveredAt || new Date().toISOString(),
    postedAt: raw.postedAt || null,
    checkedAt: raw.checkedAt || new Date().toISOString(),
    state: /** @type {JobState} */ (raw.state || 'DISCOVERED'),
    rejectionReason: raw.rejectionReason || null,
    rejectionNote: raw.rejectionNote || '',
    deterministicMatch: raw.deterministicMatch || null,
    llmEvaluation: raw.llmEvaluation || null,
    reportNumber: raw.reportNumber || null,
    reportPath: raw.reportPath || null,
    tailoredCvPath: raw.tailoredCvPath || null,
    recruiter: raw.recruiter || null,
  };
}

/**
 * Creates an Approval Task entity.
 * @param {object} params
 * @param {ApprovalTaskType} params.type
 * @param {string} params.jobId
 * @param {string} params.title
 * @param {string} [params.description]
 * @param {object} [params.payload]
 * @returns {object}
 */
export function createApprovalTask({ type, jobId, title, description = '', payload = {} }) {
  const id = `task_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  return {
    id,
    type,
    jobId,
    title,
    description,
    payload,
    status: 'PENDING', // PENDING, APPROVED, REJECTED
    createdAt: new Date().toISOString(),
    reviewedAt: null,
    decisionReason: null,
  };
}
