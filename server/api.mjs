// @ts-check
/**
 * server/api.mjs
 * Lightweight, high-performance REST API Server for the Career-Ops Web Dashboard & Product Layer.
 */

import '../lib/env/load-env.mjs';

import { createServer } from 'node:http';
import { parse as parseUrl } from 'node:url';
import {
  getDashboardSummary,
  listJobs,
  getJobById,
  updateJobState,
  listApprovalTasks,
  saveApprovalTask,
  upsertJob,
} from '../lib/db/sqlite.mjs';
import { syncAll, loadUserProfile } from '../lib/db/sync-engine.mjs';
import { processJobThroughWorkflow, processBatchWorkflow } from '../lib/workflow/orchestrator.mjs';
import { listAllAgents } from '../lib/agents/registry.mjs';
import { listAllSources } from '../lib/sources/registry.mjs';
import { detectCareerSiteAts } from '../lib/sources/detector.mjs';
import { discoverGroqModels } from '../lib/ai/groq.mjs';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { requireApiContext } from '../lib/auth/api-context.mjs';
import { requireEntitlement, recordEntitlementUse } from '../lib/entitlements/guard.mjs';
import { getUsageSummary } from '../lib/entitlements/service.mjs';
import { BILLING_CATALOG } from '../lib/billing/plans-catalog.mjs';
import {
  createCheckoutOrder,
  verifyWebhookSignature,
  handleRazorpayWebhookEvent,
  isRazorpayConfigured,
} from '../lib/billing/razorpay.mjs';
import { isSupabaseConfigured } from '../lib/db/supabase-admin.mjs';
import { isClerkConfigured } from '../lib/auth/clerk.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3800;

/**
 * Parses JSON body from incoming request.
 * @param {import('node:http').IncomingMessage} req
 * @returns {Promise<any>}
 */
/**
 * @param {import('node:http').IncomingMessage} req
 * @returns {Promise<string>}
 */
function readRawBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => {
      body += chunk;
      if (body.length > 5 * 1024 * 1024) req.destroy(new Error('Body too large'));
    });
    req.on('end', () => resolve(body));
    req.on('error', reject);
  });
}

function readJsonBody(req) {
  return readRawBody(req).then((body) => {
    try {
      return body ? JSON.parse(body) : {};
    } catch {
      return {};
    }
  });
}

/**
 * Sends a JSON response with CORS headers.
 * @param {import('node:http').ServerResponse} res
 * @param {number} statusCode
 * @param {any} data
 */
function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  });
  res.end(JSON.stringify(data));
}

/**
 * Main API Request Handler.
 * @param {import('node:http').IncomingMessage} req
 * @param {import('node:http').ServerResponse} res
 */
