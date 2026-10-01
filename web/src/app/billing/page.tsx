"use client";

import { useAuth } from "@clerk/nextjs";

const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
import { useCallback, useEffect, useState } from "react";
import { CreditCard, Loader2 } from "lucide-react";
import {
  fetchBillingPlans,
  fetchEntitlements,
  startCheckout,
  type EntitlementsResponse,
} from "@/lib/job-hunt-api";

type Catalog = {
  premium: Record<string, { amountPaise: number; label: string }>;
  pro: Record<string, { amountPaise: number; label: string }>;
};

function inr(paise: number) {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
}

function BillingContent() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [entitlements, setEntitlements] = useState<EntitlementsResponse | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const plansRes = await fetchBillingPlans();
      if (plansRes.data?.catalog) setCatalog(plansRes.data.catalog);

      if (isSignedIn) {
        const tokenFn = () => getToken();
        const entRes = await fetchEntitlements(tokenFn);
        if (entRes.res.ok) setEntitlements(entRes.data as EntitlementsResponse);
        else setError(entRes.data?.error || "Could not load entitlements");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load billing");
    } finally {
      setLoading(false);
    }
  }, [getToken, isSignedIn]);

  useEffect(() => {
    if (isLoaded) load();
  }, [isLoaded, load]);

  async function onCheckout(planId: "premium" | "pro", interval: "monthly" | "quarterly" | "yearly") {
    setCheckoutLoading(`${planId}-${interval}`);
    setError(null);
    try {
      const { res, data } = await startCheckout(() => getToken(), planId, interval);
      if (!res.ok) {
        setError(data?.error || "Checkout failed");
        return;
      }
      const checkout = data.checkout;
      if (checkout?.orderId && checkout?.keyId && typeof window !== "undefined") {
        alert(
          `Razorpay order created (${checkout.orderId}). Open Razorpay Checkout with key ${checkout.keyId} — wire the client SDK next, or pay via test dashboard.`
        );
      }
    } finally {
      setCheckoutLoading(null);
    }
  }

  if (!isLoaded || loading) {
    return (
      <div className="flex items-center gap-2 p-8 text-muted">
        <Loader2 className="size-4 animate-spin" /> Loading billing…
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-6 md:p-10">
      <header>
        <div className="mb-2 flex items-center gap-2 text-landing">
          <CreditCard className="size-5" />
          <h1 className="text-2xl font-semibold tracking-tight">Billing & plan</h1>
        </div>
        <p className="text-sm text-muted">
          Premium activates only after Razorpay payment is verified on the server (webhook). You approve every application and message.
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>
      )}

      {entitlements && (
        <section className="rounded-xl border border-border bg-surface/40 p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-faint">Current plan</h2>
          <p className="text-lg capitalize text-landing">{entitlements.planId}</p>
          <ul className="mt-4 space-y-2 text-sm">
            {Object.entries(entitlements.usage).map(([key, row]) => (
              <li key={key} className="flex justify-between gap-4 border-b border-border/60 py-2 last:border-0">
                <span className="text-muted">{key.replace(/_/g, " ")}</span>
                <span className="tabular-nums text-landing">
                  {row.used}
                  {row.limit != null ? ` / ${row.limit}` : " · fair use"}
                  <span className="text-faint"> ({row.period})</span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {catalog && (
        <section className="grid gap-4 md:grid-cols-2">
          {(["premium", "pro"] as const).map((planId) => (
            <div key={planId} className="rounded-xl border border-border bg-surface/30 p-5">
              <h3 className="text-lg font-medium capitalize text-landing">{planId}</h3>
              <ul className="mt-4 space-y-2">
                {Object.entries(catalog[planId]).map(([interval, price]) => (
                  <li key={interval}>
                    <button
                      type="button"
                      disabled={!isSignedIn || checkoutLoading !== null}
                      onClick={() => onCheckout(planId, interval as "monthly" | "quarterly" | "yearly")}
                      className="flex w-full items-center justify-between rounded-lg border border-border px-3 py-2 text-left text-sm transition hover:bg-surface-hover disabled:opacity-50"
                    >
                      <span className="capitalize text-muted">{interval}</span>
                      <span className="font-medium text-landing">
                        {checkoutLoading === `${planId}-${interval}` ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          inr(price.amountPaise)
                        )}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}

      {!isSignedIn && (
        <p className="text-sm text-muted">Sign in to view usage and start checkout.</p>
      )}
    </div>
  );
}

export default function BillingPage() {
  if (!clerkEnabled) {
    return (
      <div className="p-8 text-sm text-muted">
        Add Clerk keys to the root <code className="mx-1 rounded bg-surface-hover px-1">.env</code> to enable billing and usage meters.
      </div>
    );
  }
  return <BillingContent />;
}
