const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3800";

export type EntitlementsResponse = {
  success: boolean;
  planId: string;
  usage: Record<string, { limit: number | null; period: string; used: number }>;
};

export type PlanLimitError = {
  code: "PLAN_LIMIT_REACHED";
  feature?: string;
  used: number;
  limit: number;
  upgrade_plan: string;
};

async function apiFetch(path: string, init: RequestInit = {}, token?: string | null) {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  const data = await res.json().catch(() => ({}));
  return { res, data };
}

export async function fetchEntitlements(getToken: () => Promise<string | null>) {
  const token = await getToken();
  return apiFetch("/api/me/entitlements", {}, token);
}

export async function startCheckout(
  getToken: () => Promise<string | null>,
  planId: "premium" | "pro",
  interval: "monthly" | "quarterly" | "yearly"
) {
  const token = await getToken();
  return apiFetch(
    "/api/billing/checkout",
    { method: "POST", body: JSON.stringify({ planId, interval }) },
    token
  );
}

export async function fetchBillingPlans() {
  return apiFetch("/api/billing/plans");
}

export { API_BASE };
