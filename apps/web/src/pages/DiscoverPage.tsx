import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { endpoints, type SavedSearch } from "../lib/api/client";
import { Card, ErrorNote } from "../ui/States";

const CITIES = ["Bengaluru", "Hyderabad", "Pune", "Chennai", "Mumbai", "Gurugram", "Noida", "Ahmedabad", "Kolkata", "remote"];
const DEFAULT_TITLES = "Data Scientist, GenAI Engineer, Machine Learning Engineer";
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
  const [titles, setTitles] = useState(DEFAULT_TITLES);
  const [city, setCity] = useState("Bengaluru");
  const [mode, setMode] = useState("hybrid");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState<SavedSearch[]>([]);
  const [importStatus, setImportStatus] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    endpoints.savedSearches().then((r) => setSaved(r.saved_searches)).catch(() => undefined);
  }, []);

  async function runDemo1() {
    setBusy(true);
    setError("");
    try {
      const res = await endpoints.demo1Refresh({
        cities: [city, "remote"],
        work_mode: mode,
        enable_autopilot: true,
      });
      setStatus(
        `Demo 1 queued ${res.scans.length} scans (${res.scans.map((s) => s.connector_id).join(", ")}). ${res.hint}`,
      );
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Discover</h1>
      <p className="text-sm text-slate-500">
        Demo 1 spine: one refresh pulls <strong>Gmail alerts</strong>, <strong>LinkedIn</strong> recorded listings, and <strong>public ATS</strong> into a shared index, then ranks into{" "}
        <Link className="underline" to="/inbox">Review Inbox</Link>.
      </p>
      {error ? <ErrorNote message={error} /> : null}

      <Card title="LinkedIn scraper → master index">
        <p className="mb-3 text-sm text-slate-500">
          Run <code className="text-xs">scripts/linkedin_browserless_scraper.py</code> or the batch runner, then ingest here.
          Expects <code className="text-xs">results.json</code> / <code className="text-xs">jobs_clean.csv</code> /
          <code className="text-xs">recruiter_posts_drafts.csv</code> under <code className="text-xs">data/linkedin-exports/&lt;role&gt;/</code>.
          Keeps the latest <strong>100 jobs per keyword</strong> and <strong>10–15 hiring posts</strong>, stores them in the shared master DB,
          strips scraper email drafts, then ranks into Inbox.
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            className="rounded-md bg-indigo-700 px-4 py-2 text-white disabled:opacity-50"
            onClick={async () => {
              setBusy(true);
              setError("");
              try {
                const res = await endpoints.linkedinMasterIngest({
                  jobs_per_keyword: 100,
                  posts_limit: 15,
                  match_into_inbox: true,
                });
                setStatus(
                  `Master index: ${res.jobs_upserted} jobs + ${res.posts_upserted} posts from ${res.export_dir}. Inbox matches: ${res.inbox_matches_created}.`,
                );
              } catch (err) {
                setError(String(err));
              } finally {
                setBusy(false);
              }
            }}
          >
            Ingest LinkedIn exports to master DB
          </button>
          <button
            type="button"
            disabled={busy}
            className="rounded-md border px-4 py-2 text-sm disabled:opacity-50"
            onClick={async () => {
              setBusy(true);
              setError("");
              try {
                const res = await endpoints.matchShared({ limit: 80 });
                setStatus(`Re-matched shared catalogue → ${res.inbox_matches_created} inbox items.`);
              } catch (err) {
                setError(String(err));
              } finally {
                setBusy(false);
              }
            }}
          >
            Re-match master index to my inbox
          </button>
        </div>
      </Card>

      <Card title="Demo 1 — refresh my matches">
        <p className="mb-3 text-sm text-slate-500">
          Queues all three Demo 1 sources and enables daily autopilot. Start the worker after queuing. Fixtures power local demo; live Gmail API stays gated.
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            className="rounded-md bg-amber-700 px-4 py-2 text-white disabled:opacity-50"
            onClick={runDemo1}
          >
            {busy ? "Queuing…" : "Refresh Gmail + LinkedIn + ATS"}
          </button>
          <Link className="rounded-md border px-4 py-2 text-sm" to="/inbox">Open inbox</Link>
        </div>
        {status ? <p className="mt-2 text-sm text-slate-500">{status}</p> : null}
      </Card>

      <Card title="Narrow search and queue a single ATS fixture scan">
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
          <label className="text-sm">City (India) or remote
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
          <label className="text-sm">Source
            <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" readOnly value="public_ats_fixture (live)" />
          </label>
          <div className="md:col-span-2">
            <button type="submit" className="rounded-md border border-amber-800 px-4 py-2 text-sm text-amber-900 dark:text-amber-100">Queue ATS-only scan</button>
          </div>
        </form>
      </Card>

      <Card title="Import a candidate-captured LinkedIn export">
        <p className="mb-3 text-sm text-slate-500">
          Optional upload of JSON from your local browserless tool. Demo 1 LinkedIn fixture ingest does not need this — use Refresh above.
          Cookies and generated emails are stripped.
        </p>
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
