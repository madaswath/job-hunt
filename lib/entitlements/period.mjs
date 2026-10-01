// @ts-check
/**
 * Billing period keys for usage counters.
 */

/**
 * @param {'month' | 'day' | 'lifetime'} period
 * @param {Date} [now]
 * @returns {string}
 */
export function periodKeyFor(period, now = new Date()) {
  if (period === 'lifetime') return 'lifetime';
  if (period === 'day') {
    return now.toISOString().slice(0, 10);
  }
  return now.toISOString().slice(0, 7);
}

export default { periodKeyFor };
