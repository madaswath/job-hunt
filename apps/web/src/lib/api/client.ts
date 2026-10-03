const BASE = import.meta.env.VITE_API_BASE || "/api/v1";

type ClerkSession = { getToken: () => Promise<string | null> };
type ClerkGlobal = { Clerk?: { session?: ClerkSession | null } };

export function clerkEnabled(): boolean {
  return Boolean(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY);
}

export function getTestToken(): string | null {
  return localStorage.getItem("jobhunt_test_token");
}

export async function resolveAuthToken(
  clerk: ClerkGlobal["Clerk"] | undefined = (window as ClerkGlobal).Clerk,
  useClerk: boolean = clerkEnabled(),
): Promise<string | null> {
  if (useClerk) {
    if (!clerk?.session) return null;
    return (await clerk.session.getToken()) ?? null;
  }
  return getTestToken();
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await resolveAuthToken();
  const headers = new Headers(init.headers);
  headers.set("content-type", "application/json");
  if (token) headers.set("authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const endpoints = {
  me: () => api<{ user_id: string; email: string; name: string }>("/me"),
  dashboard: () => api<Dashboard>("/dashboard"),
  profile: () => api<ProfileResponse>("/profile"),
  saveProfile: (body: unknown) => api<ProfileResponse>("/profile", { method: "PUT", body: JSON.stringify(body) }),
  inbox: () => api<{ items: InboxItem[] }>("/inbox"),
  inboxDetail: (id: string) => api<{ item: InboxItem }>(`/inbox/${id}`),
  inboxAction: (id: string, action: string) =>
    api<{ item: InboxItem }>(`/inbox/${id}/actions`, { method: "POST", body: JSON.stringify({ action }) }),
  sources: () => api<{ sources: Source[] }>("/sources"),
  agents: () => api<{ agents: Agent[]; runs: AgentRun[] }>("/agents"),
  approvals: () => api<{ approvals: Approval[]; pending: Approval[] }>("/approvals"),
  decideApproval: (taskId: string, decision: "approved" | "denied") =>
    api<Record<string, unknown>>(`/approvals/${taskId}/decide`, { method: "POST", body: JSON.stringify({ decision }) }),
  handoffApply: (inboxId: string) => api<{ apply_urls: string[] }>(`/inbox/${inboxId}/handoff`, { method: "POST" }),
  queueScan: (body: unknown) => api<{ scan_job_id: string; status: string }>("/discovery/scans", { method: "POST", body: JSON.stringify(body) }),
  demo1Refresh: (body: unknown = {}) =>
    api<{ status: string; scans: { scan_job_id: string; connector_id: string; status: string }[]; hint: string }>(
      "/discovery/demo1-refresh",
      { method: "POST", body: JSON.stringify(body) },
    ),
  linkedinMasterIngest: (body: unknown = {}) =>
    api<{
      status: string;
      jobs_upserted: number;
      posts_upserted: number;
      inbox_matches_created: number;
      by_keyword: Record<string, number>;
      export_dir: string;
    }>("/discovery/linkedin-master-ingest", { method: "POST", body: JSON.stringify(body) }),
  matchShared: (body: unknown = {}) =>
    api<{ status: string; inbox_matches_created: number }>("/discovery/match-shared", { method: "POST", body: JSON.stringify(body) }),
  sharedJobs: () => api<{ items: { id: string; title: string; company: string; source_connector: string }[] }>("/discovery/shared-jobs"),
  importCandidateCapture: (body: unknown) => api<{ scan_job_id: string; status: string; jobs: number; posts: number }>("/discovery/candidate-imports", { method: "POST", body: JSON.stringify(body) }),
  savedSearches: () => api<{ saved_searches: SavedSearch[] }>("/discovery/saved-searches"),
  connectSource: (connectorId: string, body: unknown) =>
    api<Record<string, unknown>>(`/sources/${connectorId}/connect`, { method: "POST", body: JSON.stringify(body) }),
  revokeSource: (connectorId: string) => api<Record<string, unknown>>(`/sources/${connectorId}/revoke`, { method: "POST" }),
  ingestSource: (connectorId: string, body: unknown) =>
    api<{ scan_job_id: string; status: string }>(`/sources/${connectorId}/ingest`, { method: "POST", body: JSON.stringify(body) }),
  createOutreachDraft: (body: unknown) => api<{ draft: OutreachDraft }>("/outreach/drafts", { method: "POST", body: JSON.stringify(body) }),
  exportProfile: () => api<Record<string, unknown>>("/profile/export", { method: "POST" }),
  deleteProfile: () => api<Record<string, unknown>>("/profile/delete", { method: "POST" }),
};

export type InboxItem = {
  id: string;
  state: string;
  saved: boolean;
  rejected: boolean;
  title: string;
  company: string;
  location: string;
  excerpt: string;
  source_url: string;
  extracted_emails: string[];
  extracted_apply_urls: string[];
  capture_kind: string;
  overall_score: number;
  confidence: number;
  breakdown: { name: string; weight: number; score: number; reason: string }[];
  matched_skills: string[];
  missing_skills: string[];
  reasons_to_apply: string[];
  risks: string[];
  freshness_hours: number | null;
  documents?: { id: string; kind: string; status: string; fact_gate_passed: boolean; content?: string }[];
};

export type ConnectorHealthRow = {
  connector_id: string;
  implementation_status: string;
  last_successful_sync: string | null;
  ingestion_count: number;
  failure_reason?: string | null;
  rate_limit?: { remaining: number; limit_per_hour: number };
};

export type Dashboard = {
  recommended: { id: string; title: string; company: string; overall_score: number; state: string }[];
  pending_approvals: number;
  scan_health: { id: string; status: string; last_error: string | null; created_at: string }[];
  connector_health?: ConnectorHealthRow[];
  applications_by_stage: Record<string, number>;
  upcoming_follow_ups: unknown[];
  interview_reminders: unknown[];
  source_freshness: Record<string, string | null>;
  agent_timeline: { agent_name: string; status: string; created_at: string }[];
};

export type VerifiedFactRow = { id?: string; kind: string; value: string; source?: string; verified?: boolean };

export type ProfileResponse = {
  profile: Record<string, unknown> | null;
  verified_facts: VerifiedFactRow[];
  defaults: { cities: string[]; role_aliases: Record<string, string[]>; beta_ds_ai_titles?: string[] };
  feature_us_market: boolean;
};

export type Source = {
  id: string;
  slug: string;
  status: string;
  policy?: { retention_days?: number; max_requests_per_hour?: number; terms_summary?: string };
  health: { status: string; last_ingest_at?: string; account_status?: string };
  account?: { status: string; consent_at?: string; revoked_at?: string };
};
export type OutreachDraft = { id: string; inbox_item_id: string; channel: string; body: string; status: string };
export type Agent = { name: string; role: string; status: string };
export type AgentRun = { run_id: string; agent_name: string; status: string; created_at: string };
export type Approval = { id: string; kind: string; status: string };
export type SavedSearch = { id: string; name: string; query: unknown };
