import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { applyTheme } from "../lib/theme";
import { useState } from "react";

const NAV = [
  ["/", "Dashboard"],
  ["/discover", "Discover"],
  ["/inbox", "Review Inbox"],
  ["/applications", "Applications"],
  ["/documents", "Documents"],
  ["/agents", "Agents"],
  ["/sources", "Sources"],
  ["/analytics", "Analytics"],
  ["/settings", "Profile"],
] as const;

export function Shell() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const navigate = useNavigate();

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      <aside
        className={`fixed inset-y-0 left-0 z-20 w-64 border-r border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-ink-900 lg:static lg:block ${open ? "block" : "hidden"}`}
      >
        <p className="mb-6 text-lg font-semibold tracking-tight">Job-hunt</p>
        <nav aria-label="Workspace" className="flex flex-col gap-1">
          {NAV.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm ${isActive ? "bg-amber-50 text-amber-900 dark:bg-amber-950/40 dark:text-amber-100" : "hover:bg-slate-100 dark:hover:bg-ink-800"}`
              }
              onClick={() => setOpen(false)}
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-10 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-ink-900/90">
          <button type="button" className="rounded-md border px-2 py-1 text-sm lg:hidden" onClick={() => setOpen((v) => !v)} aria-label="Toggle navigation">
            Menu
          </button>
          <form
            className="flex flex-1"
            onSubmit={(e) => {
              e.preventDefault();
              navigate(`/discover?q=${encodeURIComponent(q)}`);
            }}
          >
            <label className="sr-only" htmlFor="global-search">
              Search roles
            </label>
            <input
              id="global-search"
              className="w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
              placeholder="Search titles, cities, companies"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </form>
          <button type="button" className="rounded-md border px-2 py-1 text-sm" onClick={() => applyTheme(document.documentElement.classList.contains("dark") ? "light" : "dark")}>
            Theme
          </button>
        </header>
        <main className="p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
