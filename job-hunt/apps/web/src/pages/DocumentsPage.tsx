import { useEffect, useState } from "react";
import { api } from "../lib/api/client";
import { Empty, ErrorNote, Loading } from "../ui/States";

type Doc = {
  id: string;
  kind: string;
  status: string;
  fact_gate_passed: boolean;
  inbox_item_id: string;
  content?: string;
};

export function DocumentsPage() {
  const [items, setItems] = useState<Doc[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<{ items: Doc[] }>("/documents")
      .then((r) => setItems(r.items))
      .catch((e) => setError(String(e)));
  }, []);
  if (error) return <ErrorNote message={error} />;
  if (!items) return <Loading />;
  if (items.length === 0) {
    return (
      <Empty
        title="No tailored documents yet"
        body="Approve prepare on an inbox item to generate fact-gated CV, cover letter, and application answers."
      />
    );
  }
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Documents</h1>
      <p className="text-sm text-slate-500">Dharma must pass before a draft is ready. Never auto-submitted.</p>
      <ul className="space-y-3">
        {items.map((d) => (
          <li key={d.id} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-ink-900">
            <div className="flex justify-between gap-2">
              <span className="font-medium capitalize">{d.kind.replace("_", " ")}</span>
              <span className="text-sm">{d.status} · gate {d.fact_gate_passed ? "pass" : "blocked"}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
