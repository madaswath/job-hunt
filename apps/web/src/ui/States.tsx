import type { ReactNode } from "react";

export function Loading() {
  return <p className="text-sm text-slate-500" role="status">Loading…</p>;
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <p className="rounded-md border border-rose-300 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-100" role="alert">
      {message}
    </p>
  );
}

export function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-700">
      <h2 className="text-base font-medium">{title}</h2>
      <p className="mt-2 text-sm text-slate-500">{body}</p>
    </div>
  );
}

export function Planned({ feature }: { feature: string }) {
  return <Empty title={`${feature} is planned`} body="This surface is routed but not live in Phase 1. No connector or agent is claimed live without tests." />;
}

export function Card({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-ink-900">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
