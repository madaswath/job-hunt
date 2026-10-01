#!/usr/bin/env node
/**
 * Reports which integration env vars are set and live-probes each service.
 * Never prints secret values.
 */
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { config } from 'dotenv';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
config({ path: join(root, '.env'), quiet: true });
const webLocal = join(root, 'web', '.env.local');
if (existsSync(webLocal)) {
  config({ path: webLocal, quiet: true, override: true });
}

/** @param {string} name */
function status(name) {
  const v = process.env[name];
  if (!v || !String(v).trim()) return 'missing';
  const t = String(v).trim();
  if (t.length < 8) return 'set (short — double-check)';
  return 'set';
}

/** @param {string} url */
function supabaseProjectRef(url) {
  try {
    const h = new URL(url).hostname;
    const m = h.match(/^([a-z0-9]+)\.supabase\.co$/i);
    return m ? m[1] : null;
  } catch {
    return null;
  }
}

const groups = {
  'API server (root .env)': [
    'CLERK_SECRET_KEY',
    'SUPABASE_URL',
    'SUPABASE_SERVICE_ROLE_KEY',
    'SUPABASE_DATABASE_URL',
    'GROQ_API_KEY',
    'TYPESAFE_API_KEY',
    'JEV_API_KEY',
    'RAZORPAY_KEY_ID',
    'RAZORPAY_KEY_SECRET',
    'RAZORPAY_WEBHOOK_SECRET',
  ],
  'Next.js (web/.env.local or root)': [
    'NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY',
    'CLERK_SECRET_KEY',
    'NEXT_PUBLIC_API_URL',
    'NEXT_PUBLIC_CLERK_SIGN_IN_URL',
  ],
  'Supabase (browser — optional)': ['SUPABASE_ANON_KEY'],
};

console.log('=== Job-hunt connection audit ===\n');
console.log(
  JSON.stringify(
    {
      rootEnv: existsSync(join(root, '.env')),
      webEnvLocal: existsSync(webLocal),
      supabaseProjectRef: process.env.SUPABASE_URL ? supabaseProjectRef(process.env.SUPABASE_URL) : null,
    },
    null,
    2
  )
);
console.log('\n--- Env vars (missing | set) ---\n');

for (const [title, vars] of Object.entries(groups)) {
  console.log(`## ${title}`);
  for (const name of vars) {
    console.log(`  ${name}: ${status(name)}`);
  }
  console.log('');
}

/** @param {string} pk */
function clerkKeyEnv(pk) {
  if (!pk || pk.length < 10) return 'invalid';
  if (pk.startsWith('pk_test_') || pk.startsWith('pk_live_')) return 'format ok';
  return 'unexpected format';
}

