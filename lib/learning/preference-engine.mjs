// @ts-check
/**
 * lib/learning/preference-engine.mjs
 * Structured rejection learning and continuous preference calibration loop.
 */

import { getDatabase } from '../db/sqlite.mjs';

/**
 * Analyzes past user rejections and calculates adapted scoring weights.
 * @returns {object}
 */
export function analyzeRejectionPatterns() {
  const db = getDatabase();

  const totalDecisions = Number(/** @type {any} */ (db.prepare('SELECT COUNT(*) as c FROM jobs WHERE state IN (\'APPROVED\', \'APPLIED\', \'REJECTED\')').get())?.c || 0);
  const totalRejections = Number(/** @type {any} */ (db.prepare('SELECT COUNT(*) as c FROM jobs WHERE state = \'REJECTED\'').get())?.c || 0);

  const reasons = db.prepare(`
    SELECT rejection_reason, COUNT(*) as count
    FROM jobs
    WHERE state = 'REJECTED' AND rejection_reason IS NOT NULL AND rejection_reason != ''
    GROUP BY rejection_reason
    ORDER BY count DESC
  `).all();

  // Dynamic weight adjustments
  const learnedModifiers = {
    minSeniorityBoost: 0,
    genAiWeightBonus: 0,
    remoteOnlyStrictness: false,
    salaryFloorAdjustment: 0,
  };

  reasons.forEach((r) => {
    const raw = /** @type {any} */ (r);
    const reason = raw.rejection_reason;
    const count = Number(raw.count);

    if (reason === 'TOO_JUNIOR' && count >= 3) {
      learnedModifiers.minSeniorityBoost += 15;
    }
    if (reason === 'NOT_ENOUGH_GENAI' && count >= 2) {
      learnedModifiers.genAiWeightBonus += 10;
    }
    if (reason === 'RELOCATION_REQUIRED' && count >= 2) {
      learnedModifiers.remoteOnlyStrictness = true;
    }
  });

  const insightReport = {
    totalDecisions,
    totalRejections,
    rejectionRate: totalDecisions > 0 ? Math.round((totalRejections / totalDecisions) * 100) : 0,
    reasonsBreakdown: reasons,
    learnedModifiers,
    recommendation: totalDecisions >= 10
      ? 'Learned preferences are active. Deterministic match weights are dynamically calibrated.'
      : 'Keep making approvals/rejections (need at least 10 decisions to calibrate weights).',
  };

  // Save to user_preferences table
  const saveStmt = db.prepare(`
    INSERT INTO user_preferences (key, value_json, updated_at)
    VALUES ('rejection_insights', ?, ?)
    ON CONFLICT(key) DO UPDATE SET
      value_json = excluded.value_json,
      updated_at = excluded.updated_at;
  `);
  saveStmt.run(JSON.stringify(insightReport), new Date().toISOString());

  return insightReport;
}

export default {
  analyzeRejectionPatterns,
};
