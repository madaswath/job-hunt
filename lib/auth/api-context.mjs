// @ts-check
/**
 * Resolve auth + app user for each API request.
 */
import { authenticateRequest, isClerkConfigured } from './clerk.mjs';
import { resolveAppUser } from '../users/resolve-user.mjs';

/**
 * @typedef {object} ApiContext
 * @property {import('../users/resolve-user.mjs').AppUser} user
 * @property {import('./clerk.mjs').AuthContext} auth
 */

/** @type {Set<string>} */
const PUBLIC_PATHS = new Set([
  '/api/health',
  '/api/billing/webhooks/razorpay',
  '/api/billing/plans',
]);

/**
 * @param {string} pathname
 * @returns {boolean}
 */
export function isPublicPath(pathname) {
  return PUBLIC_PATHS.has(pathname || '');
}

/**
 * @param {import('node:http').IncomingMessage} req
 * @param {string} pathname
 * @returns {Promise<{ ok: true, ctx: ApiContext } | { ok: false, status: number, body: object }>}
 */
export async function requireApiContext(req, pathname) {
  if (isPublicPath(pathname)) {
    return {
      ok: true,
      ctx: {
        auth: { clerkUserId: 'public', email: null, sessionId: null },
        user: { id: 'public', clerkUserId: 'public', email: null, planId: 'free' },
      },
    };
  }

  const auth = await authenticateRequest(req);
  if (!auth) {
    if (process.env.ALLOW_UNAUTH_API === 'true') {
      const devAuth = {
        clerkUserId: process.env.DEV_CLERK_USER_ID || 'dev_local_user',
        email: 'dev@localhost',
        sessionId: null,
      };
      const user = await resolveAppUser(devAuth);
      if (!user) {
        return { ok: false, status: 503, body: { success: false, error: 'User resolution failed' } };
      }
      return { ok: true, ctx: { auth: devAuth, user } };
    }

    const message = isClerkConfigured()
      ? 'Missing or invalid Authorization bearer token'
      : 'Authentication not configured. Set CLERK_SECRET_KEY or ALLOW_UNAUTH_API=true for local dev.';
    return { ok: false, status: 401, body: { success: false, error: message } };
  }

  const user = await resolveAppUser(auth);
  if (!user) {
    return { ok: false, status: 503, body: { success: false, error: 'Could not resolve app user' } };
  }

  return { ok: true, ctx: { auth, user } };
}

export default { requireApiContext, isPublicPath };
