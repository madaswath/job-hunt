import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { endpoints, type Dashboard } from "../lib/api/client";
import { Card, ErrorNote, Loading } from "../ui/States";

export function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    endpoints.dashboard().then(setData).catch((e) => setError(String(e)));
  }, []);
  if (error) return <ErrorNote message={error} />;
  if (!data) return <Loading />;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Today</h1>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card title="Recommended jobs" action={<Link className="text-sm text-amber-700" to="/inbox">Inbox</Link>}>
          {data.recommended.length === 0 ? <p className="text-sm text-slate-500">No strong matches yet. Queue a fixture scan.</p> : (
            <ul className="space-y-2 text-sm">
              {data.recommended.map((j) => (
                <li key={j.id}><span className="font-medium">{j.title}</span> · {j.company} · {j.overall_score}</li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Pending approvals"><p className="text-3xl font-semibold">{data.pending_approvals}</p></Card>
        <Card title="Scan health">
          {data.scan_health.length === 0 ? <p className="text-sm text-slate-500">No scans yet.</p> : (
            <ul className="text-sm">{data.scan_health.map((s) => <li key={s.id}>{s.status}{s.last_error ? ` — ${s.last_error}` : ""}</li>)}</ul>
          )}
        </Card>
        <Card title="Applications by stage"><p className="text-sm text-slate-500">Tracker planned for Phase 2.</p></Card>
        <Card title="Follow-ups"><p className="text-sm text-slate-500">No upcoming follow-ups.</p></Card>
        <Card title="Interview reminders"><p className="text-sm text-slate-500">No interviews recorded.</p></Card>
        <Card title="Connector health">
          {(data.connector_health?.length ?? 0) === 0 ? (
            <p className="text-sm text-slate-500">No connector activity yet.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {data.connector_health!.map((c) => (
                <li key={c.connector_id}>
                  <span className="font-medium">{c.connector_id}</span> · last sync: {String(c.last_successful_sync ?? "—")} ·
                  ingested: {c.ingestion_count ?? 0}
                  {c.failure_reason ? ` · error: ${c.failure_reason}` : ""}
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Agent activity">
          {data.agent_timeline.length === 0 ? <p className="text-sm text-slate-500">No agent runs yet.</p> : (
            <ol className="space-y-1 text-sm">
              {data.agent_timeline.map((a, i) => <li key={`${a.agent_name}-${i}`}>{a.agent_name} · {a.status}</li>)}
            </ol>
          )}
        </Card>
      </div>
    </div>
  );
}
