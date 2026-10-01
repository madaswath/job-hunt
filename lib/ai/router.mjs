// @ts-check
/**
 * lib/ai/router.mjs
 * Multi-Provider AI Inference Router with automatic fallback hierarchy:
 * PRIMARY: Groq -> FALLBACK 1: Gemini -> FALLBACK 2: OpenAI / OpenRouter -> LOCAL: Ollama.
 */

import { generateGroqCompletion } from './groq.mjs';

/**
 * Dispatches completion request with intelligent multi-provider fallback.
 *
 * @param {object} params
 * @param {Array<{ role: string, content: string }>} params.messages
 * @param {'classification' | 'job_analysis' | 'resume_tailoring' | 'outreach' | 'interview'} [params.workload='job_analysis']
 * @param {number} [params.temperature=0.2]
 * @param {number} [params.maxTokens=2048]
 * @param {boolean} [params.jsonMode=false]
 * @param {string} [params.preferredProvider]
 * @param {{ userId?: string, feature?: string, workflow?: string }} [params.usageContext]
 * @returns {Promise<{ content: string, provider: string, model: string, usage?: object }>}
 */
export async function completeWithFallback({
  messages,
  workload = 'job_analysis',
  temperature = 0.2,
  maxTokens = 2048,
  jsonMode = false,
  preferredProvider = 'groq',
  usageContext,
}) {
  const errors = [];

  // 1. Try Groq (Primary)
  if (preferredProvider === 'groq' || !preferredProvider) {
    if (process.env.GROQ_API_KEY) {
      try {
        const res = await generateGroqCompletion({
          messages,
          workload,
          temperature,
          maxTokens,
          jsonMode,
          usageContext,
        });
        return {
          ...res,
          provider: 'groq',
        };
      } catch (err) {
        errors.push({ provider: 'groq', error: err.message });
        console.warn('Groq provider error, falling back to next provider:', err.message);
      }
    }
  }

  // 2. Try Gemini (Fallback 1)
  if (process.env.GEMINI_API_KEY) {
    try {
      const { GoogleGenerativeAI } = await import('@google/generative-ai');
      const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
      const model = genAI.getGenerativeModel({
        model: workload === 'classification' ? 'gemini-1.5-flash' : 'gemini-1.5-pro',
      });

      const promptText = messages.map((m) => `${m.role}: ${m.content}`).join('\n\n');
      const result = await model.generateContent(promptText);
      return {
        content: result.response.text(),
        provider: 'gemini',
        model: 'gemini-1.5-pro',
      };
    } catch (err) {
      errors.push({ provider: 'gemini', error: err.message });
      console.warn('Gemini fallback error:', err.message);
    }
  }

  // 3. Try OpenAI / OpenRouter (Fallback 2)
  const openAiKey = process.env.OPENAI_API_KEY || process.env.OPENROUTER_API_KEY;
  if (openAiKey) {
    try {
      const baseUrl = process.env.OPENROUTER_API_KEY
        ? 'https://openrouter.ai/api/v1/chat/completions'
        : 'https://api.openai.com/v1/chat/completions';

      const res = await fetch(baseUrl, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${openAiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: process.env.OPENAI_MODEL || (process.env.OPENROUTER_API_KEY ? 'meta-llama/llama-3.3-70b-instruct' : 'gpt-4o-mini'),
          messages,
          temperature,
          max_tokens: maxTokens,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        return {
          content: data.choices?.[0]?.message?.content || '',
          provider: process.env.OPENROUTER_API_KEY ? 'openrouter' : 'openai',
          model: data.model || 'openai',
        };
      }
    } catch (err) {
      errors.push({ provider: 'openai', error: err.message });
    }
  }

  // 4. Try Local Ollama (Privacy / Offline)
  try {
    const ollamaHost = process.env.OLLAMA_HOST || 'http://127.0.0.1:11434';
    const res = await fetch(`${ollamaHost}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: process.env.OLLAMA_MODEL || 'llama3',
        messages,
        stream: false,
      }),
    });
    if (res.ok) {
      const data = await res.json();
      return {
        content: data.message?.content || '',
        provider: 'ollama',
        model: process.env.OLLAMA_MODEL || 'llama3',
      };
    }
  } catch {
    // Ollama offline
  }

  throw new Error(
    `All configured AI providers failed. Check GROQ_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY in your .env file.\nErrors: ${JSON.stringify(errors)}`
  );
}

export default {
  completeWithFallback,
};
