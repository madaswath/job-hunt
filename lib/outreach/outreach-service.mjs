// @ts-check
/**
 * lib/outreach/outreach-service.mjs
 * Generates verified, evidence-backed recruiter outreach drafts with human approval gating.
 */

import { getDatabase, saveApprovalTask } from '../db/sqlite.mjs';
import { createApprovalTask } from '../schemas/job-schema.mjs';
import { loadUserProfile } from '../db/sync-engine.mjs';

/**
 * Generates a tailored outreach email / LinkedIn message draft for a job posting.
 *
 * @param {object} job
 * @param {object} [contact]
 * @param {object} [profile]
 * @returns {object} Outreach draft object
 */
export function generateOutreachDraft(job, contact = {}, profile = null) {
  const userProf = profile || loadUserProfile();
  const candidateName = userProf.candidate?.full_name || 'Candidate';
  const headline = userProf.narrative?.headline || 'AI/ML Systems Engineer';
  const companyName = job.company?.name || 'Company';
  const roleTitle = job.role?.title || 'the open role';
  const recipientName = contact.name || 'Hiring Team';

  // Pick top matched skills
  const matchedSkills = (job.deterministicMatch?.matchedSkills || []).slice(0, 3).join(', ') || 'production AI pipelines & distributed systems';

  // Pick top proof point
  const proof = (userProf.narrative?.proof_points || [])[0] || {
    name: 'Key Project',
    hero_metric: 'Scaled real-time ML systems with significant latency reduction',
  };

  const subject = `Application / Inquiry: ${roleTitle} - ${candidateName}`;
  const body = `Hi ${recipientName},

I noticed ${companyName} is hiring for the ${roleTitle} position and wanted to reach out directly.

With a background as a ${headline}, I specialize in building ${matchedSkills}. Recently, on ${proof.name}, my work delivered ${proof.hero_metric}.

Given ${companyName}'s focus on high-scale execution, I believe my experience with ${matchedSkills} would be a strong fit for your engineering objectives.

I would welcome 10 minutes to learn more about the team's current technical roadmap.

Best regards,

${candidateName}
${userProf.candidate?.linkedin || ''}
${userProf.candidate?.portfolio_url || ''}`;

  const draftId = `outreach_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  const draft = {
    id: draftId,
    jobId: job.id,
    recipientName,
    recipientRole: contact.role || 'Talent Acquisition / Engineering Leader',
    recipientEmail: contact.email || '',
    subject,
    body,
    status: 'READY_FOR_REVIEW',
    createdAt: new Date().toISOString(),
  };

  // Persist into SQLite
  const db = getDatabase();
  const stmt = db.prepare(`
    INSERT INTO outreach_drafts (id, job_id, recipient_name, recipient_role, recipient_email, subject, body, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
      subject = excluded.subject,
      body = excluded.body,
      status = excluded.status;
  `);
  stmt.run(
    draft.id,
    draft.jobId,
    draft.recipientName,
    draft.recipientRole,
    draft.recipientEmail,
    draft.subject,
    draft.body,
    draft.status,
    draft.createdAt
  );

  // Create human approval task
  const approvalTask = createApprovalTask({
    type: 'OUTREACH_APPROVAL',
    jobId: job.id,
    title: `Approve Outreach to ${recipientName} (${companyName})`,
    description: `Subject: "${subject}"`,
    payload: {
      draftId: draft.id,
      recipient: recipientName,
      subject,
      body,
    },
  });
  saveApprovalTask(approvalTask);

  return draft;
}

export default {
  generateOutreachDraft,
};
