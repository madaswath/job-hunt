// @ts-check
/**
 * lib/db/sqlite.mjs
 * High-performance SQLite derived index using Node 22+ built-in node:sqlite.
 * Indexes canonical files for instant dashboard querying, filtering, and state management.
 */

import { DatabaseSync } from 'node:sqlite';
import { existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const REPO_ROOT = join(__dirname, '../..');
const DB_PATH = join(REPO_ROOT, 'data/career-ops.db');

let _db = null;

/**
 * Initializes and returns the SQLite database connection.
 * @param {string} [customPath]
 * @returns {DatabaseSync}
 */
export function getDatabase(customPath) {
  if (_db) return _db;

  const targetPath = customPath || DB_PATH;
  const targetDir = dirname(targetPath);
  if (!existsSync(targetDir)) {
    mkdirSync(targetDir, { recursive: true });
  }

  const db = new DatabaseSync(targetPath);
  db.exec('PRAGMA journal_mode = WAL;');
  db.exec('PRAGMA synchronous = NORMAL;');

  // Initialize schema
  db.exec(`
    CREATE TABLE IF NOT EXISTS jobs (
      id TEXT PRIMARY KEY,
      provider TEXT,
      url TEXT,
      canonical_url TEXT,
      company TEXT NOT NULL,
      domain TEXT,
      title TEXT NOT NULL,
      seniority TEXT,
      location TEXT,
      is_remote INTEGER DEFAULT 0,
      is_hybrid INTEGER DEFAULT 0,
      currency TEXT,
      min_salary REAL,
      max_salary REAL,
      description TEXT,
      state TEXT DEFAULT 'DISCOVERED',
      rejection_reason TEXT,
      match_score INTEGER DEFAULT 0,
      must_have_met INTEGER DEFAULT 0,
      must_have_total INTEGER DEFAULT 0,
      raw_json TEXT,
      discovered_at TEXT,
      updated_at TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state);
    CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs(match_score);
    CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);

    CREATE TABLE IF NOT EXISTS approval_tasks (
      id TEXT PRIMARY KEY,
      type TEXT NOT NULL,
      job_id TEXT,
      title TEXT NOT NULL,
      description TEXT,
      payload_json TEXT,
      status TEXT DEFAULT 'PENDING',
      created_at TEXT,
      reviewed_at TEXT,
      FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_tasks_status ON approval_tasks(status);

    CREATE TABLE IF NOT EXISTS outreach_drafts (
      id TEXT PRIMARY KEY,
      job_id TEXT,
      recipient_name TEXT,
      recipient_role TEXT,
      recipient_email TEXT,
      subject TEXT,
      body TEXT,
      status TEXT DEFAULT 'DRAFT',
      created_at TEXT,
      FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS user_preferences (
      key TEXT PRIMARY KEY,
      value_json TEXT,
      updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS status_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id TEXT,
      from_state TEXT,
      to_state TEXT,
      source TEXT,
      note TEXT,
      created_at TEXT
    );
  `);

  _db = db;
  return db;
}

/**
 * Upserts a canonical Job into SQLite.
 * @param {object} job
 */
export function upsertJob(job) {
  const db = getDatabase();
  const stmt = db.prepare(`
    INSERT INTO jobs (
      id, provider, url, canonical_url, company, domain, title, seniority,
      location, is_remote, is_hybrid, currency, min_salary, max_salary,
      description, state, rejection_reason, match_score, must_have_met,
      must_have_total, raw_json, discovered_at, updated_at
    ) VALUES (
      ?, ?, ?, ?, ?, ?, ?, ?,
      ?, ?, ?, ?, ?, ?,
      ?, ?, ?, ?, ?,
      ?, ?, ?, ?
    )
    ON CONFLICT(id) DO UPDATE SET
      company = excluded.company,
      domain = excluded.domain,
      title = excluded.title,
      seniority = excluded.seniority,
      location = excluded.location,
      is_remote = excluded.is_remote,
      is_hybrid = excluded.is_hybrid,
      currency = excluded.currency,
      min_salary = excluded.min_salary,
      max_salary = excluded.max_salary,
      description = excluded.description,
      state = CASE WHEN jobs.state IN ('APPLIED', 'INTERVIEW', 'OFFER', 'REJECTED') THEN jobs.state ELSE excluded.state END,
      rejection_reason = COALESCE(excluded.rejection_reason, jobs.rejection_reason),
      match_score = excluded.match_score,
      must_have_met = excluded.must_have_met,
      must_have_total = excluded.must_have_total,
      raw_json = excluded.raw_json,
      updated_at = excluded.updated_at;
  `);

  const matchScore = job.deterministicMatch?.score ?? (job.match_score || 0);
  const mustMet = job.deterministicMatch?.mustHaveMet ?? 0;
  const mustTotal = job.deterministicMatch?.mustHaveTotal ?? 0;

  stmt.run(
    job.id,
    job.source?.provider || 'direct',
    job.source?.url || '',
    job.source?.canonicalUrl || job.source?.url || '',
    job.company?.name || 'Unknown',
    job.company?.domain || '',
    job.role?.title || 'Unknown',
    job.role?.seniority || '',
    job.location?.text || '',
    job.location?.remote ? 1 : 0,
    job.location?.hybrid ? 1 : 0,
    job.compensation?.currency || 'USD',
    job.compensation?.min || null,
    job.compensation?.max || null,
    job.description || '',
    job.state || 'DISCOVERED',
    job.rejectionReason || null,
    matchScore,
    mustMet,
    mustTotal,
    JSON.stringify(job),
    job.discoveredAt || new Date().toISOString(),
    new Date().toISOString()
  );
}

/**
 * Retrieves a job by ID.
 * @param {string} id
 * @returns {object | null}
 */
export function getJobById(id) {
  const db = getDatabase();
  const stmt = db.prepare('SELECT * FROM jobs WHERE id = ?');
  const row = stmt.get(id);
  if (!row) return null;
  return JSON.parse(/** @type {any} */ (row).raw_json || '{}');
}

/**
 * Lists jobs with filtering, pagination and sorting.
 * @param {object} params
 * @param {string} [params.state]
 * @param {number} [params.minScore]
 * @param {boolean} [params.isRemote]
 * @param {string} [params.search]
 * @param {number} [params.limit]
 * @param {number} [params.offset]
 * @returns {{ jobs: object[], total: number }}
 */
export function listJobs({ state, minScore, isRemote, search, limit = 50, offset = 0 } = {}) {
  const db = getDatabase();
  let whereClauses = [];
  let params = [];

  if (state && state !== 'ALL') {
    whereClauses.push('state = ?');
    params.push(state);
  }
  if (typeof minScore === 'number') {
    whereClauses.push('match_score >= ?');
    params.push(minScore);
  }
  if (isRemote) {
    whereClauses.push('is_remote = 1');
  }
  if (search) {
    whereClauses.push('(company LIKE ? OR title LIKE ? OR location LIKE ?)');
    const term = `%${search}%`;
    params.push(term, term, term);
  }

  const whereSql = whereClauses.length > 0 ? `WHERE ${whereClauses.join(' AND ')}` : '';

  const countStmt = db.prepare(`SELECT COUNT(*) as cnt FROM jobs ${whereSql}`);
  const totalRow = countStmt.get(...params);
  const total = Number(/** @type {any} */ (totalRow)?.cnt || 0);

  const queryParams = [...params, limit, offset];
  const listStmt = db.prepare(`
    SELECT * FROM jobs ${whereSql}
    ORDER BY match_score DESC, discovered_at DESC
    LIMIT ? OFFSET ?
  `);
  const rows = listStmt.all(...queryParams);

  const jobs = rows.map((r) => {
    try {
      return JSON.parse(/** @type {any} */ (r).raw_json || '{}');
    } catch {
      return r;
    }
  });

  return { jobs, total };
}

/**
 * Updates a job state.
 * @param {string} id
 * @param {string} newState
 * @param {string} [rejectionReason]
 * @param {string} [note]
 */
export function updateJobState(id, newState, rejectionReason = '', note = '') {
  const db = getDatabase();
  const current = getJobById(id);
  if (!current) return false;

  const oldState = current.state;
  current.state = newState;
  if (rejectionReason) current.rejectionReason = rejectionReason;
  if (note) current.rejectionNote = note;
  current.updatedAt = new Date().toISOString();

  const stmt = db.prepare(`
    UPDATE jobs SET state = ?, rejection_reason = ?, raw_json = ?, updated_at = ?
    WHERE id = ?
  `);
  stmt.run(newState, rejectionReason || null, JSON.stringify(current), new Date().toISOString(), id);

  // Record status event
  const evtStmt = db.prepare(`
    INSERT INTO status_events (job_id, from_state, to_state, source, note, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  evtStmt.run(id, oldState, newState, 'user_action', note || '', new Date().toISOString());

  return true;
}

/**
 * Creates or updates an approval task.
 * @param {object} task
 */
export function saveApprovalTask(task) {
  const db = getDatabase();
  const stmt = db.prepare(`
    INSERT INTO approval_tasks (id, type, job_id, title, description, payload_json, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
      status = excluded.status,
      reviewed_at = excluded.reviewed_at;
  `);
  stmt.run(
    task.id,
    task.type,
    task.jobId,
    task.title,
    task.description || '',
    JSON.stringify(task.payload || {}),
    task.status || 'PENDING',
    task.createdAt || new Date().toISOString()
  );
}

/**
 * Lists pending approval tasks.
 * @param {string} [status]
 * @returns {object[]}
 */
export function listApprovalTasks(status = 'PENDING') {
  const db = getDatabase();
  const stmt = db.prepare(`
    SELECT t.*, j.company, j.title as job_title, j.match_score
    FROM approval_tasks t
    LEFT JOIN jobs j ON t.job_id = j.id
    WHERE t.status = ?
    ORDER BY t.created_at DESC
  `);
  const rows = stmt.all(status);
  return rows.map((r) => {
    const raw = /** @type {any} */ (r);
    return {
      ...raw,
      payload: JSON.parse(raw.payload_json || '{}'),
    };
  });
}

/**
 * Returns aggregated pipeline and review metrics.
 * @returns {object}
 */
export function getDashboardSummary() {
  const db = getDatabase();
  const totalJobs = Number(/** @type {any} */ (db.prepare('SELECT COUNT(*) as c FROM jobs').get())?.c || 0);
  const discovered = Number(/** @type {any} */ (db.prepare("SELECT COUNT(*) as c FROM jobs WHERE state = 'DISCOVERED'").get())?.c || 0);
  const qualified = Number(/** @type {any} */ (db.prepare("SELECT COUNT(*) as c FROM jobs WHERE state = 'QUALIFIED' OR state = 'REVIEW'").get())?.c || 0);
  const strongMatches = Number(/** @type {any} */ (db.prepare('SELECT COUNT(*) as c FROM jobs WHERE match_score >= 80').get())?.c || 0);
  const approved = Number(/** @type {any} */ (db.prepare("SELECT COUNT(*) as c FROM jobs WHERE state = 'APPROVED'").get())?.c || 0);
  const applied = Number(/** @type {any} */ (db.prepare("SELECT COUNT(*) as c FROM jobs WHERE state = 'APPLIED'").get())?.c || 0);
  const pendingTasks = Number(/** @type {any} */ (db.prepare("SELECT COUNT(*) as c FROM approval_tasks WHERE status = 'PENDING'").get())?.c || 0);

  const topJobs = db.prepare(`
    SELECT id, company, title, location, is_remote, match_score, state
    FROM jobs
    WHERE state NOT IN ('REJECTED', 'CLOSED')
    ORDER BY match_score DESC
    LIMIT 6
  `).all();

  const rejectionStats = db.prepare(`
    SELECT rejection_reason, COUNT(*) as count
    FROM jobs
    WHERE rejection_reason IS NOT NULL AND rejection_reason != ''
    GROUP BY rejection_reason
    ORDER BY count DESC
  `).all();

  return {
    totalJobs,
    discovered,
    qualified,
    strongMatches,
    approved,
    applied,
    pendingTasks,
    topJobs,
    rejectionStats,
    timestamp: new Date().toISOString(),
  };
}

export default {
  getDatabase,
  upsertJob,
  getJobById,
  listJobs,
  updateJobState,
  saveApprovalTask,
  listApprovalTasks,
  getDashboardSummary,
};
