// @ts-check
/**
 * lib/recruiter/recruiter-finder.mjs
 * Recruiter & Hiring Manager Discovery and Contact Intelligence.
 */

import { existsSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const REPO_ROOT = join(__dirname, '../..');

/**
 * Searches local contacts in data/contacts.tsv for warm connections at the target company.
 * @param {string} companyName
 * @returns {Array<object>}
 */
export function findInternalContacts(companyName) {
  const contactsPath = join(REPO_ROOT, 'data/contacts.tsv');
  if (!existsSync(contactsPath)) return [];

  const content = readFileSync(contactsPath, 'utf8');
  const lines = content.split('\n');
  const matches = [];
  const compLower = companyName.toLowerCase();

  for (const line of lines) {
    const parts = line.split('\t');
    if (parts.length >= 3) {
      const [name, comp, role, email, linkedin] = parts;
      if (comp && comp.toLowerCase().includes(compLower)) {
        matches.push({
          name: name.trim(),
          company: comp.trim(),
          role: (role || 'Recruiting / Engineering').trim(),
          email: (email || '').trim(),
          linkedin: (linkedin || '').trim(),
          relationship: 'warm_contact',
          confidence: 0.95,
        });
      }
    }
  }

  return matches;
}

/**
 * Generates targeted LinkedIn search links for talent acquisition and hiring managers.
 * @param {string} companyName
 * @param {string} [roleTitle]
 * @returns {object}
 */
export function generateRecruiterSearchQueries(companyName, roleTitle = '') {
  const compEnc = encodeURIComponent(companyName);
  
  const recruiterQuery = encodeURIComponent(`"${companyName}" (Recruiter OR "Talent Acquisition" OR "Technical Sourcer")`);
  const hiringManagerQuery = encodeURIComponent(`"${companyName}" ("Engineering Manager" OR "Head of AI" OR "Director of Engineering" OR "VP of Engineering")`);

  return {
    recruiterSearchUrl: `https://www.linkedin.com/search/results/people/?keywords=${recruiterQuery}`,
    hiringManagerSearchUrl: `https://www.linkedin.com/search/results/people/?keywords=${hiringManagerQuery}`,
    companyPageUrl: `https://www.linkedin.com/company/${compEnc}`,
  };
}

/**
 * Discovers contacts and builds recruiter intelligence card for a job.
 * @param {object} job
 * @returns {object}
 */
export function discoverRecruiterIntelligence(job) {
  const companyName = job.company?.name || 'Company';
  const roleTitle = job.role?.title || '';
  const warmContacts = findInternalContacts(companyName);
  const searchUrls = generateRecruiterSearchQueries(companyName, roleTitle);

  return {
    company: companyName,
    warmContacts,
    hasWarmIntro: warmContacts.length > 0,
    searchLinks: searchUrls,
    recommendedStrategy: warmContacts.length > 0
      ? `Reach out to existing connection (${warmContacts[0].name}) for an employee referral.`
      : `Search LinkedIn for Talent Acquisition / Engineering Managers at ${companyName} and send tailored pitch.`,
  };
}

export default {
  findInternalContacts,
  generateRecruiterSearchQueries,
  discoverRecruiterIntelligence,
};
