// @ts-check
/**
 * lib/normalization/job-normalizer.mjs
 * Normalizes provider outputs, markdown pipelines, and scraped payloads into canonical Job entities.
 */

import { createCanonicalJob } from '../schemas/job-schema.mjs';
import { normalizeUrl } from '../../url-key.mjs';

/**
 * Parses raw provider output or URL into a canonical Job entity.
 *
 * @param {object | string} raw
 * @param {string} [defaultProvider]
 * @returns {object}
 */
export function normalizeJob(raw, defaultProvider = 'direct') {
  if (typeof raw === 'string') {
    // Markdown pipeline link format: "- [Company](url) - Role - Location" or plain URL
    const urlMatch = raw.match(/https?:\/\/[^\s)\]]+/);
    const url = urlMatch ? urlMatch[0] : raw;

    let company = 'Target Company';
    let role = 'Open Position';
    let location = 'Remote / Unspecified';

    // Parse markdown list entry if present
    const mdMatch = raw.match(/\[([^\]]+)\]\(([^)]+)\)(?:\s*-\s*([^-\n]+))?(?:\s*-\s*([^-\n]+))?/);
    if (mdMatch) {
      company = mdMatch[1].trim();
      if (mdMatch[3]) role = mdMatch[3].trim();
      if (mdMatch[4]) location = mdMatch[4].trim();
    }

    return createCanonicalJob({
      url,
      company: { name: company },
      role: { title: role },
      location: { text: location, remote: /remote/i.test(location) },
      source: { provider: defaultProvider, url },
    });
  }

  // Object payload from Greenhouse, Ashby, Lever, Workday, etc.
  const url = raw.url || raw.link || raw.source_url || raw.apply_url || '';
  const companyName = raw.company || raw.company_name || raw.employer || 'Direct Employer';
  const title = raw.title || raw.role || raw.position || 'Software Engineer';
  const locationText = raw.location || raw.locations?.join(', ') || raw.city || 'Remote / Unspecified';
  const isRemote = Boolean(raw.remote ?? /remote/i.test(locationText) ?? false);
  const isHybrid = Boolean(raw.hybrid ?? /hybrid/i.test(locationText) ?? false);

  return createCanonicalJob({
    id: raw.id,
    source: {
      provider: raw.provider || defaultProvider,
      sourceId: raw.source_id || raw.job_id || raw.req_id || '',
      url,
      canonicalUrl: normalizeUrl(url) || url,
    },
    company: {
      name: companyName,
      domain: raw.domain || '',
      logoUrl: raw.logo || '',
    },
    role: {
      title,
      seniority: raw.seniority || raw.level || 'Mid-Senior',
      employmentType: raw.employment_type || raw.type || 'Full-time',
    },
    location: {
      text: locationText,
      remote: isRemote,
      hybrid: isHybrid,
      onsite: !isRemote && !isHybrid,
      country: raw.country || '',
      city: raw.city || '',
    },
    compensation: {
      currency: raw.currency || 'USD',
      min: raw.min_salary ?? raw.salary_min ?? null,
      max: raw.max_salary ?? raw.salary_max ?? null,
      interval: raw.salary_interval || 'year',
      rawText: raw.salary || raw.compensation_text || '',
    },
    description: raw.description || raw.body || raw.content || raw.snippet || '',
    requirements: {
      skills: Array.isArray(raw.skills) ? raw.skills : (Array.isArray(raw.tags) ? raw.tags : []),
      mustHaves: raw.must_haves || [],
      niceToHaves: raw.nice_to_haves || [],
      minExperienceYears: raw.min_experience_years || null,
    },
    postedAt: raw.posted_at || raw.date_posted || null,
    discoveredAt: raw.discovered_at || new Date().toISOString(),
    state: raw.state || 'DISCOVERED',
  });
}

export default normalizeJob;
