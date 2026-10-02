import { useEffect, useState } from "react";
import { endpoints, type SavedSearch } from "../lib/api/client";
import { Card, ErrorNote } from "../ui/States";

const CITIES = ["Bengaluru", "Hyderabad", "Pune", "Chennai", "Mumbai", "Gurugram", "Noida", "Ahmedabad", "Kolkata", "remote"];
const UNSAFE_IMPORT_KEYS = ["cookie", "session", "password", "authorization", "bearer", "email_draft", "generated_email"];

function removeUnsafeImportFields(value: unknown): { value: unknown; removed: boolean } {
  if (Array.isArray(value)) {
    const children = value.map(removeUnsafeImportFields);
    return { value: children.map((child) => child.value), removed: children.some((child) => child.removed) };
  }
  if (value && typeof value === "object") {
    let removed = false;
    const clean: Record<string, unknown> = {};
    for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
      if (UNSAFE_IMPORT_KEYS.some((part) => key.toLowerCase().includes(part))) {
        removed = true;
        continue;
      }
      const next = removeUnsafeImportFields(child);
      clean[key] = next.value;
      removed ||= next.removed;
    }
    return { value: clean, removed };
  }
  return { value, removed: false };
}

export function DiscoverPage() {
  const [titles, setTitles] = useState("GenAI Engineer");
  const [city, setCity] = useState("Bengaluru");
  const [mode, setMode] = useState("hybrid");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState<SavedSearch[]>([]);
  const [importStatus, setImportStatus] = useState("");
  useEffect(() => {
    endpoints.savedSearches().then((r) => setSaved(r.saved_searches)).catch(() => undefined);
  }, []);
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Discover</h1>
      {error ? <ErrorNote message={error} /> : null}
      <Card title="Search and queue fixture scan">
        <form
          className="grid gap-3 md:grid-cols-2"
          onSubmit={async (e) => {
            e.preventDefault();
            setError("");
            try {
              const res = await endpoints.queueScan({
                connector_id: "public_ats_fixture",
                titles: titles.split(",").map((t) => t.trim()).filter(Boolean),
                cities: [city],
                work_mode: mode,
                saved_search_name: "last-scan",
              });
              setStatus(`Queued ${res.scan_job_id} (${res.status}). Worker will ingest fixtures.`);
            } catch (err) {
              setError(String(err));
            }
          }}
        >
          <label className="text-sm">Target titles
            <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" value={titles} onChange={(e) => setTitles(e.target.value)} />
          </label>
          <label className="text-sm">Indian city
            <select className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" value={city} onChange={(e) => setCity(e.target.value)}>
              {CITIES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <label className="text-sm">Work mode
            <select className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" value={mode} onChange={(e) => setMode(e.target.value)}>
              <option>remote</option>
              <option>hybrid</option>
              <option>onsite</option>
            </select>
          </label>
          <label className="text-sm">Experience range
            <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" defaultValue="3-8 years" />
          </label>
          <label className="text-sm">CTC range (INR annual)
            <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" defaultValue="2500000-4000000" />
          </label>
          <label className="text-sm">Employment type
            <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" defaultValue="full-time" />
          </label>
          <label className="text-sm">Source
            <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" readOnly value="public_ats_fixture (live)" />
          </label>
          <div className="md:col-span-2">
            <button type="submit" className="rounded-md bg-amber-700 px-4 py-2 text-white">Queue scan</button>
            {status ? <p className="mt-2 text-sm text-slate-500">{status}</p> : null}
          </div>
        </form>
      </Card>
      <Card title="Import a candidate-captured LinkedIn export">
        <p className="mb-3 text-sm text-slate-500">Upload the JSON exported by your local browserless tool. It is scored by Narada → Ganesha → Arjuna and appears in Review inbox. The platform never receives browser cookies, scrapes LinkedIn, auto-applies, or sends recruiter email.</p>
        <label className="block text-sm">Browserless JSON export (up to 100 jobs and 100 hiring posts)
          <input
            className="mt-1 block w-full text-sm"
            type="file"
            accept="application/json,.json"
            onChange={async (event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              setError("");
              setImportStatus("Reading export…");
              try {
                const parsed = JSON.parse(await file.text());
                const sanitized = removeUnsafeImportFields(parsed);
                const payload = sanitized.value as { jobs?: unknown[]; posts?: unknown[]; metadata?: unknown };
                const jobCount = payload.jobs?.length || 0;
                const postCount = payload.posts?.length || 0;
                if (jobCount > 100 || postCount > 100) throw new Error("Each import is limited to 100 jobs and 100 posts.");
                const res = await endpoints.importCandidateCapture({
                  ...payload,
                  titles: titles.split(",").map((title) => title.trim()).filter(Boolean).slice(0, 10),
                  cities: [city],
                });
                setImportStatus(`${sanitized.removed ? "Removed unsafe session/draft fields. " : ""}Queued ${res.jobs} jobs and ${res.posts} posts (${res.scan_job_id}). Start the worker, then review ranked matches in Inbox.`);
              } catch (err) {
                setImportStatus("");
                setError(`Import was not queued: ${String(err)}`);
              } finally {
                event.target.value = "";
              }
            }}
          />
        </label>
        {importStatus ? <p className="mt-2 text-sm text-slate-500">{importStatus}</p> : null}
      </Card>
      <Card title="Saved searches">
        {saved.length === 0 ? <p className="text-sm text-slate-500">Queue a scan with a name to save it.</p> : (
          <ul className="text-sm">{saved.map((s) => <li key={s.id}>{s.name}</li>)}</ul>
        )}
      </Card>
    </div>
  );
}
