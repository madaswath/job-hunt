// @ts-check
/**
 * lib/db/sync-engine.mjs
 * Bi-directional sync between canonical files (Markdown/TSV/YAML) and the fast SQLite index.
 */

import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { load } from 'js-yaml';
import { upsertJob, saveApprovalTask } from './sqlite.mjs';
import { normalizeJob } from '../normalization/job-normalizer.mjs';
import { qualifyJob } from '../matching/qualification-engine.mjs';
import { scoreJobDeterministically } from '../matching/deterministic-scorer.mjs';
import { createApprovalTask } from '../schemas/job-schema.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const REPO_ROOT = join(__dirname, '../..');

/**
 * Loads the active user profile (from config/profile.yml with fallback to profile.example.yml).
 * @returns {object}
 */
export function loadUserProfile() {
  const customProfile = join(REPO_ROOT, 'config/profile.yml');
  const exampleProfile = join(REPO_ROOT, 'config/profile.example.yml');

  const targetPath = existsSync(customProfile) ? customProfile : exampleProfile;
  if (!existsSync(targetPath)) return {};

  try {
    const content = readFileSync(targetPath, 'utf8');
    return load(content) || {};
  } catch (err) {
    console.error('Error loading profile:', err);
    return {};
  }
}

/**
 * Parses data/pipeline.md into Job entities.
 * @param {object} profile
 * @returns {object[]}
 */
export function syncPipelineFile(profile) {
  const pipelinePath = join(REPO_ROOT, 'data/pipeline.md');
  if (!existsSync(pipelinePath)) return [];

  const content = readFileSync(pipelinePath, 'utf8');
  const lines = content.split('\n');
  const jobs = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || !trimmed.startsWith('-') || !trimmed.includes('http')) continue;

    const job = normalizeJob(trimmed, 'pipeline');
    
    // Qualify & score
    const qual = qualifyJob(job, profile);
    if (!qual.qualified) {
      job.state = 'REJECTED';
      job.rejectionReason = qual.reason;
      job.rejectionNote = qual.details;
    } else {
      job.state = 'QUALIFIED';
      job.deterministicMatch = scoreJobDeterministically(job, profile);
      job.match_score = job.deterministicMatch.score;

      if (job.deterministicMatch.score >= 75) {
        job.state = 'REVIEW';
        // Create an approval task for human review
        saveApprovalTask(
          createApprovalTask({
            type: 'JOB_REVIEW',
            jobId: job.id,
            title: `Review ${job.role.title} at ${job.company.name}`,
            description: `Match score: ${job.deterministicMatch.score}% - ${job.location.text}`,
            payload: { match: job.deterministicMatch },
          })
        );
      }
    }

    upsertJob(job);
    jobs.push(job);
  }

  return jobs;
}

/**
 * Reads existing reports in reports/*.md and hydrates evaluated data into SQLite.
 * @returns {number}
 */
export function syncReports() {
  const reportsDir = join(REPO_ROOT, 'reports');
  if (!existsSync(reportsDir)) return 0;

  const files = readdirSync(reportsDir).filter((f) => f.endsWith('.md') && !f.startsWith('.'));
  let synced = 0;

  for (const file of files) {
    const fullPath = join(reportsDir, file);
    try {
      const content = readFileSync(fullPath, 'utf8');
      
      // Extract title/company from filename: e.g. 001-company-slug-2026-10-01.md
      const match = file.match(/^(\d+)-([^-]+(?:-[^-]+)*?)-(\d{4}-\d{2}-\d{2})\.md$/);
      const reportNum = match ? match[1] : '';
      const companySlug = match ? match[2].replace(/-/g, ' ') : 'Company';

      // Parse score and summary if available in report
      const scoreMatch = content.match(/\*\*Score:\*\*\s*([0-9.]+)\/5/i) || content.match(/Score:\s*([0-9.]+)\/5/i);
      const evalScore = scoreMatch ? parseFloat(scoreMatch[1]) : 4.0;
      const matchScore = Math.round((evalScore / 5) * 100);

      const job = normalizeJob({
        url: `local:reports/${file}`,
        company: companySlug,
        title: 'Evaluated Position',
        state: 'QUALIFIED',
      });
      job.reportNumber = reportNum;
      job.reportPath = `reports/${file}`;
      job.match_score = matchScore;
      job.llmEvaluation = {
        score: evalScore,
        reportPath: `reports/${file}`,
      };

      upsertJob(job);
      synced++;
    } catch (e) {
      console.warn(`Could not sync report ${file}:`, e);
    }
  }

  return synced;
}

/**
 * Full synchronization of all local data sources into the SQLite index.
 * @returns {{ jobsCount: number, reportsCount: number, profile: object }}
 */
export function syncAll() {
  const profile = loadUserProfile();
  const pipelineJobs = syncPipelineFile(profile);
  const reportsCount = syncReports();

  return {
    jobsCount: pipelineJobs.length,
    reportsCount,
    profile,
  };
}

export default {
  loadUserProfile,
  syncPipelineFile,
  syncReports,
  syncAll,
};