async function probe() {
  /** @type {Record<string, string>} */
  const out = {};

  // Clerk publishable ↔ secret sanity (no API call)
  const pub = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || process.env.CLERK_PUBLISHABLE_KEY;
  const sec = process.env.CLERK_SECRET_KEY;
  if (pub && sec) {
    const pubEnv = pub.includes('_test_') ? 'test' : pub.includes('_live_') ? 'live' : '?';
    const secEnv = sec.includes('_test_') ? 'test' : sec.includes('_live_') ? 'live' : '?';
    out.clerk_keys =
      pubEnv === secEnv ? `paired (${pubEnv})` : `MISMATCH publishable=${pubEnv} secret=${secEnv}`;
    out.clerk_publishable = clerkKeyEnv(pub);
  } else {
    out.clerk_keys = 'missing publishable or secret';
  }

  // Clerk Backend API
  if (sec) {
    try {
      const res = await fetch('https://api.clerk.com/v1/users?limit=1', {
        headers: { Authorization: `Bearer ${sec}` },
      });
      if (res.ok) out.clerk_api = 'ok';
      else if (res.status === 401) out.clerk_api = 'http 401 — invalid CLERK_SECRET_KEY';
      else out.clerk_api = `http ${res.status}`;
    } catch (e) {
      out.clerk_api = `error: ${e.message}`;
    }
  } else out.clerk_api = 'skipped';

  // Supabase service role
  if (process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY) {
    try {
      const { createClient } = await import('@supabase/supabase-js');
      const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, {
        auth: { persistSession: false, autoRefreshToken: false },
      });
      const { data, error } = await sb.from('plans').select('id').limit(3);
      if (error) {
        if (error.message.includes('Could not find the table')) {
          out.supabase_service_role =
            'auth ok — schema missing (run npm run db:migrate or SQL migrations)';
        } else if (error.message.includes('Invalid API key') || error.code === 'PGRST301') {
          out.supabase_service_role = 'invalid SERVICE_ROLE_KEY or wrong SUPABASE_URL';
        } else {
          out.supabase_service_role = `error: ${error.message}`;
        }
      } else {
        out.supabase_service_role = `ok (${data?.length ?? 0} plan rows)`;
      }
    } catch (e) {
      out.supabase_service_role = `error: ${e.message}`;
    }
  } else {
    out.supabase_service_role = 'skipped (URL or SERVICE_ROLE missing)';
  }

  // Supabase anon
  if (process.env.SUPABASE_URL && process.env.SUPABASE_ANON_KEY) {
    try {
      const { createClient } = await import('@supabase/supabase-js');
      const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_ANON_KEY, {
        auth: { persistSession: false },
      });
      const { error } = await sb.from('plans').select('id').limit(1);
      if (error) {
        if (error.message.includes('Could not find the table')) {
          out.supabase_anon = 'auth ok — plans table missing (migrations)';
        } else {
          out.supabase_anon = `error: ${error.message}`;
        }
      } else out.supabase_anon = 'ok';
    } catch (e) {
      out.supabase_anon = `error: ${e.message}`;
    }
  } else out.supabase_anon = 'skipped';

  // Direct Postgres URL (host reachability only — no password in logs)
  const dbUrl = process.env.SUPABASE_DATABASE_URL || process.env.DATABASE_URL;
  if (dbUrl?.startsWith('postgresql://')) {
    try {
      const u = new URL(dbUrl.replace(/^postgresql:/, 'http:'));
      out.supabase_database_url = `configured (host ${u.hostname}) — run npm run db:migrate to verify login`;
    } catch {
      out.supabase_database_url = 'malformed URL';
    }
  } else {
    out.supabase_database_url = 'not set (optional; use SQL Editor or db:migrate)';
  }

  // Groq
  if (process.env.GROQ_API_KEY) {
    try {
      const res = await fetch('https://api.groq.com/openai/v1/models', {
        headers: { Authorization: `Bearer ${process.env.GROQ_API_KEY}` },
      });
      if (res.ok) out.groq = 'ok';
      else if (res.status === 401) out.groq = 'http 401 — invalid GROQ_API_KEY';
      else out.groq = `http ${res.status}`;
    } catch (e) {
      out.groq = `error: ${e.message}`;
    }
  } else out.groq = 'skipped';

  // Jev (jevtypesafeai.com/decide or api.typesafe.ai/systemone)
  const jevKey = process.env.TYPESAFE_API_KEY || process.env.JEV_API_KEY;
  if (jevKey) {
    try {
      const url = (process.env.JEV_API_URL || 'https://jevtypesafeai.com/api/v1/decide').replace(/\/$/, '');
      /** @type {Record<string, unknown>} */
      const body = {
        state: 'Customer: I was charged twice and nobody has replied for 3 days.',
        questions: {
          route: {
            type: 'choice',
            instructions: 'Where should this ticket go?',
            criteria: {
              billing: 'payments, refunds, invoices',
              bug: 'the product is broken',
              account: 'login or access',
            },
          },
        },
      };
      if (process.env.JEV_MODEL) body.model = process.env.JEV_MODEL;
      else if (!url.includes('/decide')) body.model = 'jev-latest';

      const res = await fetch(url, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${jevKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });
      if (res.ok) out.jev = `ok (${new URL(url).hostname})`;
      else if (res.status === 401) out.jev = 'http 401 — invalid JEV_API_KEY';
      else out.jev = `http ${res.status}`;
    } catch (e) {
      out.jev = `error: ${e.message}`;
    }
  } else out.jev = 'skipped';

  // Razorpay
  const rzId = process.env.RAZORPAY_KEY_ID;
  const rzSec = process.env.RAZORPAY_KEY_SECRET;
  const rzMode = (process.env.RAZORPAY_MODE || '').toLowerCase();
  const keyMode = rzId?.startsWith('rzp_live_') ? 'live' : rzId?.startsWith('rzp_test_') ? 'test' : '?';
  if (rzMode && keyMode !== '?' && rzMode !== keyMode) {
    out.razorpay_mode = `MISMATCH want ${rzMode}, keys are ${keyMode}`;
  } else if (keyMode !== '?') {
    out.razorpay_mode = keyMode;
  }
  if (rzId && rzSec) {
    try {
      const token = Buffer.from(`${rzId}:${rzSec}`).toString('base64');
      const res = await fetch('https://api.razorpay.com/v1/payments?count=1', {
        headers: { Authorization: `Basic ${token}` },
      });
      if (res.ok) out.razorpay = 'ok';
      else if (res.status === 401) out.razorpay = 'http 401 — invalid KEY_ID or KEY_SECRET';
      else out.razorpay = `http ${res.status}`;
    } catch (e) {
      out.razorpay = `error: ${e.message}`;
    }
  } else out.razorpay = 'skipped';

  // Local API health (optional)
  const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3800';
  try {
    const res = await fetch(`${apiUrl.replace(/\/$/, '')}/api/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      const j = await res.json();
      out.local_api = `ok @ ${apiUrl} (clerk=${j.clerk} supabase=${j.supabase} groq=${j.groq} jev=${j.jev})`;
    } else out.local_api = `http ${res.status} — is "npm run api" running?`;
  } catch {
    out.local_api = `not reachable at ${apiUrl} — start with npm run api`;
  }

  console.log('--- Live probes (no secrets) ---\n');
  for (const [k, v] of Object.entries(out)) {
    const icon =
      v === 'ok' || v.startsWith('ok ') || v.startsWith('paired') || v.includes('auth ok')
        ? '✓'
        : v.startsWith('skipped') || v.includes('not set') || v.includes('optional')
          ? '○'
          : '✗';
    console.log(`${icon} ${k}: ${v}`);
  }

  const failed = Object.entries(out).filter(
    ([, v]) =>
      v.includes('401') ||
      v.includes('invalid') ||
      v.includes('MISMATCH') ||
      v.includes('malformed') ||
      v.includes('not reachable') ||
      (v.startsWith('http ') && !v.includes('ok'))
  );
  console.log(failed.length ? `\n${failed.length} issue(s) need attention above.` : '\nAll probed services connected.');
}

probe();
