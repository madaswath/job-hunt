import { describe, expect, it } from "vitest";
import { applyTheme } from "./theme";

describe("theme", () => {
  it("toggles dark class", () => {
    document.documentElement.classList.remove("dark");
    applyTheme("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    applyTheme("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
