import { useEffect, useState, type ChangeEvent } from "react";
import { endpoints } from "../lib/api/client";
import { ErrorNote, Loading } from "../ui/States";

export function ProfilePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [us, setUs] = useState(false);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    skills: "python, fastapi, rag, langchain",
    target_titles: "GenAI Engineer, Backend Engineer",
    preferred_cities: "Bengaluru, Hyderabad, remote",
    work_mode: "hybrid",
    min_ctc_inr_annual: "2500000",
    expected_ctc_inr_annual: "3500000",
    notice_period_days: "60",
    employment_types: "full-time",
    company_preference: "either",
    deal_breakers: "",
    title_aliases: "GenAI Engineer, LLM Engineer",
    banned_companies: "",
    banned_roles: "",
    min_ctc_inr_monthly: "",
    years_experience: "6",
    seniority: "mid",
    verified_facts: "metric: Built RAG evaluation at current employer\nskill: python\nskill: rag",
  });
  useEffect(() => {
    endpoints.profile().then((r) => {
      setUs(r.feature_us_market);
      const p = r.profile;
      if (p) {
        setForm((f) => ({
          ...f,
          full_name: String(p.full_name || ""),
          email: String(p.email || ""),
          skills: ((p.skills as string[]) || []).join(", "),
          target_titles: ((p.target_titles as string[]) || []).join(", "),
          preferred_cities: ((p.preferred_cities as string[]) || []).join(", "),
          work_mode: String(p.work_mode || "hybrid"),
          min_ctc_inr_annual: String(p.min_ctc_inr_annual || ""),
          expected_ctc_inr_annual: String(p.expected_ctc_inr_annual || ""),
          notice_period_days: String(p.notice_period_days || ""),
          employment_types: ((p.employment_types as string[]) || []).join(", "),
          company_preference: String(p.company_preference || "either"),
          deal_breakers: ((p.deal_breakers as string[]) || []).join(", "),
          years_experience: String(p.years_experience || ""),
          seniority: String(p.seniority || ""),
          verified_facts: (r.verified_facts as { kind: string; value: string }[] || []).map((f) => `${f.kind}: ${f.value}`).join("\n") || "",
          title_aliases: ((p.title_aliases as string[]) || []).join(", "),
          banned_companies: ((p.banned_companies as string[]) || []).join(", "),
          banned_roles: ((p.banned_roles as string[]) || []).join(", "),
        }));
      }
      setLoading(false);
    }).catch((e) => {
      setError(String(e));
      setLoading(false);
    });
  }, []);
  const set = (k: keyof typeof form) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value });
  if (loading) return <Loading />;
  return (
    <form
      className="mx-auto max-w-3xl space-y-3"
      onSubmit={async (e) => {
        e.preventDefault();
        try {
          await endpoints.saveProfile({
            ...form,
            skills: form.skills.split(",").map((s) => s.trim()).filter(Boolean),
            target_titles: form.target_titles.split(",").map((s) => s.trim()).filter(Boolean),
            preferred_cities: form.preferred_cities.split(",").map((s) => s.trim()).filter(Boolean),
            employment_types: form.employment_types.split(",").map((s) => s.trim()).filter(Boolean),
            deal_breakers: form.deal_breakers.split(",").map((s) => s.trim()).filter(Boolean),
            title_aliases: form.title_aliases.split(",").map((s) => s.trim()).filter(Boolean),
            banned_companies: form.banned_companies.split(",").map((s) => s.trim()).filter(Boolean),
            banned_roles: form.banned_roles.split(",").map((s) => s.trim()).filter(Boolean),
            min_ctc_inr_annual: Number(form.min_ctc_inr_annual) || null,
            min_ctc_inr_monthly: Number(form.min_ctc_inr_monthly) || null,
            expected_ctc_inr_annual: Number(form.expected_ctc_inr_annual) || null,
            notice_period_days: Number(form.notice_period_days) || null,
            years_experience: Number(form.years_experience) || null,
            verified_facts: form.verified_facts.split("\n").map((s) => s.trim()).filter(Boolean).map((line) => {
              const idx = line.indexOf(":");
              if (idx === -1) return { kind: "other", value: line };
              return { kind: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() };
            }),
            trigger_rematch: true,
          });
          setError("");
        } catch (err) {
          setError(String(err));
        }
      }}
    >
      <h1 className="text-2xl font-semibold">Profile and settings</h1>
      {error ? <ErrorNote message={error} /> : null}
      {Object.entries({
        full_name: "Full name",
        email: "Email",
        skills: "Skills",
        target_titles: "Target titles",
        preferred_cities: "Preferred Indian cities",
        min_ctc_inr_annual: "Minimum CTC (INR annual)",
        expected_ctc_inr_annual: "Expected CTC (INR annual)",
        notice_period_days: "Notice period (days)",
        years_experience: "Years of experience",
        seniority: "Seniority",
      }).map(([k, label]) => (
        <label key={k} className="block text-sm">{label}
          <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" value={form[k as keyof typeof form]} onChange={set(k as keyof typeof form)} />
        </label>
      ))}
      <label className="block text-sm">Work mode
        <select className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" value={form.work_mode} onChange={set("work_mode")}>
          <option>remote</option><option>hybrid</option><option>onsite</option>
        </select>
      </label>
      <label className="block text-sm">Employment type
        <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" value={form.employment_types} onChange={set("employment_types")} />
      </label>
      <label className="block text-sm">Company preference
        <select className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" value={form.company_preference} onChange={set("company_preference")}>
          <option>startup</option><option>enterprise</option><option>either</option>
        </select>
      </label>
      <label className="block text-sm">Title aliases
        <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" value={form.title_aliases} onChange={set("title_aliases")} />
      </label>
      <label className="block text-sm">Min CTC (INR monthly, optional)
        <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" value={form.min_ctc_inr_monthly} onChange={set("min_ctc_inr_monthly")} />
      </label>
      <label className="block text-sm">Deal-breakers
        <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" value={form.deal_breakers} onChange={set("deal_breakers")} />
      </label>
      <label className="block text-sm">Banned companies
        <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" value={form.banned_companies} onChange={set("banned_companies")} />
      </label>
      <label className="block text-sm">Verified facts (kind: value per line)
        <textarea className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-700 dark:bg-ink-800" rows={4} value={form.verified_facts} onChange={set("verified_facts")} />
      </label>
      <p className="text-xs text-slate-500">Saving enqueues a rematch job so Ganesha/Arjuna re-score existing captures.</p>
      {us ? <p className="text-sm">US sponsorship fields enabled by feature flag.</p> : <p className="text-sm text-slate-500">H-1B / US sponsorship is hidden (FEATURE_US_MARKET=false).</p>}
      <div className="flex flex-wrap gap-2">
        <button type="submit" className="rounded-md bg-amber-700 px-4 py-2 text-white">Save profile</button>
        <button type="button" className="rounded-md border px-4 py-2 text-sm" onClick={() => endpoints.exportProfile()}>Export data</button>
        <button type="button" className="rounded-md border px-4 py-2 text-sm" onClick={() => endpoints.deleteProfile()}>Delete data</button>
      </div>
      <p className="text-sm text-slate-500">Notifications and billing settings: in-app prefs on API; billing is planned.</p>
    </form>
  );
}
