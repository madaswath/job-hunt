import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

/** Serves repo-root plugins/registry.json (Next app root is web/). */
export async function GET() {
  const candidates = [
    join(process.cwd(), "..", "plugins", "registry.json"),
    join(process.cwd(), "plugins", "registry.json"),
  ];
  const path = candidates.find((p) => existsSync(p));
  if (!path) {
    return Response.json({ error: "plugins/registry.json not found" }, { status: 404 });
  }
  const data = JSON.parse(readFileSync(path, "utf8"));
  return Response.json(data);
}
