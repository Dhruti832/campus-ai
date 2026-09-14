import { expect, test } from "@playwright/test";

import { ADMIN_KEY } from "./constants";

test.describe("admin panel", () => {
  test("rejects a wrong key and accepts the real one", async ({ page }) => {
    await page.goto("/admin");

    await page.getByLabel("Admin key").fill("definitely-wrong");
    await page.getByRole("button", { name: "Unlock" }).click();
    await expect(page.getByText("Invalid admin key.")).toBeVisible();

    await page.getByLabel("Admin key").fill(ADMIN_KEY);
    await page.getByRole("button", { name: "Unlock" }).click();
    await expect(page.getByText("example-docs")).toBeVisible();
    await expect(page.getByText("Active", { exact: true })).toBeVisible();
  });

  test("creates, edits, and deletes a website corpus", async ({ page }) => {
    const corpusName = `e2e-${Date.now()}`;

    await page.goto("/admin");
    await page.getByLabel("Admin key").fill(ADMIN_KEY);
    await page.getByRole("button", { name: "Unlock" }).click();
    await expect(page.getByText("example-docs")).toBeVisible();

    // --- Create ---
    await page.getByRole("button", { name: /add website/i }).click();
    await page.getByLabel("Corpus name").fill(corpusName);
    await page.getByLabel("Website URL").fill("https://example.com");
    await page.getByLabel("Persona (optional)").fill("You are a test bot.");
    await page.getByRole("button", { name: "Add and crawl" }).click();

    await expect(page.getByText(corpusName)).toBeVisible({ timeout: 20_000 });

    // --- Edit ---
    await page.getByRole("button", { name: `Edit ${corpusName}` }).click();
    await expect(page.getByLabel("Website URL")).toHaveValue("https://example.com", {
      timeout: 10_000,
    });
    await page.getByLabel("Persona").fill("You are an updated test bot.");
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByLabel("Website URL")).not.toBeVisible();

    // --- Delete ---
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: `Delete ${corpusName}` }).click();
    await expect(page.getByText(corpusName)).not.toBeVisible({ timeout: 10_000 });
  });
});
