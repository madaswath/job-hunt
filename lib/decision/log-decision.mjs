// @ts-check
import { createHash } from 'node:crypto';
import { getSupabaseAdmin } from '../db/supabase-admin.mjs';

/**
 * @param {string} input
 * @returns {string}
 */
export function hashInput(input) {
  return createHash('sha256').update(input).digest('hex').slice(0, 32);
}

/**
 * @param {object} row
 */
export async function logDecisionEvent(row) {
  const supabase = getSupabaseAdmin();
  const payload = {
    user_id: row.userId && !String(row.userId).startsWith('local:') ? row.userId : null,
    job_id: row.jobId || null,
    agent: row.agent,
    decision_type: row.decisionType,
    provider: row.provider,
    decision: row.decision,
    confidence: row.confidence ?? null,
    input_hash: row.inputHash || null,
    metadata: row.metadata || {},
  };

  if (!supabase) {
    if (process.env.NODE_ENV !== 'production') {
      console.debug('[decision]', JSON.stringify(payload));
    }
    return;
  }

  const { error } = await supabase.from('decision_events').insert(payload);
  if (error) console.warn('logDecisionEvent:', error.message);
}

export default { logDecisionEvent, hashInput };
