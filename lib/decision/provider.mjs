// @ts-check
/**
 * DecisionProvider — Rules → Jev → rule fallback. Keeps Job-hunt vendor-agnostic.
 */
import { evaluateSystemOne, isJevConfigured, choiceAnswer, noulAnswer, confidenceOf } from './jev.mjs';
import { buildGaneshaQuestions, buildNaradaQuestions, buildRouteQuestion, buildGroqGateQuestion } from './schemas.mjs';
import { rulesQualification } from './rules.mjs';
import { fallbackGaneshaDecision, fallbackGroqGate } from './fallback.mjs';
import { logDecisionEvent, hashInput } from './log-decision.mjs';
import { formatJobState, formatProfileState } from './state-format.mjs';

/**
 * @typedef {object} DecisionContext
 * @property {string} [userId]
 * @property {string} [jobId]
 * @property {string} [agent]
 * @property {string} [planId]
 */

/**
 * @param {DecisionContext} ctx
 */
export function createDecisionProvider(ctx = {}) {
  /**
   * @param {string|object} state
   * @param {Record<string, object>} questions
   * @param {string} decisionType
   */
  async function classify(state, questions, decisionType) {
    const stateStr = typeof state === 'string' ? state : JSON.stringify(state);
    const inputHash = hashInput(stateStr + JSON.stringify(Object.keys(questions)));

    if (!isJevConfigured()) {
      return { provider: 'RULE', answers: {}, inputHash, skipped: true };
    }

    try {
      const result = await evaluateSystemOne({ state, questions });
      await logDecisionEvent({
        userId: ctx.userId,
        jobId: ctx.jobId,
        agent: ctx.agent || 'unknown',
        decisionType,
        provider: 'JEV',
        decision: JSON.stringify(result.answers),
        confidence: null,
        inputHash,
        metadata: { model: result.model, usage: result.usage },
      });
      return { ...result, inputHash };
    } catch (err) {
      console.warn('Jev classify failed, using rules:', err.message);
      return { provider: 'RULE', answers: {}, inputHash, error: err.message };
    }
  }

  /**
   * Ganesha pipeline decision (after hard rules pass).
   * @param {object} job
   * @param {object} profile
   * @param {number} [deterministicScore]
   */
  async function evaluateGanesha(job, profile, deterministicScore = 0) {
    const hard = rulesQualification(job, profile);
    if (hard.qualification === 'REJECT') {
      const decision = {
        qualification: 'REJECT',
        priority: 'LOW',
        roleRelevance: 'OTHER',
        scamFlag: false,
        provider: 'RULE',
        confidence: 0.95,
        details: hard.reason || hard.details,
      };
      await logDecisionEvent({
        userId: ctx.userId,
        jobId: job.id,
        agent: 'Ganesha',
        decisionType: 'qualification',
        provider: 'RULE',
        decision: decision.qualification,
        confidence: decision.confidence,
        inputHash: hashInput(JSON.stringify({ job: job.id, hard: true })),
      });
      return decision;
    }

    const state = {
      job: formatJobState(job),
      candidate: formatProfileState(profile),
      deterministic_score: deterministicScore,
    };

    let answers;
    let provider = 'JEV';
    if (isJevConfigured()) {
      try {
        const res = await evaluateSystemOne({
          state,
          questions: buildGaneshaQuestions(),
        });
        answers = res.answers;
        await logDecisionEvent({
          userId: ctx.userId,
          jobId: job.id,
          agent: 'Ganesha',
          decisionType: 'ganesha_bundle',
          provider: 'JEV',
          decision: JSON.stringify({
            qualification: choiceAnswer(answers.qualification),
            priority: choiceAnswer(answers.priority),
            role_relevance: choiceAnswer(answers.role_relevance),
          }),
          confidence: confidenceOf(answers.qualification),
          inputHash: hashInput(JSON.stringify(state)),
          metadata: { model: res.model },
        });
      } catch (err) {
        console.warn('Ganesha Jev error:', err.message);
        const fb = fallbackGaneshaDecision({ job, profile, deterministicScore });
        answers = fb.answers;
        provider = 'RULE';
      }
    } else {
      const fb = fallbackGaneshaDecision({ job, profile, deterministicScore });
      answers = fb.answers;
      provider = 'RULE';
    }

    const scamNoul = noulAnswer(answers.scam_or_low_quality);
    const decision = {
      qualification: /** @type {any} */ (choiceAnswer(answers.qualification) || 'REVIEW'),
      priority: /** @type {any} */ (choiceAnswer(answers.priority) || 'REVIEW'),
      roleRelevance: /** @type {any} */ (choiceAnswer(answers.role_relevance) || 'OTHER'),
      scamFlag: scamNoul !== null && scamNoul > 0.65,
      provider,
      confidence: confidenceOf(answers.qualification),
      details: 'Decision layer evaluation complete',
    };

    if (decision.scamFlag) {
      decision.qualification = 'REJECT';
      decision.priority = 'LOW';
    }

    return decision;
  }

  /**
   * Narada: lightweight classification on normalized job.
   * @param {object} job
   */
  async function classifyJobPosting(job) {
    const state = formatJobState(job);
    if (!isJevConfigured()) {
      return { provider: 'RULE', seniority: 'UNKNOWN', employmentType: 'UNKNOWN' };
    }
    try {
      const res = await evaluateSystemOne({ state, questions: buildNaradaQuestions() });
      return {
        provider: 'JEV',
        seniority: choiceAnswer(res.answers.seniority),
        employmentType: choiceAnswer(res.answers.employment_type),
      };
    } catch {
      return { provider: 'RULE', seniority: 'UNKNOWN', employmentType: 'UNKNOWN' };
    }
  }

  /**
   * @param {object} params
   */
  async function shouldRunGroqAnalysis(params) {
    const { priority, deterministicScore, planId = ctx.planId || 'free' } = params;
    const state = {
      plan_id: planId,
      priority,
      deterministic_score: deterministicScore,
    };

    if (isJevConfigured()) {
      try {
        const res = await evaluateSystemOne({ state, questions: buildGroqGateQuestion() });
        const noul = noulAnswer(res.answers.run_deep_analysis);
        const run = noul !== null && noul >= 0.55;
        await logDecisionEvent({
          userId: ctx.userId,
          jobId: params.jobId,
          agent: 'Vishwakarma',
          decisionType: 'groq_gate',
          provider: 'JEV',
          decision: run ? 'RUN_GROQ' : 'SKIP_GROQ',
          confidence: noul,
          inputHash: hashInput(JSON.stringify(state)),
        });
        return { run, provider: 'JEV', confidence: noul };
      } catch (err) {
        console.warn('Groq gate Jev error:', err.message);
      }
    }

    const fb = fallbackGroqGate({ planId, priority, deterministicScore });
    const noul = noulAnswer(fb.answers.run_deep_analysis);
    return { run: noul !== null && noul >= 0.55, provider: 'RULE', confidence: noul };
  }

  /**
   * @param {object} state
   * @param {Record<string, string>} routes
   */
  async function route(state, routes) {
    const res = await classify(state, buildRouteQuestion(routes), 'workflow_route');
    const choice = choiceAnswer(res.answers?.next_stage);
    return { route: choice, provider: res.provider || 'RULE' };
  }

  return {
    classify,
    evaluateGanesha,
    classifyJobPosting,
    shouldRunGroqAnalysis,
    route,
  };
}

export default { createDecisionProvider };
