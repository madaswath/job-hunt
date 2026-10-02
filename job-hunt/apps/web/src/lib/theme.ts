export function applyTheme(theme: "light" | "dark") {
  document.documentElement.classList.toggle("dark", theme === "dark");
  localStorage.setItem("jobhunt_theme", theme);
}

export function initTheme() {
  const stored = localStorage.getItem("jobhunt_theme") as "light" | "dark" | null;
  const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  applyTheme(stored || preferred);
}
