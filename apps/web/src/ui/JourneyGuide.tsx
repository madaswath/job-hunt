import { Link } from "react-router-dom";
import { Card } from "./States";

const STEPS = [
  { to: "/settings", label: "1. Profile", body: "Save DS+AI titles, skills, cities, CTC, deal-breakers." },
  { to: "/sources", label: "2. Sources", body: "Gmail alerts, LinkedIn ingest, public ATS — consent and sync." },
  { to: "/discover", label: "3. Refresh", body: "One Demo 1 refresh queues all three sources into your inbox." },
  { to: "/inbox", label: "4. Review", body: "Ruthless ranked matches. Save, reject, or prepare materials." },
  { to: "/documents", label: "5. Apply pack", body: "Approve drafts, then open external apply — you always submit." },
] as const;

export function JourneyGuide() {
  return (
    <Card title="Path from login to apply">
      <ol className="grid gap-3 md:grid-cols-5">
        {STEPS.map((step) => (
          <li key={step.to} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
            <Link className="font-medium text-amber-800 dark:text-amber-200" to={step.to}>
              {step.label}
            </Link>
            <p className="mt-1 text-xs text-slate-500">{step.body}</p>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-xs text-slate-500">We never auto-submit applications or send recruiter mail. Full UX notes: docs/ux-architecture.md</p>
    </Card>
  );
}
