// @ts-check
/**
 * Typed Jev question shapes for Job-hunt agents (System One / decision layer).
 * @see https://api.typesafe.ai/v1/systemone
 */

/** @typedef {'REJECT'|'REVIEW'|'QUALIFY'} QualificationDecision */
/** @typedef {'LOW'|'MEDIUM'|'HIGH'|'REVIEW'} PriorityBand */
/** @typedef {'AI_ENGINEERING'|'ML_ENGINEERING'|'DATA_SCIENCE'|'DATA_ANALYTICS'|'OTHER'} RoleRelevance */

/**
 * Ganesha: role fit + qualification + priority in one round trip.
 * @param {object} [opts]
 * @returns {Record<string, object>}
 */
export function buildGaneshaQuestions(opts = {}) {
  return {
    role_relevance: {
      type: 'choice',
      instructions:
        'Which job family best describes this posting relative to the candidate target roles and skills in STATE?',
      criteria: {
        AI_ENGINEERING: 'Applied AI, LLM apps, RAG, agents, GenAI platform/engineering',
        ML_ENGINEERING: 'ML training, MLOps, model deployment, classical ML',
        DATA_SCIENCE: 'Data science, experimentation, modeling, research-oriented DS',
        DATA_ANALYTICS: 'BI, reporting, SQL dashboards, analytics engineering light',
        OTHER: 'Unrelated or mixed role family',
      },
    },
    qualification: {
      type: 'choice',
      instructions:
        'Given hard constraints and role fit in STATE, should this job enter the candidate pipeline?',
      criteria: {
        REJECT: 'Clear mismatch, blocker, scam signal, or waste of candidate time',
        REVIEW: 'Borderline — needs human or deeper check before Groq analysis',
        QUALIFY: 'Passes filters and is plausibly worth matching/scoring',
      },
    },
    priority: {
      type: 'choice',
      instructions: 'How urgently should this job be reviewed after deterministic scoring?',
      criteria: {
        LOW: 'Weak fit or noisy listing — deprioritize Groq spend',
        MEDIUM: 'Reasonable fit — standard queue',
        HIGH: 'Strong fit — prioritize deeper analysis if plan allows',
        REVIEW: 'Ambiguous — human review before any Groq call',
      },
    },
    scam_or_low_quality: {
      type: 'noul',
      instructions:
        'Is this posting likely a scam, ghost job, duplicate spam, or clearly low-quality listing (yes = flag)?',
    },
  };
}

/**
 * Narada: classify discovered job type / seniority bucket.
 * @returns {Record<string, object>}
 */
export function buildNaradaQuestions() {
  return {
    seniority: {
      type: 'choice',
      instructions: 'Seniority level implied by title and description.',
      criteria: {
        INTERN: 'Intern or student',
        JUNIOR: 'Junior / entry',
        MID: 'Mid level',
        SENIOR: 'Senior',
        STAFF_PLUS: 'Staff, principal, lead, director+',
        UNKNOWN: 'Cannot determine',
      },
    },
    employment_type: {
      type: 'choice',
      instructions: 'Primary employment type.',
      criteria: {
        FULL_TIME: 'Full-time employee',
        CONTRACT: 'Contract or temp',
        PART_TIME: 'Part-time',
        UNKNOWN: 'Not specified',
      },
    },
  };
}

/**
 * Vishwakarma: next workflow stage routing.
 * @param {Record<string, string>} routeCriteria
 * @returns {Record<string, object>}
 */
export function buildRouteQuestion(routeCriteria) {
  return {
    next_stage: {
      type: 'choice',
      instructions: 'Pick the next workflow stage given STATE and deterministic scores.',
      criteria: routeCriteria,
    },
  };
}

/**
 * Gate: should we spend Groq on deep Brihaspati analysis?
 * @returns {Record<string, object>}
 */
export function buildGroqGateQuestion() {
  return {
    run_deep_analysis: {
      type: 'noul',
      instructions:
        'Should we run expensive LLM deep job-fit analysis now? Yes only if fit is promising and not already rejected by rules.',
    },
  };
}

export default {
  buildGaneshaQuestions,
  buildNaradaQuestions,
  buildRouteQuestion,
  buildGroqGateQuestion,
};
