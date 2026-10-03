import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { endpoints, type ApplicationItem } from "../lib/api/client";
import { Empty, ErrorNote, Loading } from "../ui/States";

const NEXT: Record<string, string[]> = {
  started: ["applied", "interview", "rejected", "withdrawn"],
  applied: ["interview", "offer", "rejected", "withdrawn"],
  interview: ["offer", "rejected", "withdrawn"],
  offer: ["rejected", "withdrawn"],
  rejected: [],
  withdrawn: [],
};

function label(state: string) {
  return state.replace(/_/g, " ");
}

export function ApplicationsPage() {
  const [items, setItems] = useState<ApplicationItem[] | null>(null);
  const [byStage, setByStage] = useState<Record<string, number>>({});
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  const load = () =>
    endpoints
      .applications()
      .then((r) => {
        setItems(r.items);
        setByStage(r.by_stage || {});
      })
      .catch((e) => setError(String(e)));

  useEffect(() => {
    load();
  }, []);

  if (error) return <ErrorNote message={error} />;
  if (!items) return <Loading />;

  if (items.length === 0) {
    return (
      <Empty
        title="No applications tracked yet"
        body="Open an external apply handoff from Inbox (or mark a role applied). We never auto-submit — you own the send."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Applications</h1>
          <p className="text-sm text-slate-500">Post-handoff tracker. Outcomes are yours to record.</p>
        </div>
        <Link className="text-sm text-amber-700 underline" to="/inbox">
          Back to Inbox
        </Link>
      </div>

      <div className="flex flex-wrap gap-2 text-sm">
        {Object.entries(byStage)
          .filter(([, n]) => n > 0)
          .map(([state, n]) => (
            <span key={state} className="rounded-md border border-slate-200 px-2 py-1 dark:border-slate-700">
              {label(state)}: {n}
            </span>
          ))}
      </div>

      <ul className="space-y-3">
        {items.map((app) => (
          <li key={app.id} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-ink-900">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-medium">{app.title || "Role"} · {app.company || "Company"}</p>
                <p className="text-sm text-slate-500">
                  {app.location || "—"} · {label(app.state)}
                  {app.overall_score != null ? ` · score ${app.overall_score}` : ""}
                </p>
              </div>
              {app.apply_url ? (
                <a className="text-sm text-amber-700 underline" href={app.apply_url} target="_blank" rel="noreferrer">
                  Apply URL
                </a>
              ) : null}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {(NEXT[app.state] || []).map((next) => (
                <button
                  key={next}
                  type="button"
                  className="rounded-md border px-3 py-1 text-sm dark:border-slate-700"
                  onClick={async () => {
                    await endpoints.patchApplication(app.id, { state: next });
                    setMsg(`Moved to ${label(next)}`);
                    load();
                  }}
                >
                  Mark {label(next)}
                </button>
              ))}
            </div>
          </li>
        ))}
      </ul>
      {msg ? <p className="text-sm text-slate-500">{msg}</p> : null}
    </div>
  );
}
