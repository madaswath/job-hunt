// @ts-check
/**
 * Brihaspati / Groq deep analysis — only when decision gate allows (saves Groq spend).
 */
import { completeWithFallback } from '../ai/router.mjs';
import { formatJobState, formatProfileState } from '../decision/state-format.mjs';

/**
 * @param {object} params
 * @param {object} params.job
 * @param {object} params.profile
 * @param {string} [params.userId]
 * @returns {Promise<{ ran: boolean, summary?: string, provider?: string }>}
 */
export async function runDeepJobAnalysis({ job, profile, userId }) {
  if (!process.env.GROQ_API_KEY && !process.env.GEMINI_API_KEY && !process.env.OPENAI_API_KEY) {
    return { ran: false, summary: 'No generative provider configured' };
  }

  const state = {
    job: formatJobState(job),
    candidate: formatProfileState(profile),
    match_score: job.deterministicMatch?.score ?? job.match_score,
  };

  const messages = [
    {
      role: 'system',
      content:
        'You are Brihaspati, a concise job-fit analyst. Output 5 bullet points: fit, gaps, comp note, risk, apply recommendation. No fabrication beyond STATE.',
    },
    {
      role: 'user',
      content: JSON.stringify(state),
    },
  ];

  const res = await completeWithFallback({
    messages,
    workload: 'job_analysis',
    maxTokens: 800,
    usageContext: {
      userId,
      feature: 'job_deep_analysis',
      workflow: 'brihaspati',
    },
  });

  return {
    ran: true,
    summary: res.content,
    provider: res.provider,
    model: res.model,
  };
}

export default { runDeepJobAnalysis };
