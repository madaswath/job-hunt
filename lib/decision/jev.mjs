// @ts-check
/**
 * Jev decision API — compatible with TypeSafe System One request shape.
 *
 * Default host: https://jevtypesafeai.com/api/v1/decide (Bearer JEV_API_KEY)
 * Official TypeSafe: set JEV_API_URL=https://api.typesafe.ai/v1/systemone + TYPESAFE_API_KEY
 */

const DEFAULT_URL = 'https://jevtypesafeai.com/api/v1/decide';

/**
 * @param {string} baseUrl
 * @param {string} selectedModel
 * @param {string|object|Array} state
 * @param {Record<string, object>} questions
 */
function buildRequestBody(baseUrl, selectedModel, state, questions) {
  /** @type {Record<string, unknown>} */
  const body = { state, questions };
  const isDecideHost = baseUrl.includes('/decide');
  if (!isDecideHost || process.env.JEV_MODEL) {
    body.model = selectedModel;
  }
  return body;
}

/**
 * @returns {boolean}
 */
export function isJevConfigured() {
  return Boolean(process.env.TYPESAFE_API_KEY || process.env.JEV_API_KEY);
}

/**
 * @returns {string | undefined}
 */
function getApiKey() {
  return process.env.TYPESAFE_API_KEY || process.env.JEV_API_KEY;
}

/**
 * @param {object} params
 * @param {string|object|Array} params.state
 * @param {Record<string, object>} params.questions
 * @param {string} [params.model]
 * @returns {Promise<{ answers: Record<string, object>, model: string, usage?: object, provider: 'JEV' }>}
 */
export async function evaluateSystemOne({ state, questions, model }) {
  const key = getApiKey();
  if (!key) {
    throw new Error('TYPESAFE_API_KEY (or JEV_API_KEY) is not configured');
  }

  const baseUrl = (process.env.JEV_API_URL || DEFAULT_URL).replace(/\/$/, '');
  const selectedModel = model || process.env.JEV_MODEL || 'jev-latest';

  const started = Date.now();
  const res = await fetch(baseUrl, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(buildRequestBody(baseUrl, selectedModel, state, questions)),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Jev API error (${res.status}): ${errText}`);
  }

  const data = await res.json();
  return {
    answers: data.answers || {},
    model: data.model || selectedModel,
    usage: data.usage,
    provider: 'JEV',
    latencyMs: Date.now() - started,
  };
}

/**
 * @param {object} answer
 * @returns {string | null}
 */
export function choiceAnswer(answer) {
  if (!answer || answer.type !== 'choice') return null;
  return typeof answer.choice === 'string' ? answer.choice : null;
}

/**
 * @param {object} answer
 * @returns {number | null}
 */
export function noulAnswer(answer) {
  if (!answer || answer.type !== 'noul') return null;
  return typeof answer.noul === 'number' ? answer.noul : null;
}

/**
 * @param {object} answer
 * @returns {number | null}
 */
export function confidenceOf(answer) {
  if (!answer) return null;
  if (typeof answer.confidence === 'number') return answer.confidence;
  if (answer.type === 'noul' && typeof answer.noul === 'number') return answer.noul;
  return null;
}

export default {
  isJevConfigured,
  evaluateSystemOne,
  choiceAnswer,
  noulAnswer,
  confidenceOf,
};
