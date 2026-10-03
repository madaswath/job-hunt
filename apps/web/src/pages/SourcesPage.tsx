import { useEffect, useState } from "react";
import { endpoints, type Source } from "../lib/api/client";
import { ErrorNote, Loading } from "../ui/States";

const DEMO1_IDS = new Set(["gmail_alerts", "linkedin", "public_ats_fixture"]);

export function SourcesPage() {
  const [sources, setSources] = useState<Source[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const reload = () => endpoints.sources().then((r) => setSources(r.sources)).catch((e) => setError(String(e)));

  useEffect(() => {
    reload();
  }, []);

  async function connect(id: string, body: Record<string, unknown> = {}) {
    setBusy(id);
    try {
      await endpoints.connectSource(id, body);
      await reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  async function revoke(id: string) {
    setBusy(id);
    try {
      await endpoints.revokeSource(id);
      await reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  async function ingest(id: string, body: Record<string, unknown> = {}) {
    setBusy(`${id}-ingest`);
    try {
      await endpoints.ingestSource(id, body);
      await reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  if (error) return <ErrorNote message={error} />;
  if (!sources) return <Loading />;

  const demo1 = sources.filter((s) => DEMO1_IDS.has(s.id));
  const rest = sources.filter((s) => !DEMO1_IDS.has(s.id));

  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold">Sources</h1>
      <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">
        Demo 1 sources first. Gmail uses narrow label scope; LinkedIn Demo 1 uses recorded listings (not unrestricted live scrape);
        ATS fixtures are live for local demo. No auto-send.
      </p>

      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Demo 1</h2>
      <div className="mb-6 grid gap-3 md:grid-cols-2">
        {demo1.map((s) => {
          const connected = s.account?.status === "connected";
          const live = s.status === "live" || s.status === "ingestion_ready";
          return (
            <article key={s.id} className="rounded-xl border border-amber-200 bg-white p-4 dark:border-amber-900 dark:bg-ink-900">
              <h3 className="font-medium">{s.id}</h3>
              <p className="text-sm capitalize text-slate-500">Status: {s.status}</p>
              {s.policy?.terms_summary ? <p className="mt-2 text-xs text-slate-500">{s.policy.terms_summary}</p> : null}
              {s.health?.last_ingest_at && (
                <p className="mt-1 text-xs text-slate-500">Last ingest: {String(s.health.last_ingest_at)}</p>
              )}
              {live && s.id === "gmail_alerts" && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {!connected ? (
                    <button type="button" disabled={busy !== null} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white disabled:opacity-50" onClick={() => connect("gmail_alerts", { labels: ["JobAlerts", "Jobs"] })}>
                      Connect Gmail alerts
                    </button>
                  ) : (
                    <>
                      <button type="button" disabled={busy !== null} className="rounded bg-emerald-700 px-3 py-1 text-sm text-white disabled:opacity-50" onClick={() => ingest("gmail_alerts", {})}>
                        Sync alerts
                      </button>
                      <button type="button" disabled={busy !== null} className="rounded border px-3 py-1 text-sm disabled:opacity-50" onClick={() => revoke("gmail_alerts")}>
                        Revoke
                      </button>
                    </>
                  )}
                </div>
              )}
              {live && s.id === "linkedin" && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {!connected ? (
                    <button type="button" disabled={busy !== null} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white disabled:opacity-50" onClick={() => connect("linkedin", {})}>
                      Enable LinkedIn ingest
                    </button>
                  ) : (
                    <>
                      <button type="button" disabled={busy !== null} className="rounded bg-emerald-700 px-3 py-1 text-sm text-white disabled:opacity-50" onClick={() => ingest("linkedin", {})}>
                        Sync LinkedIn fixtures
                      </button>
                      <button type="button" disabled={busy !== null} className="rounded border px-3 py-1 text-sm disabled:opacity-50" onClick={() => revoke("linkedin")}>
                        Revoke
                      </button>
                    </>
                  )}
                </div>
              )}
              {live && s.id === "public_ats_fixture" && (
                <p className="mt-2 text-xs text-slate-500">Queued from Discover Demo 1 refresh or ATS-only scan. No OAuth required.</p>
              )}
            </article>
          );
        })}
      </div>

      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Other connectors</h2>
      <div className="grid gap-3 md:grid-cols-2">
        {rest.map((s) => {
          const live = s.status === "live" || s.status === "ingestion_ready";
          return (
            <article key={s.id} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-ink-900">
              <h3 className="font-medium">{s.id}</h3>
              <p className="text-sm capitalize text-slate-500">Status: {s.status}</p>
              {!live && <p className="mt-2 text-xs text-slate-500">Catalog or planned — not a live integration.</p>}
              {live && s.id === "browser_capture" && (
                <p className="mt-2 text-xs text-slate-500">Use bookmarklet or POST /sources/browser-capture from an approved client.</p>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
