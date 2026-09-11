import { ChatApiError, sendChatMessage } from "../api";

describe("sendChatMessage", () => {
  const originalFetch = global.fetch;
  const originalEnv = process.env.NEXT_PUBLIC_API_URL;

  afterEach(() => {
    global.fetch = originalFetch;
    process.env.NEXT_PUBLIC_API_URL = originalEnv;
  });

  it("posts the query and returns the parsed response", async () => {
    const mockResponse = { answer: "Hi there", sources: [] };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    }) as unknown as typeof fetch;

    const result = await sendChatMessage("hello");

    expect(result).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/chat",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "hello" }),
      })
    );
  });

  it("uses NEXT_PUBLIC_API_URL when set", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.com";
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ answer: "ok", sources: [] }),
    }) as unknown as typeof fetch;

    await sendChatMessage("q");

    expect(global.fetch).toHaveBeenCalledWith(
      "https://api.example.com/chat",
      expect.anything()
    );
  });

  it("throws ChatApiError with the status code on a non-ok response", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 429,
      json: async () => ({}),
    }) as unknown as typeof fetch;

    await expect(sendChatMessage("q")).rejects.toMatchObject(
      new ChatApiError("Chat request failed with status 429", 429)
    );
  });
});
