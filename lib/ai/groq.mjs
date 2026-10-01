// @ts-check
/**
 * lib/ai/groq.mjs
 * Primary GroqCloud AI Inference Provider with dynamic model discovery and workload optimization.
 */
import { logAiUsage } from '../usage/ai-usage.mjs';

const GROQ_API_URL = 'https://api.groq.com/openai/v1';

// Default model tiers for different workloads (configurable via environment variables)
export const GROQ_MODELS = {
  // Fast / lightweight for classification, extraction, normalization
  FAST: process.env.GROQ_FAST_MODEL || 'llama-3.1-8b-instant',
  // Deep reasoning / high quality for Brihaspati (Analysis), Saraswati (CV), Krishna (Outreach)
  REASONING: process.env.GROQ_REASONING_MODEL || 'llama-3.3-70b-versatile',
  // Long context / complex synthesis
  LONG_CONTEXT: process.env.GROQ_LONG_MODEL || 'mixtral-8x7b-32768',
};

/**
 * Discovers available models from the Groq API.
 * @param {string} [apiKey]
 * @returns {Promise<string[]>}
 */
export async function discoverGroqModels(apiKey) {
  const key = apiKey || process.env.GROQ_API_KEY;
  if (!key) return [GROQ_MODELS.FAST, GROQ_MODELS.REASONING];

  try {
    const res = await fetch(`${GROQ_API_URL}/models`, {
      headers: {
        Authorization: `Bearer ${key}`,
        'Content-Type': 'application/json',
      },
    });
    if (!res.ok) return [GROQ_MODELS.FAST, GROQ_MODELS.REASONING];
    const data = await res.json();
    return (data.data || []).map((/** @type {{ id: string }} */ m) => m.id);
  } catch {
    return [GROQ_MODELS.FAST, GROQ_MODELS.REASONING];
  }
}

/**
 * Executes a chat completion against the Groq API.
 * @param {object} params
 * @param {Array<{ role: string, content: string }>} params.messages
 * @param {string} [params.workload='job_analysis'] - 'classification' | 'job_analysis' | 'resume_tailoring' | 'outreach'
 * @param {string} [params.model]
 * @param {number} [params.temperature=0.2]
 * @param {number} [params.maxTokens=2048]
 * @param {boolean} [params.jsonMode=false]
 * @param {string} [params.apiKey]
 * @param {{ userId?: string, feature?: string, workflow?: string }} [params.usageContext]
 * @returns {Promise<{ content: string, model: string, usage?: object }>}
 */
export async function generateGroqCompletion({
  messages,
  workload = 'job_analysis',
  model,
  temperature = 0.2,
  maxTokens = 2048,
  jsonMode = false,
  apiKey,
  usageContext,
}) {
  const key = apiKey || process.env.GROQ_API_KEY;
  if (!key) {
    throw new Error('GROQ_API_KEY is not configured in environment.');
  }

  // Pick optimal model for workload
  let selectedModel = model;
  if (!selectedModel) {
    if (workload === 'classification' || workload === 'normalization') {
      selectedModel = GROQ_MODELS.FAST;
    } else {
      selectedModel = GROQ_MODELS.REASONING;
    }
  }

  const payload = {
    model: selectedModel,
    messages,
    temperature,
    max_tokens: maxTokens,
    response_format: jsonMode ? { type: 'json_object' } : undefined,
  };

  const started = Date.now();
  const res = await fetch(`${GROQ_API_URL}/chat/completions`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Groq API Error (${res.status}): ${errText}`);
  }

  const data = await res.json();
  const choice = data.choices?.[0];
  const usage = data.usage || {};

  await logAiUsage({
    userId: usageContext?.userId,
    feature: usageContext?.feature || workload,
    workflow: usageContext?.workflow || workload,
    provider: 'groq',
    model: data.model || selectedModel,
    inputTokens: usage.prompt_tokens,
    outputTokens: usage.completion_tokens,
    latencyMs: Date.now() - started,
  });

  return {
    content: choice?.message?.content || '',
    model: data.model || selectedModel,
    usage,
  };
}

export default {
  discoverGroqModels,
  generateGroqCompletion,
  GROQ_MODELS,
};
