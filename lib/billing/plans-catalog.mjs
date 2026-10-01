// @ts-check
/** INR list prices for Razorpay one-time checkout (subscriptions use plan IDs when configured). */

export const BILLING_CATALOG = {
  premium: {
    monthly: { amountPaise: 29900, label: 'Premium — Monthly' },
    quarterly: { amountPaise: 79900, label: 'Premium — Quarterly' },
    yearly: { amountPaise: 249900, label: 'Premium — Yearly' },
  },
  pro: {
    monthly: { amountPaise: 69900, label: 'Pro — Monthly' },
    quarterly: { amountPaise: 189900, label: 'Pro — Quarterly' },
    yearly: { amountPaise: 599900, label: 'Pro — Yearly' },
  },
};

/**
 * @param {'premium'|'pro'} planId
 * @param {'monthly'|'quarterly'|'yearly'} interval
 */
export function getPrice(planId, interval) {
  return BILLING_CATALOG[planId]?.[interval] || null;
}

export default { BILLING_CATALOG, getPrice };
