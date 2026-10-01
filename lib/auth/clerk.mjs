// @ts-check
/**
 * Clerk JWT verification for the Job-hunt API.
 */
import { createClerkClient, verifyToken } from '@clerk/backend';

/**
 * @typedef {object} AuthContext
 * @property {string} clerkUserId
 * @property {string | null} email
 * @property {string | null} sessionId
 */

/**
 * @returns {boolean}
 */
export function isClerkConfigured() {
  return Boolean(process.env.CLERK_SECRET_KEY);
}

/**
 * @param {import('node:http').IncomingMessage} req
 * @returns {Promise<AuthContext | null>}
 */
export async function authenticateRequest(req) {
  if (process.env.ALLOW_UNAUTH_API === 'true') {
    return {
      clerkUserId: process.env.DEV_CLERK_USER_ID || 'dev_local_user',
      email: 'dev@localhost',
      sessionId: null,
    };
  }

  if (!isClerkConfigured()) {
    return null;
  }

  const authHeader = req.headers.authorization || '';
  const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7).trim() : '';
  if (!token) return null;

  try {
    const payload = await verifyToken(token, {
      secretKey: process.env.CLERK_SECRET_KEY,
    });
    const clerkUserId = payload.sub;
    if (!clerkUserId) return null;

    let email = null;
    if (payload.email && typeof payload.email === 'string') {
      email = payload.email;
    } else {
      try {
        const clerk = createClerkClient({ secretKey: process.env.CLERK_SECRET_KEY });
        const user = await clerk.users.getUser(clerkUserId);
        email = user.emailAddresses?.[0]?.emailAddress || null;
      } catch {
        /* optional enrichment */
      }
    }

    return {
      clerkUserId,
      email,
      sessionId: typeof payload.sid === 'string' ? payload.sid : null,
    };
  } catch (err) {
    console.warn('Clerk auth failed:', err.message);
    return null;
  }
}

export default { authenticateRequest, isClerkConfigured };