export async function handleApiRequest(req, res) {
  const { pathname, query } = parseUrl(req.url || '/', true);

  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    });
    res.end();
    return;
  }

  try {
    // 0. Health (no auth)
    if (pathname === '/api/health' && req.method === 'GET') {
      sendJson(res, 200, {
        success: true,
        service: 'job-hunt-api',
        entitlements: process.env.ENTITLEMENTS_MODE || 'soft',
        clerk: isClerkConfigured(),
        supabase: isSupabaseConfigured(),
        razorpay: isRazorpayConfigured(),
        jev: Boolean(process.env.TYPESAFE_API_KEY || process.env.JEV_API_KEY),
        razorpayMode: process.env.RAZORPAY_MODE || null,
      });
      return;
    }

    // Razorpay webhook — raw body + signature (never trust client checkout alone)
    if (pathname === '/api/billing/webhooks/razorpay' && req.method === 'POST') {
      const raw = await readRawBody(req);
      const signature = req.headers['x-razorpay-signature'];
      if (!verifyWebhookSignature(raw, typeof signature === 'string' ? signature : undefined)) {
        sendJson(res, 400, { success: false, error: 'Invalid webhook signature' });
        return;
      }
      let event = {};
      try {
        event = raw ? JSON.parse(raw) : {};
      } catch {
        sendJson(res, 400, { success: false, error: 'Invalid JSON' });
        return;
      }
      const result = await handleRazorpayWebhookEvent(event);
      sendJson(res, 200, { success: true, ...result });
      return;
    }

    if (pathname === '/api/billing/plans' && req.method === 'GET') {
      sendJson(res, 200, { success: true, currency: 'INR', catalog: BILLING_CATALOG });
      return;
    }

    const authResult = await requireApiContext(req, pathname || '');
    if (!authResult.ok) {
      sendJson(res, authResult.status, authResult.body);
      return;
    }
    const { user } = authResult.ctx;

    // Me / entitlements
    if (pathname === '/api/me' && req.method === 'GET') {
      sendJson(res, 200, {
        success: true,
        user: {
          id: user.id,
          planId: user.planId,
          email: user.email,
        },
      });
      return;
    }

    if (pathname === '/api/me/entitlements' && req.method === 'GET') {
      const usage = await getUsageSummary(user.id, user.planId);
      sendJson(res, 200, { success: true, planId: user.planId, usage });
      return;
    }

    if (pathname === '/api/billing/checkout' && req.method === 'POST') {
      const body = await readJsonBody(req);
      const planId = body.planId === 'pro' ? 'pro' : 'premium';
      const interval = ['monthly', 'quarterly', 'yearly'].includes(body.interval) ? body.interval : 'monthly';
      try {
        const checkout = await createCheckoutOrder({
          userId: user.id,
          planId,
          interval,
          clerkUserId: user.clerkUserId,
        });
        sendJson(res, 200, { success: true, checkout });
      } catch (err) {
        sendJson(res, 503, { success: false, error: err.message });
      }
      return;
    }

    // 1. Dashboard Summary
    if (pathname === '/api/summary' && req.method === 'GET') {
      const summary = getDashboardSummary();
      sendJson(res, 200, { success: true, ...summary });
      return;
    }

    // 2. Agents Suite Registry
    if (pathname === '/api/agents' && req.method === 'GET') {
      const agents = listAllAgents();
      sendJson(res, 200, { success: true, agents });
      return;
    }

    // 2.1 Sources Catalog
    if (pathname === '/api/sources' && req.method === 'GET') {
      const sources = listAllSources();
      sendJson(res, 200, { success: true, sources });
      return;
    }

    // 2.2 Detect Career Site ATS
    if (pathname === '/api/sources/detect' && req.method === 'POST') {
      const body = await readJsonBody(req);
      const detection = await detectCareerSiteAts(body.url);
      sendJson(res, 200, detection);
      return;
    }

    // 2.3 Plugins Manifest
    if (pathname === '/api/plugins' && req.method === 'GET') {
      const regPath = join(__dirname, '../plugins/registry.json');
      const manifest = existsSync(regPath) ? JSON.parse(readFileSync(regPath, 'utf8')) : { plugins: [] };
      sendJson(res, 200, { success: true, ...manifest });
      return;
    }

    // 2.4 Groq / AI Model Discovery
    if (pathname === '/api/ai/models' && req.method === 'GET') {
      const models = await discoverGroqModels();
      sendJson(res, 200, { success: true, primary: 'groq', models });
      return;
    }

    // 3. Profile Endpoint
    if (pathname === '/api/profile' && req.method === 'GET') {
      const profile = loadUserProfile();
      sendJson(res, 200, { success: true, profile });
      return;
    }

    // 3. List & Filter Jobs
    if (pathname === '/api/jobs' && req.method === 'GET') {
      const state = typeof query.state === 'string' ? query.state : undefined;
      const minScore = query.minScore ? parseInt(/** @type {string} */ (query.minScore), 10) : undefined;
      const isRemote = query.remote === 'true';
      const search = typeof query.search === 'string' ? query.search : undefined;
      const limit = query.limit ? parseInt(/** @type {string} */ (query.limit), 10) : 50;
      const offset = query.offset ? parseInt(/** @type {string} */ (query.offset), 10) : 0;

      const result = listJobs({ state, minScore, isRemote, search, limit, offset });
      sendJson(res, 200, { success: true, ...result });
      return;
    }

    // 4. Get Job by ID
    const jobMatch = pathname?.match(/^\/api\/jobs\/([a-zA-Z0-9_-]+)$/);
    if (jobMatch && req.method === 'GET') {
      const jobId = jobMatch[1];
      const job = getJobById(jobId);
      if (!job) {
        sendJson(res, 404, { success: false, error: 'Job not found' });
        return;
      }
      sendJson(res, 200, { success: true, job });
      return;
    }

    // 5. Job Action (Approve / Save / Reject / Apply)
    const actionMatch = pathname?.match(/^\/api\/jobs\/([a-zA-Z0-9_-]+)\/action$/);
    if (actionMatch && req.method === 'POST') {
      const jobId = actionMatch[1];
      const body = await readJsonBody(req);
      const action = (body.action || '').toUpperCase();
      const reason = body.reason || '';
      const note = body.note || '';

      let targetState = 'REVIEW';
      if (action === 'APPROVE') targetState = 'APPROVED';
      else if (action === 'REJECT') targetState = 'REJECTED';
      else if (action === 'APPLY') targetState = 'APPLIED';
      else if (action === 'SAVE') targetState = 'QUALIFIED';

      const updated = updateJobState(jobId, targetState, reason, note);
      sendJson(res, 200, { success: updated, state: targetState });
      return;
    }

    // 6. Approval Queue
    if (pathname === '/api/approval-queue' && req.method === 'GET') {
      const status = typeof query.status === 'string' ? query.status : 'PENDING';
      const tasks = listApprovalTasks(status);
      sendJson(res, 200, { success: true, tasks });
      return;
    }

    // 7. Decide Approval Task
    const taskMatch = pathname?.match(/^\/api\/approval-queue\/([a-zA-Z0-9_-]+)\/decide$/);
    if (taskMatch && req.method === 'POST') {
      const taskId = taskMatch[1];
      const body = await readJsonBody(req);
      const decision = (body.decision || 'APPROVED').toUpperCase();
      const reason = body.reason || '';

      saveApprovalTask({
        id: taskId,
        status: decision,
        reviewedAt: new Date().toISOString(),
        decisionReason: reason,
      });

      sendJson(res, 200, { success: true, taskId, status: decision });
      return;
    }

    // 8. Trigger File Sync
    if (pathname === '/api/jobs/sync' && req.method === 'POST') {
      const syncResult = syncAll();
      sendJson(res, 200, { success: true, ...syncResult });
      return;
    }

    // 9. Ingest / Import Single Job or Batch
    if (pathname === '/api/jobs/import' && req.method === 'POST') {
      const body = await readJsonBody(req);
      const itemCount = Array.isArray(body.items) ? body.items.length : 1;

      for (let i = 0; i < itemCount; i++) {
        const gate = await requireEntitlement({ user, featureKey: 'job_evaluation' });
        if (!gate.ok) {
          sendJson(res, gate.status, gate.body);
          return;
        }
      }

      if (Array.isArray(body.items)) {
        const batchResult = await processBatchWorkflow(body.items, {
          userId: user.id,
          planId: user.planId,
        });
        for (let i = 0; i < body.items.length; i++) {
          await recordEntitlementUse({ user, featureKey: 'job_evaluation', metadata: { batch: true } });
        }
        sendJson(res, 200, { success: true, ...batchResult, planId: user.planId });
      } else if (body.url || body.item) {
        const singleResult = await processJobThroughWorkflow(body.item || body.url, {
          userId: user.id,
          planId: user.planId,
        });
        await recordEntitlementUse({ user, featureKey: 'job_evaluation' });
        sendJson(res, 200, { success: true, ...singleResult, planId: user.planId });
      } else {
        sendJson(res, 400, { success: false, error: 'Expected { url } or { items: [...] }' });
      }
      return;
    }

    // 10. Resume generation (entitlement-gated stub — wires Saraswati path)
    if (pathname === '/api/resume/generate' && req.method === 'POST') {
      const gate = await requireEntitlement({ user, featureKey: 'resume_generation' });
      if (!gate.ok) {
        sendJson(res, gate.status, gate.body);
        return;
      }
      const body = await readJsonBody(req);
      await recordEntitlementUse({ user, featureKey: 'resume_generation', metadata: { jobId: body.jobId } });
      sendJson(res, 200, {
        success: true,
        message: 'Resume generation queued. Connect cv.md / profile for full Saraswati pipeline.',
        planId: user.planId,
      });
      return;
    }

    // 11. Job scan trigger (daily limit)
    if (pathname === '/api/jobs/scan' && req.method === 'POST') {
      const gate = await requireEntitlement({ user, featureKey: 'job_scan' });
      if (!gate.ok) {
        sendJson(res, gate.status, gate.body);
        return;
      }
      await recordEntitlementUse({ user, featureKey: 'job_scan' });
      sendJson(res, 200, {
        success: true,
        message: 'Scan authorized. Run worker scan.mjs or scheduled Vishwakarma job.',
        planId: user.planId,
      });
      return;
    }

    // Fallback 404
    sendJson(res, 404, { success: false, error: 'Endpoint not found' });
  } catch (err) {
    console.error('API Error:', err);
    sendJson(res, 500, { success: false, error: err.message });
  }
}

/**
 * Starts the REST API server.
 * @param {number} [port]
 * @returns {import('node:http').Server}
 */
export function startServer(port = PORT) {
  const server = createServer(handleApiRequest);
  server.listen(port, () => {
    console.log(`🚀 Career-Ops API Server running at http://localhost:${port}`);
  });
  return server;
}

// Auto-run when executed directly
if (process.argv[1]?.endsWith('server/api.mjs') || process.argv[1]?.endsWith('api.mjs')) {
  // Sync files on start
  try {
    syncAll();
  } catch (e) {
    console.warn('Initial sync warning:', e);
  }
  startServer();
}

export default { startServer, handleApiRequest };
