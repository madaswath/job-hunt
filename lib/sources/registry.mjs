// @ts-check
/**
 * lib/sources/registry.mjs
 * Job-hunt Job Sources Catalog across 4 Tiers:
 * Tier A: Direct Public ATS APIs (Greenhouse, Lever, Ashby, Workday, etc.)
 * Tier B: General Job Platforms (LinkedIn, Naukri, Indeed, Wellfound, Instahyre, etc.)
 * Tier C: Company Career Sites (Auto-detected)
 * Tier D: Connected Authenticated Accounts (Gmail alerts, OAuth connectors)
 */

export const SOURCE_TIERS = {
  TIER_A: 'Direct Public ATS APIs',
  TIER_B: 'General Job Platforms',
  TIER_C: 'Company Career Sites',
  TIER_D: 'Connected Accounts',
};

export const DEFAULT_JOB_SOURCES = [
  // Tier A: Direct Public ATS
  {
    id: 'src_greenhouse',
    name: 'Greenhouse Public ATS',
    slug: 'greenhouse',
    tier: 'TIER_A',
    sourceType: 'PUBLIC_ATS',
    provider: 'greenhouse',
    authType: 'NONE',
    enabled: true,
    supportsSearch: true,
    description: 'Direct zero-token API access to thousands of high-growth tech companies.',
  },
  {
    id: 'src_lever',
    name: 'Lever Postings API',
    slug: 'lever',
    tier: 'TIER_A',
    sourceType: 'PUBLIC_ATS',
    provider: 'lever',
    authType: 'NONE',
    enabled: true,
    supportsSearch: true,
    description: 'Public job board API for venture-backed and enterprise employers.',
  },
  {
    id: 'src_ashby',
    name: 'Ashby Job Board API',
    slug: 'ashby',
    tier: 'TIER_A',
    sourceType: 'PUBLIC_ATS',
    provider: 'ashby',
    authType: 'NONE',
    enabled: true,
    supportsSearch: true,
    description: 'High-fidelity structured ATS API popular among AI startups.',
  },
  {
    id: 'src_workday',
    name: 'Workday Public CXS',
    slug: 'workday',
    tier: 'TIER_A',
    sourceType: 'PUBLIC_ATS',
    provider: 'workday',
    authType: 'NONE',
    enabled: true,
    supportsSearch: true,
    description: 'Enterprise career portal connector for Fortune 500 companies.',
  },
  {
    id: 'src_breezy',
    name: 'Breezy HR',
    slug: 'breezy',
    tier: 'TIER_A',
    sourceType: 'PUBLIC_ATS',
    provider: 'breezy',
    authType: 'NONE',
    enabled: true,
    supportsSearch: true,
    description: 'Fast-moving tech companies and remote employers.',
  },
  {
    id: 'src_smartrecruiters',
    name: 'SmartRecruiters',
    slug: 'smartrecruiters',
    tier: 'TIER_A',
    sourceType: 'PUBLIC_ATS',
    provider: 'smartrecruiters',
    authType: 'NONE',
    enabled: true,
    supportsSearch: true,
    description: 'Global enterprise hiring platform.',
  },

  // Tier B: General Platforms
  {
    id: 'src_linkedin',
    name: 'LinkedIn Jobs',
    slug: 'linkedin',
    tier: 'TIER_B',
    sourceType: 'CONNECTED_ACCOUNT',
    provider: 'linkedin',
    authType: 'USER_AUTHORIZED',
    enabled: true,
    supportsSearch: true,
    description: 'Largest professional network. Job alerts and saved role discovery.',
  },
  {
    id: 'src_naukri',
    name: 'Naukri.com',
    slug: 'naukri',
    tier: 'TIER_B',
    sourceType: 'CONNECTED_ACCOUNT',
    provider: 'naukri',
    authType: 'USER_AUTHORIZED',
    enabled: true,
    supportsSearch: true,
    description: 'Premier Indian tech and enterprise hiring platform.',
  },
  {
    id: 'src_indeed',
    name: 'Indeed',
    slug: 'indeed',
    tier: 'TIER_B',
    sourceType: 'CONNECTED_ACCOUNT',
    provider: 'indeed',
    authType: 'USER_AUTHORIZED',
    enabled: true,
    supportsSearch: true,
    description: 'Comprehensive job search aggregator and direct posting board.',
  },
  {
    id: 'src_wellfound',
    name: 'Wellfound (AngelList)',
    slug: 'wellfound',
    tier: 'TIER_B',
    sourceType: 'CONNECTED_ACCOUNT',
    provider: 'wellfound',
    authType: 'USER_AUTHORIZED',
    enabled: true,
    supportsSearch: true,
    description: 'Early-stage and high-growth startup engineering roles.',
  },
  {
    id: 'src_instahyre',
    name: 'Instahyre',
    slug: 'instahyre',
    tier: 'TIER_B',
    sourceType: 'CONNECTED_ACCOUNT',
    provider: 'instahyre',
    authType: 'USER_AUTHORIZED',
    enabled: true,
    supportsSearch: true,
    description: 'AI-driven curated tech hiring in India.',
  },
  {
    id: 'src_remoteok',
    name: 'RemoteOK',
    slug: 'remoteok',
    tier: 'TIER_B',
    sourceType: 'PUBLIC_API',
    provider: 'remoteok',
    authType: 'NONE',
    enabled: true,
    supportsSearch: true,
    description: 'Global remote tech opportunities.',
  },
  {
    id: 'src_hn',
    name: 'Hacker News (Who is Hiring)',
    slug: 'hackernews',
    tier: 'TIER_B',
    sourceType: 'PUBLIC_API',
    provider: 'hackernews',
    authType: 'NONE',
    enabled: true,
    supportsSearch: true,
    description: 'Monthly direct hiring threads by engineering founders.',
  },

  // Tier D: Connected Email Connectors
  {
    id: 'src_gmail_alerts',
    name: 'Gmail Job Alerts Ingest',
    slug: 'gmail',
    tier: 'TIER_D',
    sourceType: 'EMAIL_CONNECTOR',
    provider: 'gmail',
    authType: 'OAUTH',
    enabled: true,
    supportsSearch: false,
    description: 'Ingests email alerts from LinkedIn, Naukri, Indeed, and company newsletters.',
  },
];

/**
 * Returns all registered job sources.
 * @returns {Array<object>}
 */
export function listAllSources() {
  return DEFAULT_JOB_SOURCES;
}

export default {
  SOURCE_TIERS,
  DEFAULT_JOB_SOURCES,
  listAllSources,
};
