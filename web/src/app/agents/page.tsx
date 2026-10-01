import React from "react";
import { AGENTS } from "@/lib/agents-registry";

export const dynamic = "force-dynamic";

export default function AgentsPage() {
  const agentsList = Object.values(AGENTS);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="mb-8 flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-6 items-center rounded-full bg-indigo-500/10 px-2.5 text-xs font-semibold text-indigo-400">
            AI Agent Suite
          </span>
          <span className="text-xs text-muted-foreground">11 Autonomous Specialists</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Job-hunt Agents
        </h1>
        <p className="text-muted-foreground">
          Your specialized AI team coordinating discovery, qualification, matching, resume tailoring, verification, and recruiter communication.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {agentsList.map((agent) => (
          <div
            key={agent.id}
            className="flex flex-col justify-between rounded-xl border border-border/70 bg-card p-5 shadow-xs transition-all hover:border-indigo-500/40 hover:shadow-md"
          >
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10 text-lg font-bold text-indigo-400">
                    {agent.icon}
                  </div>
                  <div>
                    <h2 className="text-base font-semibold text-foreground">
                      {agent.name}
                    </h2>
                    <p className="text-xs text-muted-foreground">{agent.title}</p>
                  </div>
                </div>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  {agent.status}
                </span>
              </div>

              <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
                {agent.role}
              </p>

              <div className="mt-4 flex flex-wrap gap-1.5">
                {(agent.skills || []).map((skill) => (
                  <span
                    key={skill}
                    className="inline-block rounded-md bg-secondary px-2 py-0.5 text-[10px] font-medium text-secondary-foreground"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            <div className="mt-5 border-t border-border/40 pt-3 text-[11px] text-muted-foreground/80">
              <span className="font-mono text-[10px] text-indigo-400/80">
                {agent.module}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
