"use client";

import React, { useEffect, useState } from "react";
import { Puzzle, ShieldCheck, CheckCircle2, Lock } from "lucide-react";

type PluginEntry = {
  id: string;
  name: string;
  category: string;
  description: string;
  allowed?: string[];
  disallowed?: string[];
};

export default function PluginsPage() {
  const [plugins, setPlugins] = useState<PluginEntry[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedPlugin, setSelectedPlugin] = useState<PluginEntry | null>(null);
  const [connectedMap, setConnectedMap] = useState<Record<string, boolean>>({
    gmail: true,
  });

  useEffect(() => {
    fetch("/api/plugins")
      .then((r) => {
        if (!r.ok) throw new Error("Could not load plugin registry");
        return r.json();
      })
      .then((data) => setPlugins(data.plugins || []))
      .catch((e) => setLoadError(e.message));
  }, []);

  const handleToggleConnect = (pluginId: string) => {
    setConnectedMap((prev) => ({
      ...prev,
      [pluginId]: !prev[pluginId],
    }));
    setSelectedPlugin(null);
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="mb-8 flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-6 items-center rounded-full bg-indigo-500/10 px-2.5 text-xs font-semibold text-indigo-400">
            Plugin Architecture
          </span>
          <span className="text-xs text-muted-foreground">Least-Privilege Authenticated Connectors</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Job-hunt Plugin Store
        </h1>
        <p className="text-muted-foreground">
          Connect your authorized job platforms, email alerts, and productivity workspaces with strict sandboxed permissions and human approval gating.
        </p>
      </div>

      {loadError && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {loadError}
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {plugins.map((plugin) => {
          const isConnected = connectedMap[plugin.id];
          return (
            <div
              key={plugin.id}
              className="flex flex-col justify-between rounded-xl border border-border/80 bg-card p-5 shadow-xs transition-all hover:border-indigo-500/30"
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 font-bold">
                      <Puzzle className="size-5" />
                    </div>
                    <div>
                      <h2 className="text-sm font-semibold text-foreground">{plugin.name}</h2>
                      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                        {plugin.category}
                      </span>
                    </div>
                  </div>
                  {isConnected ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                      <CheckCircle2 className="size-3" /> Connected
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                      Available
                    </span>
                  )}
                </div>

                <p className="mt-4 text-xs text-muted-foreground leading-relaxed">
                  {plugin.description}
                </p>

                <div className="mt-4 border-t border-border/50 pt-3">
                  <div className="text-[11px] font-semibold text-foreground/80 mb-1.5 flex items-center gap-1">
                    <ShieldCheck className="size-3.5 text-emerald-400" />
                    Sandboxed Capabilities
                  </div>
                  <ul className="space-y-1">
                    {(plugin.allowed || []).map((perm: string, i: number) => (
                      <li key={i} className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                        <span className="text-emerald-400 text-xs">✓</span> {perm}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="mt-5 border-t border-border/40 pt-3 flex items-center justify-between">
                <button
                  onClick={() => setSelectedPlugin(plugin)}
                  className="text-xs font-medium text-indigo-400 hover:text-indigo-300"
                >
                  Permissions & Policy
                </button>
                <button
                  onClick={() => handleToggleConnect(plugin.id)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    isConnected
                      ? "border border-border bg-surface text-muted-foreground hover:bg-red-500/10 hover:text-red-400"
                      : "bg-indigo-600 text-white hover:bg-indigo-500"
                  }`}
                >
                  {isConnected ? "Disconnect" : "Connect"}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Permission Inspection Modal */}
      {selectedPlugin && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-base font-semibold text-foreground">
                {selectedPlugin.name} Authorization Policy
              </h3>
              <button
                onClick={() => setSelectedPlugin(null)}
                className="text-muted-foreground hover:text-foreground text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="my-4 space-y-4 text-xs">
              <div>
                <h4 className="font-semibold text-emerald-400 mb-1.5">✓ Allowed Operations</h4>
                <ul className="space-y-1 text-muted-foreground">
                  {(selectedPlugin.allowed || []).map((item: string, i: number) => (
                    <li key={i}>• {item}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="font-semibold text-red-400 mb-1.5">✕ Strictly Forbidden Autonomous Actions</h4>
                <ul className="space-y-1 text-muted-foreground">
                  {(selectedPlugin.disallowed || []).map((item: string, i: number) => (
                    <li key={i}>• {item}</li>
                  ))}
                </ul>
              </div>

              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-amber-300">
                <div className="flex items-start gap-2">
                  <Lock className="size-4 shrink-0 mt-0.5" />
                  <span>
                    <strong>Human Approval Gate:</strong> Outreach messages and application submissions require explicit confirmation in your Approval Queue.
                  </span>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-border pt-3">
              <button
                onClick={() => setSelectedPlugin(null)}
                className="rounded-lg border border-border px-4 py-1.5 text-xs font-medium text-foreground hover:bg-surface"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
