// @ts-check
/**
 * When Jev is unavailable, synthesize typed decisions from rules + heuristics.
 */
import {
  rulesQualification,
  rulesPriorityBand,
  rulesRoleRelevance,
  rulesShouldRunGroq,
} from './rules.mjs';

/**
 * @param {object} params
 * @param {object} params.job
 * @param {object} params.profile
 * @param {number} [params.deterministicScore]
 * @returns {{ answers: object, provider: 'RULE', model: 'rules-v1' }}
 */
export function fallbackGaneshaDecision({ job, profile, deterministicScore = 0 }) {
  const ruleQ = rulesQualification(job, profile);
  const role = rulesRoleRelevance(job);
  const priority = rulesPriorityBand(deterministicScore);

  let qualification = ruleQ.qualification;
  if (qualification === 'QUALIFY' && role === 'OTHER' && deterministicScore < 55) {
    qualification = 'REVIEW';
  }

  return {
    provider: 'RULE',
    model: 'rules-v1',
    answers: {
      role_relevance: { type: 'choice', choice: role, confidence: 0.75 },
      qualification: { type: 'choice', choice: qualification, confidence: 0.8 },
      priority: {
        type: 'choice',
        choice: qualification === 'REJECT' ? 'LOW' : priority,
        confidence: 0.7,
      },
      scam_or_low_quality: { type: 'noul', noul: 0.05 },
    },
  };
}

/**
 * @param {object} params
 * @param {string} params.planId
 * @param {string} params.priority
 * @param {number} params.deterministicScore
 */
export function fallbackGroqGate({ planId, priority, deterministicScore }) {
  const run = rulesShouldRunGroq(planId, priority, deterministicScore);
  return {
    provider: 'RULE',
    model: 'rules-v1',
    answers: {
      run_deep_analysis: { type: 'noul', noul: run ? 0.85 : 0.15 },
    },
  };
}

export default { fallbackGaneshaDecision, fallbackGroqGate };
