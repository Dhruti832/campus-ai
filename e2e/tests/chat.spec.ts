import { expect, test } from "@playwright/test";

import { FIXTURE_ANSWER_SNIPPET, FIXTURE_SOURCE_TITLE } from "./constants";

test.describe("chat", () => {
  test("shows the active corpus and answers using retrieved context", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("example-docs")).toBeVisible();

    await page.getByRole("textbox", { name: "Message" }).fill("How do I get started?");
    await page.getByRole("button", { name: "Send" }).click();

    const log = page.getByRole("log");
    await expect(log.getByText("How do I get started?")).toBeVisible();
    await expect(log.getByText(FIXTURE_ANSWER_SNIPPET)).toBeVisible({ timeout: 15_000 });
    await expect(log.getByRole("link", { name: FIXTURE_SOURCE_TITLE })).toBeVisible();
  });

  test("lets the user pin an assistant reply and filter to pinned messages", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("textbox", { name: "Message" }).fill("How do I get started?");
    await page.getByRole("button", { name: "Send" }).click();

    const log = page.getByRole("log");
    await expect(log.getByText(FIXTURE_ANSWER_SNIPPET)).toBeVisible({ timeout: 15_000 });

    // Both the user's and the assistant's bubbles get a pin button, but the
    // assistant's is only rendered once its reply is fully persisted (not
    // during streaming) — wait for both to exist before picking the last one.
    const pinButtons = page.getByRole("button", { name: "Pin message" });
    await expect(pinButtons).toHaveCount(2);
    await pinButtons.last().click();

    const pinCount = page.getByRole("button", { name: "1" });
    await expect(pinCount).toBeVisible();
    await pinCount.click();

    await expect(log.getByText("How do I get started?")).not.toBeVisible();
    await expect(log.getByText(FIXTURE_ANSWER_SNIPPET)).toBeVisible();
  });

  test("lets the user give feedback on an answer", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("textbox", { name: "Message" }).fill("How do I get started?");
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.getByRole("log").getByText(FIXTURE_ANSWER_SNIPPET)).toBeVisible({
      timeout: 15_000,
    });

    const goodButton = page.getByRole("button", { name: "Good response" });
    await goodButton.click();

    await expect(goodButton).toBeDisabled();
    await expect(goodButton).toHaveAttribute("aria-pressed", "true");
  });
});
