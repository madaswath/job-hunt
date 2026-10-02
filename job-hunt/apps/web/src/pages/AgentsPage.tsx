import { useEffect, useState } from "react";
import { endpoints, type Agent, type AgentRun } from "../lib/api/client";
import { ErrorNote, Loading } from "../ui/States";

export function AgentsPage() {
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    endpoints.agents().then((r) => {
      setAgents(r.agents);
      setRuns(r.runs);
    }).catch((e) => setError(String(e)));
  }, []);
  if (error) return <ErrorNote message={error} />;
  if (!agents) return <Loading />;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Agents</h1>
      <div className="grid gap-3 md:grid-cols-2">
        {agents.map((a) => (
          <article key={a.name} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-ink-900">
            <h2 className="font-medium capitalize">{a.name}</h2>
            <p className="text-sm text-slate-500">{a.role}</p>
            <p className="mt-2 text-xs uppercase tracking-wide">{a.status}</p>
          </article>
        ))}
      </div>
      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase text-slate-500">Recent runs</h2>
        {runs.length === 0 ? <p className="text-sm text-slate-500">No runs yet.</p> : (
          <ul className="text-sm">{runs.map((r) => <li key={r.run_id}>{r.agent_name} · {r.status}</li>)}</ul>
        )}
      </section>
    </div>
  );
}
