// @ts-check
/**
 * lib/sources/detector.mjs
 * Narada's Automated ATS & Career Site Detection Engine.
 * Inspects any company URL or career page and automatically resolves the underlying ATS provider.
 */

/**
 * Known ATS hostname patterns and signatures.
 */
const ATS_SIGNATURES = [
  { provider: 'greenhouse', pattern: /boards\.greenhouse\.io|api\.greenhouse\.io|greenhouse\.io/i, name: 'Greenhouse' },
  { provider: 'lever', pattern: /jobs\.lever\.co|api\.lever\.co/i, name: 'Lever' },
  { provider: 'ashby', pattern: /jobs\.ashbyhq\.com|api\.ashbyhq\.com/i, name: 'Ashby' },
  { provider: 'workday', pattern: /myworkdayjobs\.com|workday\.com/i, name: 'Workday' },
  { provider: 'smartrecruiters', pattern: /smartrecruiters\.com/i, name: 'SmartRecruiters' },
  { provider: 'bamboohr', pattern: /bamboohr\.com\/careers|bamboohr\.com\/jobs/i, name: 'BambooHR' },
  { provider: 'personio', pattern: /personio\.de|personio\.com/i, name: 'Personio' },
  { provider: 'teamtailor', pattern: /teamtailor\.com/i, name: 'Teamtailor' },
  { provider: 'breezy', pattern: /breezy\.hr/i, name: 'Breezy HR' },
];

/**
 * Detects the ATS provider for a given career site URL.
 *
 * @param {string} url
 * @returns {Promise<{
 *   success: boolean,
 *   url: string,
 *   detectedProvider: string,
 *   providerName: string,
 *   isPublicApi: boolean,
 *   confidence: number,
 *   message: string
 * }>}
 */
export async function detectCareerSiteAts(url) {
  if (!url || !url.startsWith('http')) {
    return {
      success: false,
      url,
      detectedProvider: 'unknown',
      providerName: 'Custom Career Site',
      isPublicApi: false,
      confidence: 0,
      message: 'Invalid URL provided.',
    };
  }

  // 1. Check direct URL signature match
  for (const sig of ATS_SIGNATURES) {
    if (sig.pattern.test(url)) {
      return {
        success: true,
        url,
        detectedProvider: sig.provider,
        providerName: sig.name,
        isPublicApi: true,
        confidence: 0.99,
        message: `Directly identified as ${sig.name} public board. Zero-token API scraping available.`,
      };
    }
  }

  // 2. Fetch page HTML to check for embedded ATS iframes or script markers
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);

    const res = await fetch(url, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        Accept: 'text/html,application/xhtml+xml',
      },
    });
    clearTimeout(timeout);

    if (res.ok) {
      const html = (await res.text()).toLowerCase();

      for (const sig of ATS_SIGNATURES) {
        if (sig.pattern.test(html) || html.includes(`data-ats="${sig.provider}"`)) {
          return {
            success: true,
            url,
            detectedProvider: sig.provider,
            providerName: sig.name,
            isPublicApi: true,
            confidence: 0.90,
            message: `Identified embedded ${sig.name} ATS widgets on career page.`,
          };
        }
      }
    }
  } catch {
    // Network fallback
  }

  // 3. Fallback: Treat as custom company career crawler
  return {
    success: true,
    url,
    detectedProvider: 'custom_crawler',
    providerName: 'Custom Company Portal',
    isPublicApi: false,
    confidence: 0.60,
    message: 'Custom career portal. Will be monitored via Narada generic crawler & RSS parser.',
  };
}

export default {
  detectCareerSiteAts,
};
