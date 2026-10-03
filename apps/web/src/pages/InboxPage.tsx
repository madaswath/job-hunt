import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { endpoints, type InboxItem } from "../lib/api/client";
import { Empty, ErrorNote, Loading } from "../ui/States";

function inboxActionsForState(state: string): { id: string; label: string }[] {
  const actions = [
    { id: "reject", label: "Reject" },
    { id: "save", label: "Save" },
  ];
  if (state === "review_required") {
    actions.push({ id: "request_analysis", label: "Request analysis" }, { id: "prepare_application", label: "Prepare application" });
  }
  if (state === "tailored") actions.push({ id: "request_draft_approval", label: "Request draft approval" });
  return actions;
}

type InboxDetail = InboxItem & {
  captured_text?: string;
  content_hash?: string;
  capture_method?: string;
  captured_at?: string;
  duplicate_of?: string | null;
  approval_tasks?: { id: string; kind: string; status: string }[];
  apply_url?: string;
};

export function InboxPage() {
  const [items, setItems] = useState<InboxDetail[] | null>(null);
  const [error, setError] = useState("");
  const [active, setActive] = useState<InboxDetail | null>(null);
  const [msg, setMsg] = useState("");
  const [draftBusy, setDraftBusy] = useState(false);
  const load = () => endpoints.inbox().then((r) => setItems(r.items as InboxDetail[])).catch((e) => setError(String(e)));
  useEffect(() => {
    load();
  }, []);
  if (error) return <ErrorNote message={error} />;
  if (!items) return <Loading />;
  if (items.length === 0) {
    return (
      <Empty
        title="Inbox is empty"
        body="Save your profile, then run Demo 1 refresh on Discover (Gmail + LinkedIn + ATS)."
      />
    );
  }

  const docs = active?.documents || [];
  const emails = active?.extracted_emails || [];

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id}>
            <button type="button" onClick={() => { setActive(item); setMsg(""); }} className="w-full rounded-xl border border-slate-200 bg-white p-4 text-left dark:border-slate-800 dark:bg-ink-900">
              <div className="flex justify-between gap-2">
                <span className="font-medium">{item.title}</span>
                <span className="text-sm text-amber-700">{item.overall_score}</span>
              </div>
              <p className="text-sm text-slate-500">{item.company} · {item.location} · {item.state}</p>
            </button>
          </li>
        ))}
      </ul>
      {active ? (
        <article className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-ink-900">
          <h2 className="text-xl font-semibold">{active.title}</h2>
          <p className="text-sm text-slate-500">{active.company} · {active.location} · state: {active.state}</p>
          <p className="mt-3 whitespace-pre-wrap text-sm">{active.captured_text || active.excerpt}</p>
          <p className="mt-2 text-sm"><a className="text-amber-700 underline" href={active.source_url} target="_blank" rel="noreferrer">Original source</a></p>
          <p className="mt-2 text-xs text-slate-500">
            Captured {active.captured_at || "—"} via {active.capture_method || "—"} · hash {active.content_hash?.slice(0, 12) || "—"}
            {active.duplicate_of ? ` · duplicate of ${active.duplicate_of}` : ""}
          </p>
          <p className="mt-2 text-xs text-slate-500">Apply links: {(active.extracted_apply_urls || []).join(", ") || active.apply_url || "none"}</p>
          <p className="mt-2 text-sm">Confidence {active.confidence} · Freshness {active.freshness_hours ?? "unknown"}h</p>
          <div className="mt-3 space-y-1 text-sm">
            {(active.breakdown || []).map((b) => (
              <p key={b.name}>{b.name}: {Math.round(b.score * 100)} ({b.reason})</p>
            ))}
          </div>
          <p className="mt-3 text-sm">Risks: {(active.risks || []).join("; ") || "none"}</p>
          {(active.approval_tasks || []).length > 0 ? (
            <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/30">
              <p className="font-medium">Pending approvals</p>
              {(active.approval_tasks || []).filter((t) => t.status === "pending").map((t) => (
                <div key={t.id} className="mt-2 flex flex-wrap gap-2">
                  <span>{t.kind.replace(/_/g, " ")}</span>
                  <button type="button" className="rounded border px-2 py-0.5" onClick={async () => {
                    await endpoints.decideApproval(t.id, "approved");
                    setMsg("Approved — check apply pack / Documents if prepare was approved.");
                    load();
                    const refreshed = await endpoints.inboxDetail(active.id);
                    setActive(refreshed.item as InboxDetail);
                  }}>Approve</button>
                  <button type="button" className="rounded border px-2 py-0.5" onClick={async () => {
                    await endpoints.decideApproval(t.id, "denied");
                    load();
                  }}>Deny</button>
                </div>
              ))}
            </div>
          ) : null}
          <div className="mt-4 flex flex-wrap gap-2">
            {inboxActionsForState(active.state).map((action) => (
              <button
                key={action.id}
                type="button"
                className="rounded-md border px-3 py-1 text-sm dark:border-slate-700"
                onClick={async () => {
                  const res = await endpoints.inboxAction(active.id, action.id);
                  setActive(res.item as InboxDetail);
                  load();
                }}
              >
                {action.label}
              </button>
            ))}
          </div>

          {docs.length > 0 ? (
            <div className="mt-4 rounded-md border border-slate-200 p-3 dark:border-slate-700">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium">Apply pack</p>
                <Link className="text-xs text-amber-700 underline" to="/documents">All documents</Link>
              </div>
              <ul className="mt-2 space-y-2 text-sm">
                {docs.map((d) => (
                  <li key={d.id}>
                    <p className="font-medium capitalize">{d.kind.replace(/_/g, " ")} · {d.status} · gate {d.fact_gate_passed ? "pass" : "blocked"}</p>
                    {d.content ? <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs dark:bg-ink-800">{d.content}</pre> : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {emails.length > 0 ? (
            <div className="mt-4 rounded-md border border-slate-200 p-3 text-sm dark:border-slate-700">
              <p className="font-medium">Recruiter email path</p>
              <p className="mt-1 text-xs text-slate-500">{emails.join(", ")}</p>
              <button
                type="button"
                disabled={draftBusy}
                className="mt-2 rounded-md border px-3 py-1 text-sm disabled:opacity-50"
                onClick={async () => {
                  setDraftBusy(true);
                  try {
                    const res = await endpoints.createOutreachDraft({
                      inbox_item_id: active.id,
                      channel: "email",
                      explicit_outreach_request: true,
                    });
                    setMsg(`Draft ready (${res.draft.status}). Review body, then you send — we never auto-send.`);
                  } catch (e) {
                    setMsg(String(e));
                  } finally {
                    setDraftBusy(false);
                  }
                }}
              >
                Draft recruiter email
              </button>
            </div>
          ) : null}

          {active.state === "ready_to_apply" ? (
            <button
              type="button"
              className="mt-4 rounded-md bg-amber-700 px-4 py-2 text-white"
              onClick={async () => {
                const h = await endpoints.handoffApply(active.id);
                if (h.apply_urls[0]) window.open(h.apply_urls[0], "_blank", "noopener,noreferrer");
                setMsg("Apply URL opened. Materials are above — you submit on the employer site.");
              }}
            >
              Open external apply (handoff)
            </button>
          ) : null}
          {msg ? <p className="mt-2 text-sm text-slate-500">{msg}</p> : null}
          <p className="mt-3 text-xs text-slate-500">Never auto-submit. Prepare creates an approval task; tailored/ready require explicit approve.</p>
        </article>
      ) : <p className="text-sm text-slate-500">Select a listing to review evidence.</p>}
    </div>
  );
}
