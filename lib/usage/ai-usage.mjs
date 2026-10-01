// @ts-check
/**
 * Append-only Groq / LLM usage telemetry for unit economics.
 */
import { getSupabaseAdmin } from '../db/supabase-admin.mjs';

/** Rough USD per 1M tokens (tune from Groq dashboard) */
const COST_PER_M_INPUT = 0.05;
const COST_PER_M_OUTPUT = 0.08;

/**
 * @param {object} params
 * @param {string | null | undefined} params.userId
 * @param {string} params.feature
 * @param {string} [params.workflow]
 * @param {string} [params.provider='groq']
 * @param {string} [params.model]
 * @param {number} [params.inputTokens=0]
 * @param {number} [params.outputTokens=0]
 * @param {number} [params.latencyMs]
 * @param {object} [params.metadata]
 */
export async function logAiUsage({
  userId,
  feature,
  workflow,
  provider = 'groq',
  model,
  inputTokens = 0,
  outputTokens = 0,
  latencyMs,
  metadata = {},
}) {
  const estimated =
    (inputTokens / 1_000_000) * COST_PER_M_INPUT + (outputTokens / 1_000_000) * COST_PER_M_OUTPUT;

  const row = {
    user_id: userId && !userId.startsWith('local:') ? userId : null,
    feature,
    workflow: workflow || null,
    provider,
    model: model || null,
    input_tokens: inputTokens || null,
    output_tokens: outputTokens || null,
    latency_ms: latencyMs ?? null,
    estimated_cost_usd: estimated > 0 ? estimated : null,
    metadata,
  };

  const supabase = getSupabaseAdmin();
  if (!supabase) {
    if (process.env.NODE_ENV !== 'production') {
      console.debug('[ai-usage]', JSON.stringify(row));
    }
    return;
  }

  const { error } = await supabase.from('ai_usage_events').insert(row);
  if (error) console.warn('logAiUsage:', error.message);
}

export default { logAiUsage };
