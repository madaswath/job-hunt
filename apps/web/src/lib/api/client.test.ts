import { afterEach, describe, expect, it, vi } from "vitest";
import { getTestToken, resolveAuthToken } from "./client";

describe("resolveAuthToken", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("uses the test token only when Clerk is not configured", async () => {
    localStorage.setItem("jobhunt_test_token", "test-jwt");
    await expect(resolveAuthToken(undefined, false)).resolves.toBe("test-jwt");
    expect(getTestToken()).toBe("test-jwt");
  });

  it("does not call Clerk.getToken when a test token exists but Clerk is disabled", async () => {
    localStorage.setItem("jobhunt_test_token", "test-jwt");
    const getToken = vi.fn(async () => "clerk-jwt");
    await expect(resolveAuthToken({ session: { getToken } }, false)).resolves.toBe("test-jwt");
    expect(getToken).not.toHaveBeenCalled();
  });

  it("uses Clerk session token when Clerk is enabled", async () => {
    localStorage.setItem("jobhunt_test_token", "test-jwt");
    const getToken = vi.fn(async () => "clerk-jwt");
    await expect(resolveAuthToken({ session: { getToken } }, true)).resolves.toBe("clerk-jwt");
    expect(getToken).toHaveBeenCalledOnce();
  });

  it("returns null when Clerk is enabled but there is no session", async () => {
    localStorage.setItem("jobhunt_test_token", "test-jwt");
    await expect(resolveAuthToken(undefined, true)).resolves.toBeNull();
  });
});
