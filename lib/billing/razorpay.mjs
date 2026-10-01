// @ts-check
/**
 * Razorpay orders + webhook verification. Premium activates only after verified webhook.
 */
import { createHmac, timingSafeEqual } from 'node:crypto';
import { getSupabaseAdmin } from '../db/supabase-admin.mjs';
import { getPrice } from './plans-catalog.mjs';

const RAZORPAY_API = 'https://api.razorpay.com/v1';

/**
 * @returns {boolean}
 */
export function isRazorpayConfigured() {
  return Boolean(process.env.RAZORPAY_KEY_ID && process.env.RAZORPAY_KEY_SECRET);
}

/**
 * @returns {'live'|'test'|null}
 */
export function razorpayKeyMode() {
  const id = process.env.RAZORPAY_KEY_ID || '';
  if (id.startsWith('rzp_live_')) return 'live';
  if (id.startsWith('rzp_test_')) return 'test';
  return null;
}

/**
 * Warn when RAZORPAY_MODE=live but keys are test (or vice versa).
 */
export function assertRazorpayModeConsistency() {
  const want = (process.env.RAZORPAY_MODE || '').toLowerCase();
  const have = razorpayKeyMode();
  if (!want || !have || want === have) return;
  console.warn(
    `Razorpay: RAZORPAY_MODE=${want} but RAZORPAY_KEY_ID looks like ${have} mode — payments will fail until they match.`
  );
}

/**
 * @param {string} body
 * @returns {string}
 */
function basicAuthHeader(body) {
  const key = process.env.RAZORPAY_KEY_ID;
  const secret = process.env.RAZORPAY_KEY_SECRET;
  const token = Buffer.from(`${key}:${secret}`).toString('base64');
  return `Basic ${token}`;
}

/**
 * @param {{ userId: string, planId: 'premium'|'pro', interval: 'monthly'|'quarterly'|'yearly', clerkUserId: string }} params
 */
export async function createCheckoutOrder({ userId, planId, interval, clerkUserId }) {
  if (!isRazorpayConfigured()) {
    throw new Error('Razorpay is not configured');
  }
  assertRazorpayModeConsistency();

  const price = getPrice(planId, interval);
  if (!price) throw new Error('Invalid plan or interval');

  const receipt = `jh_${planId}_${interval}_${Date.now()}`.slice(0, 40);

  const res = await fetch(`${RAZORPAY_API}/orders`, {
    method: 'POST',
    headers: {
      Authorization: basicAuthHeader(''),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      amount: price.amountPaise,
      currency: 'INR',
      receipt,
      notes: {
        app_user_id: userId,
        plan_id: planId,
        interval,
        clerk_user_id: clerkUserId,
      },
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Razorpay order failed: ${text}`);
  }

  const order = await res.json();

  const supabase = getSupabaseAdmin();
  if (supabase) {
    await supabase.from('payments').insert({
      user_id: userId,
      plan_id: planId,
      razorpay_order_id: order.id,
      amount_paise: price.amountPaise,
      currency: 'INR',
      status: 'created',
      metadata: { interval, receipt },
    });
  }

  return {
    orderId: order.id,
    amount: price.amountPaise,
    currency: 'INR',
    keyId: process.env.RAZORPAY_KEY_ID,
    description: price.label,
    planId,
    interval,
  };
}

/**
 * @param {string} rawBody
 * @param {string | undefined} signature
 * @returns {boolean}
 */
export function verifyWebhookSignature(rawBody, signature) {
  const secret = process.env.RAZORPAY_WEBHOOK_SECRET;
  if (!secret || !signature) return false;
  const expected = createHmac('sha256', secret).update(rawBody).digest('hex');
  try {
    return timingSafeEqual(Buffer.from(expected), Buffer.from(signature));
  } catch {
    return false;
  }
}

/**
 * @param {object} event
 */
export async function handleRazorpayWebhookEvent(event) {
  const supabase = getSupabaseAdmin();
  if (!supabase) {
    console.warn('Webhook received but Supabase not configured');
    return { ok: false, reason: 'no_database' };
  }

  const eventId = event?.id || event?.event_id;
  const eventType = event?.event;

  if (eventId) {
    const { error: dupErr } = await supabase.from('subscription_events').insert({
      provider: 'razorpay',
      provider_event_id: eventId,
      event_type: eventType || 'unknown',
      payload: event,
    });
    if (dupErr?.code === '23505') {
      return { ok: true, duplicate: true };
    }
  }

  const paymentEntity = event?.payload?.payment?.entity;
  const orderEntity = event?.payload?.order?.entity;

  if (eventType === 'payment.captured' && paymentEntity) {
    const orderId = paymentEntity.order_id;
    const { data: paymentRow } = await supabase
      .from('payments')
      .select('*')
      .eq('razorpay_order_id', orderId)
      .maybeSingle();

    if (paymentRow) {
      await supabase
        .from('payments')
        .update({
          status: 'captured',
          razorpay_payment_id: paymentEntity.id,
        })
        .eq('id', paymentRow.id);

      const planId = paymentRow.plan_id || paymentRow.metadata?.plan_id;
      const userId = paymentRow.user_id;
      const interval = paymentRow.metadata?.interval || 'monthly';

      if (userId && planId) {
        const periodEnd = computePeriodEnd(interval);
        const { data: existingSub } = await supabase
          .from('subscriptions')
          .select('id')
          .eq('user_id', userId)
          .order('updated_at', { ascending: false })
          .limit(1)
          .maybeSingle();

        const subPayload = {
          user_id: userId,
          plan_id: planId,
          status: 'active',
          current_period_start: new Date().toISOString(),
          current_period_end: periodEnd,
          updated_at: new Date().toISOString(),
        };

        if (existingSub?.id) {
          await supabase.from('subscriptions').update(subPayload).eq('id', existingSub.id);
        } else {
          await supabase.from('subscriptions').insert(subPayload);
        }

        await supabase.from('audit_events').insert({
          user_id: userId,
          action: 'subscription.activated',
          resource_type: 'plan',
          resource_id: planId,
          metadata: { order_id: orderId, payment_id: paymentEntity.id },
        });
      }
    }
  }

  if (eventType === 'order.paid' && orderEntity) {
    await supabase
      .from('payments')
      .update({ status: 'paid' })
      .eq('razorpay_order_id', orderEntity.id);
  }

  return { ok: true };
}

/**
 * @param {string} interval
 * @returns {string}
 */
function computePeriodEnd(interval) {
  const d = new Date();
  if (interval === 'yearly') d.setFullYear(d.getFullYear() + 1);
  else if (interval === 'quarterly') d.setMonth(d.getMonth() + 3);
  else d.setMonth(d.getMonth() + 1);
  return d.toISOString();
}

export default {
  isRazorpayConfigured,
  createCheckoutOrder,
  verifyWebhookSignature,
  handleRazorpayWebhookEvent,
};
