// @ts-check
/**
 * lib/workflow/orchestrator.mjs
 * Structured Stage-by-Stage Workflow Execution Engine.
 *
 * Pipeline:
 * Ingest -> Normalize -> Liveness -> Hard Filter -> Deterministic Score -> LLM Evaluate -> Approval Queue
 */

import { normalizeJob } from '../normalization/job-normalizer.mjs';
import { scoreJobDeterministically } from '../matching/deterministic-scorer.mjs';
import { upsertJob, saveApprovalTask, getJobById } from '../db/sqlite.mjs';
import { createApprovalTask } from '../schemas/job-schema.mjs';
import { loadUserProfile } from '../db/sync-engine.mjs';
import { checkLivenessViaApi } from '../../liveness-api.mjs';
import { createDecisionProvider } from '../decision/provider.mjs';
import { runDeepJobAnalysis } from './deep-analysis.mjs';

/**
 * Executes the complete qualification and evaluation workflow for a single job.
 *
 * @param {object | string} rawInput
 * @param {object} [options]
 * @param {object} [options.profile]
 * @param {number} [options.evalThreshold=75]
 * @param {string} [options.userId]
 * @param {string} [options.planId='free']
 * @returns {Promise<object>}
 */
export async function processJobThroughWorkflow(rawInput, options = {}) {
  const profile = options.profile || loadUserProfile();
  const evalThreshold = options.evalThreshold ?? 75;
  const planId = options.planId || 'free';
  const decisions = createDecisionProvider({
    userId: options.userId,
    planId,
    agent: 'Vishwakarma',
  });

  // 1. Ingestion & Normalization
  const job = normalizeJob(rawInput);
  job.state = 'DISCOVERED';

  const naradaMeta = await decisions.classifyJobPosting(job);
  if (naradaMeta.seniority) {
    job.role = job.role || {};
    job.role.seniority = job.role.seniority || naradaMeta.seniority;
  }
  job.decisionMeta = { ...(job.decisionMeta || {}), narada: naradaMeta };

  // 2. Liveness Check (zero-token fast API check if recognized ATS)
  if (job.source?.url && job.source.url.startsWith('http')) {
    try {
      const liveCheck = await checkLivenessViaApi(job.source.url);
      if (liveCheck && liveCheck.result === 'expired') {
        job.state = 'CLOSED';
        job.rejectionReason = 'JOB_EXPIRED';
        job.rejectionNote = `Posting detected as closed/expired (${liveCheck.reason || 'API gone'}).`;
        upsertJob(job);
        return { success: false, job, stage: 'liveness', reason: job.rejectionReason };
      }
    } catch {
      // Non-blocking fallback
    }
  }

  // 3–4. Deterministic scoring first (cheap), then Ganesha + Jev decision layer
  job.deterministicMatch = scoreJobDeterministically(job, profile);
  job.match_score = job.deterministicMatch.score;

  const ganesha = await decisions.evaluateGanesha(job, profile, job.match_score);
  job.decisionMeta = { ...(job.decisionMeta || {}), ganesha };

  if (ganesha.qualification === 'REJECT') {
    job.state = 'REJECTED';
    job.rejectionReason = ganesha.scamFlag ? 'LOW_QUALITY_POSTING' : 'ROLE_MISMATCH';
    job.rejectionNote = ganesha.details || 'Rejected by Ganesha decision layer';
    upsertJob(job);
    return { success: false, job, stage: 'ganesha', reason: job.rejectionReason, ganesha };
  }

  if (ganesha.qualification === 'REVIEW' && job.match_score < evalThreshold) {
    job.state = 'REVIEW';
    job.rejectionNote = 'Borderline fit — review before Groq analysis';
    upsertJob(job);
    return { success: true, job, stage: 'review', ganesha };
  }

  job.state = 'QUALIFIED';

  const groqGate = await decisions.shouldRunGroqAnalysis({
    jobId: job.id,
    priority: ganesha.priority,
    deterministicScore: job.match_score,
    planId,
  });
  job.decisionMeta.groqGate = groqGate;

  let deepAnalysis = null;
  if (groqGate.run && job.match_score >= Math.min(evalThreshold, 60)) {
    deepAnalysis = await runDeepJobAnalysis({ job, profile, userId: options.userId });
    job.decisionMeta.deepAnalysis = {
      ran: deepAnalysis.ran,
      provider: deepAnalysis.provider,
    };
    if (deepAnalysis.summary) {
      job.llmSummary = deepAnalysis.summary;
    }
  }

  // 5. Shortlist & Approval Queue Creation
  if (job.deterministicMatch.score >= evalThreshold) {
    job.state = 'REVIEW';
    const task = createApprovalTask({
      type: 'JOB_REVIEW',
      jobId: job.id,
      title: `Review ${job.role.title} at ${job.company.name}`,
      description: `Deterministic Score: ${job.deterministicMatch.score}% | ${job.location.text}`,
      payload: {
        score: job.deterministicMatch.score,
        breakdown: job.deterministicMatch.breakdown,
        whyItFits: job.deterministicMatch.whyItFits,
        risks: job.deterministicMatch.risks,
      },
    });
    saveApprovalTask(task);
  }

  // Persist into SQLite index
  upsertJob(job);

  return {
    success: true,
    job,
    stage: job.deterministicMatch.score >= evalThreshold ? 'shortlisted' : 'qualified',
    ganesha,
    groqGate,
    deepAnalysis,
  };
}

/**
 * Batch processes multiple job listings through the workflow engine.
 *
 * @param {Array<object | string>} items
 * @param {object} [options]
 * @returns {Promise<{ processed: number, qualified: number, shortlisted: number, rejected: number }>}
 */
export async function processBatchWorkflow(items, options = {}) {
  const profile = options.profile || loadUserProfile();
  const planId = options.planId || 'free';
  let qualifiedCount = 0;
  let shortlistedCount = 0;
  let rejectedCount = 0;

  for (const item of items) {
    const res = await processJobThroughWorkflow(item, { ...options, profile, planId });
    if (!res.success) {
      rejectedCount++;
    } else if (res.stage === 'shortlisted') {
      shortlistedCount++;
      qualifiedCount++;
    } else {
      qualifiedCount++;
    }
  }

  return {
    processed: items.length,
    qualified: qualifiedCount,
    shortlisted: shortlistedCount,
    rejected: rejectedCount,
  };
}

export default {
  processJobThroughWorkflow,
  processBatchWorkflow,
};
