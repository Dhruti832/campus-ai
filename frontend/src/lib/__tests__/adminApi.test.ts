import {
  AdminApiError,
  getCorpusDetail,
  getCorpusStats,
  setActiveCorpus,
  triggerIngest,
  updateCorpus,
} from "../adminApi";

describe("adminApi", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  describe("getCorpusStats", () => {
    it("sends the admin key header and returns parsed stats", async () => {
      const mockStats = [{ name: "example-docs", sources: 7, chunks: 20, active: true }];
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockStats,
      }) as unknown as typeof fetch;

      const result = await getCorpusStats("secret");

      expect(result).toEqual(mockStats);
      expect(global.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/admin/corpora",
        expect.objectContaining({
          headers: expect.objectContaining({ "X-Admin-Key": "secret" }),
        })
      );
    });

    it("throws a friendly AdminApiError on 403", async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({}),
      }) as unknown as typeof fetch;

      await expect(getCorpusStats("wrong")).rejects.toMatchObject(
        new AdminApiError("Invalid admin key.", 403)
      );
    });

    it("throws a generic AdminApiError on other failures", async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({}),
      }) as unknown as typeof fetch;

      await expect(getCorpusStats("secret")).rejects.toMatchObject(
        new AdminApiError("Admin request failed with status 500.", 500)
      );
    });
  });

  describe("setActiveCorpus", () => {
    it("posts the corpus name", async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ active_corpus: "example-university" }),
      }) as unknown as typeof fetch;

      const result = await setActiveCorpus("secret", "example-university");

      expect(result).toEqual({ active_corpus: "example-university" });
      const [, init] = (global.fetch as jest.Mock).mock.calls[0];
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual({ corpus: "example-university" });
    });
  });

  describe("triggerIngest", () => {
    it("posts the corpus name and returns ingest counts", async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ sources_ingested: 7, chunks_ingested: 20 }),
      }) as unknown as typeof fetch;

      const result = await triggerIngest("secret", "example-docs");

      expect(result).toEqual({ sources_ingested: 7, chunks_ingested: 20 });
      const [, init] = (global.fetch as jest.Mock).mock.calls[0];
      expect(JSON.parse(init.body)).toEqual({ corpus: "example-docs" });
    });
  });

  describe("getCorpusDetail", () => {
    it("fetches the corpus detail with the admin key header", async () => {
      const detail = {
        name: "acme-docs",
        website_url: "https://docs.acme.com",
        persona: "You are Acme's bot.",
        max_pages: 50,
      };
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => detail,
      }) as unknown as typeof fetch;

      const result = await getCorpusDetail("secret", "acme-docs");

      expect(result).toEqual(detail);
      expect(global.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/admin/corpora/acme-docs",
        expect.objectContaining({
          headers: expect.objectContaining({ "X-Admin-Key": "secret" }),
        })
      );
    });

    it("throws an AdminApiError on 404", async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({}),
      }) as unknown as typeof fetch;

      await expect(getCorpusDetail("secret", "example-docs")).rejects.toBeInstanceOf(
        AdminApiError
      );
    });
  });

  describe("updateCorpus", () => {
    it("sends a PATCH with the changed fields", async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ name: "acme-docs" }),
      }) as unknown as typeof fetch;

      const result = await updateCorpus("secret", "acme-docs", {
        websiteUrl: "https://new.acme.com",
        persona: "New persona.",
        maxPages: 200,
      });

      expect(result).toEqual({ name: "acme-docs" });
      const [url, init] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toBe("http://localhost:8000/admin/corpora/acme-docs");
      expect(init.method).toBe("PATCH");
      expect(JSON.parse(init.body)).toEqual({
        website_url: "https://new.acme.com",
        persona: "New persona.",
        max_pages: 200,
      });
    });
  });
});
