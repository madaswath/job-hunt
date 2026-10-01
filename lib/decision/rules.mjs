// @ts-check
/**
 * Rules-first decision fallbacks (no API). Runs before Jev.
 */
import { qualifyJob } from '../matching/qualification-engine.mjs';

/**
 * @param {object} job
 * @param {object} profile
 * @returns {{ qualification: 'REJECT'|'REVIEW'|'QUALIFY', reason?: string, provider: 'RULE' }}
 */
export function rulesQualification(job, profile) {
  const hard = qualifyJob(job, profile);
  if (!hard.qualified) {
    return { qualification: 'REJECT', reason: hard.reason || hard.details, provider: 'RULE' };
  }
  return { qualification: 'QUALIFY', provider: 'RULE' };
}

/**
 * @param {number} deterministicScore
 * @returns {'LOW'|'MEDIUM'|'HIGH'|'REVIEW'}
 */
export function rulesPriorityBand(deterministicScore) {
  if (deterministicScore >= 82) return 'HIGH';
  if (deterministicScore >= 68) return 'MEDIUM';
  if (deterministicScore >= 50) return 'REVIEW';
  return 'LOW';
}

/**
 * @param {object} job
 * @returns {'AI_ENGINEERING'|'ML_ENGINEERING'|'DATA_SCIENCE'|'DATA_ANALYTICS'|'OTHER'}
 */
export function rulesRoleRelevance(job) {
  const text = `${job.role?.title || ''} ${job.description || ''}`.toLowerCase();
  if (/\b(genai|llm|rag|agent|prompt|langchain|openai)\b/.test(text)) return 'AI_ENGINEERING';
  if (/\b(mlops|machine learning|pytorch|tensorflow|deep learning)\b/.test(text)) return 'ML_ENGINEERING';
  if (/\b(data scientist|experiment|statistical)\b/.test(text)) return 'DATA_SCIENCE';
  if (/\b(analyst|tableau|power bi|looker|sql)\b/.test(text)) return 'DATA_ANALYTICS';
  return 'OTHER';
}

/**
 * @param {'free'|'premium'|'pro'} planId
 * @param {'LOW'|'MEDIUM'|'HIGH'|'REVIEW'} priority
 * @param {number} score
 * @returns {boolean}
 */
export function rulesShouldRunGroq(planId, priority, score) {
  if (priority === 'REJECT' || priority === 'LOW') return false;
  if (planId === 'free') {
    return priority === 'HIGH' && score >= 85;
  }
  if (planId === 'premium') {
    return (priority === 'HIGH' || priority === 'MEDIUM') && score >= 70;
  }
  return score >= 60 && priority !== 'REVIEW';
}

export default {
  rulesQualification,
  rulesPriorityBand,
  rulesRoleRelevance,
  rulesShouldRunGroq,
};
