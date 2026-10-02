import { useEffect, useState } from "react";
import { endpoints, type Source } from "../lib/api/client";
import { ErrorNote, Loading } from "../ui/States";

export function SourcesPage() {
  const [sources, setSources] = useState<Source[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const reload = () => endpoints.sources().then((r) => setSources(r.sources)).catch((e) => setError(String(e)));

  useEffect(() => {
    reload();
  }, []);

  async function connectGmail() {
    setBusy("gmail");
    try {
      await endpoints.connectSource("gmail_alerts", { labels: ["JobAlerts", "Jobs"] });
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

  async function ingestGmail() {
    setBusy("gmail-ingest");
    try {
      await endpoints.ingestSource("gmail_alerts", {});
      await reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  if (error) return <ErrorNote message={error} />;
  if (!sources) return <Loading />;
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Sources</h1>
      <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">
        Live connectors require consent. Gmail uses narrow label scope; browser capture is candidate-initiated only. No auto-send.
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        {sources.map((s) => {
          const connected = s.account?.status === "connected";
          const live = s.status === "live" || s.status === "ingestion_ready";
          const gmailLabel = s.id === "gmail_alerts" && s.status === "ingestion_ready";
          return (
            <article key={s.id} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-ink-900">
              <h2 className="font-medium">{s.id}</h2>
              <p className="text-sm capitalize text-slate-500">
                Status: {gmailLabel ? "fixture / live-ingestion ready" : s.status}
              </p>
              {s.policy?.retention_days != null && (
                <p className="mt-1 text-xs text-slate-500">Retention: {s.policy.retention_days} days</p>
              )}
              {s.health?.last_ingest_at && (
                <p className="mt-1 text-xs text-slate-500">Last ingest: {String(s.health.last_ingest_at)}</p>
              )}
              {!live && <p className="mt-2 text-xs text-slate-500">Catalog or planned — not a live integration.</p>}
              {live && s.id === "gmail_alerts" && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {!connected ? (
                    <button
                      type="button"
                      disabled={busy !== null}
                      className="rounded bg-indigo-600 px-3 py-1 text-sm text-white disabled:opacity-50"
                      onClick={connectGmail}
                    >
                      Connect Gmail alerts
                    </button>
                  ) : (
                    <>
                      <button
                        type="button"
                        disabled={busy !== null}
                        className="rounded bg-emerald-700 px-3 py-1 text-sm text-white disabled:opacity-50"
                        onClick={ingestGmail}
                      >
                        Sync alerts
                      </button>
                      <button
                        type="button"
                        disabled={busy !== null}
                        className="rounded border border-slate-300 px-3 py-1 text-sm disabled:opacity-50"
                        onClick={() => revoke("gmail_alerts")}
                      >
                        Revoke
                      </button>
                    </>
                  )}
                </div>
              )}
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
