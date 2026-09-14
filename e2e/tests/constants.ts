// Must match ADMIN_API_KEY in .github/workflows/e2e-ci.yml (and whatever
// you export locally — see e2e/README.md).
export const ADMIN_KEY = process.env.E2E_ADMIN_KEY ?? "e2e-admin-key";

// Matches scripts/seed_e2e_fixture.py — the fixture content seeded under
// the "example-docs" corpus so retrieval has something real to find.
export const FIXTURE_ANSWER_SNIPPET = "CampusAI lets you chat with any website's documentation";
export const FIXTURE_SOURCE_TITLE = "Getting Started";
