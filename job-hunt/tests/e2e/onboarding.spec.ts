import { expect, test } from "@playwright/test";

test("onboarding scan inbox no auto apply", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Continue as test candidate" }).click();
  await expect(page.getByRole("heading", { name: "Today" })).toBeVisible();
  await page.getByRole("link", { name: "Profile" }).click();
  await page.getByRole("button", { name: "Save profile" }).click();
  await page.getByRole("link", { name: "Discover" }).click();
  await page.getByRole("button", { name: "Queue scan" }).click();
  await expect(page.getByText(/Queued/)).toBeVisible();
  await page.getByRole("link", { name: "Review Inbox" }).click();
  await expect(page.getByText("never auto-submit")).toHaveCount(0);
});
