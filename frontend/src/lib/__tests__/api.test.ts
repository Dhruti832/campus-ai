import { ChatApiError, getActiveCorpus, streamChatMessage, submitFeedback } from "../api";

function ndjsonResponse(ok: boolean, status: number, events: object[]) {
  const lines = events.map((e) => JSON.stringify(e));
  let index = 0;
  return {
    ok,
    status,
    body: {
      getReader: () => ({
        read: async () => {
          if (index >= lines.length) return { done: true, value: undefined };
          const chunk = new TextEncoder().encode(`${lines[index]}\n`);
          index += 1;
          return { done: false, value: chunk };
        },
      }),
    },
  };
}

describe("streamChatMessage", () => {
  const originalFetch = global.fetch;
  const originalEnv = process.env.NEXT_PUBLIC_API_URL;

  afterEach(() => {
    global.fetch = originalFetch;
    // Assigning `undefined` to a process.env property coerces it to the
    // *string* "undefined" in Node, which would otherwise leak into every
    // later test in this file and defeat streamChatMessage's `?? "http://
    // localhost:8000"` fallback.
    if (originalEnv === undefined) {
      delete process.env.NEXT_PUBLIC_API_URL;
    } else {
      process.env.NEXT_PUBLIC_API_URL = originalEnv;
    }
  });

  it("posts the query to /chat/stream and assembles the answer from token events", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      ndjsonResponse(true, 200, [
        { type: "token", text: "Hi " },
        { type: "token", text: "there" },
        { type: "sources", sources: [{ url: "https://x", title: "X", category: "General" }] },
      ])
    ) as unknown as typeof fetch;

    const result = await streamChatMessage("hello");

    expect(result).toEqual({
      answer: "Hi there",
      sources: [{ url: "https://x", title: "X", category: "General" }],
    });
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/chat/stream",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "hello", history: [] }),
      })
    );
  });

  it("sends the given history turns in the request body", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(ndjsonResponse(true, 200, [])) as unknown as typeof fetch;

    const history = [
      { role: "user" as const, text: "earlier question" },
      { role: "assistant" as const, text: "earlier answer" },
    ];
    await streamChatMessage("follow-up", undefined, history);

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/chat/stream",
      expect.objectContaining({
        body: JSON.stringify({ query: "follow-up", history }),
      })
    );
  });

  it("calls onToken for each token chunk as it arrives", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      ndjsonResponse(true, 200, [
        { type: "token", text: "Hi " },
        { type: "token", text: "there" },
        { type: "sources", sources: [] },
      ])
    ) as unknown as typeof fetch;

    const onToken = jest.fn();
    await streamChatMessage("hello", onToken);

    expect(onToken).toHaveBeenNthCalledWith(1, "Hi ");
    expect(onToken).toHaveBeenNthCalledWith(2, "there");
  });

  it("uses NEXT_PUBLIC_API_URL when set", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.com";
    global.fetch = jest
      .fn()
      .mockResolvedValue(ndjsonResponse(true, 200, [])) as unknown as typeof fetch;

    await streamChatMessage("q");

    expect(global.fetch).toHaveBeenCalledWith(
      "https://api.example.com/chat/stream",
      expect.anything()
    );
  });

  it("ignores blank lines and reassembles a line split across chunk boundaries", async () => {
    const fullLine = `${JSON.stringify({ type: "token", text: "hello" })}\n`;
    const mid = Math.floor(fullLine.length / 2);
    const encoder = new TextEncoder();
    const part1 = encoder.encode(fullLine.slice(0, mid));
    const part2 = encoder.encode(
      `${fullLine.slice(mid)}\n${JSON.stringify({ type: "sources", sources: [] })}\n`
    );
    let call = 0;
    const reader = {
      read: async () => {
        call += 1;
        if (call === 1) return { done: false, value: part1 };
        if (call === 2) return { done: false, value: part2 };
        return { done: true, value: undefined };
      },
    };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: { getReader: () => reader },
    }) as unknown as typeof fetch;

    const result = await streamChatMessage("q");

    expect(result).toEqual({ answer: "hello", sources: [] });
  });

  it("throws ChatApiError with the status code on a non-ok response", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: false, status: 429, body: null }) as unknown as typeof fetch;

    await expect(streamChatMessage("q")).rejects.toMatchObject(
      new ChatApiError("Chat request failed with status 429", 429)
    );
  });

  it("does not retry a non-retryable (4xx) status", async () => {
    const fetchMock = jest.fn().mockResolvedValue({ ok: false, status: 429, body: null });
    global.fetch = fetchMock as unknown as typeof fetch;

    await expect(streamChatMessage("q")).rejects.toBeInstanceOf(ChatApiError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  describe("retrying on transient failures", () => {
    beforeEach(() => jest.useFakeTimers());
    afterEach(() => jest.useRealTimers());

    it("retries after a 502 and succeeds on the second attempt", async () => {
      const fetchMock = jest
        .fn()
        .mockResolvedValueOnce({ ok: false, status: 502, body: null })
        .mockResolvedValueOnce(
          ndjsonResponse(true, 200, [
            { type: "token", text: "hi" },
            { type: "sources", sources: [] },
          ])
        );
      global.fetch = fetchMock as unknown as typeof fetch;

      const promise = streamChatMessage("q");
      await jest.advanceTimersByTimeAsync(5000);
      const result = await promise;

      expect(result).toEqual({ answer: "hi", sources: [] });
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    it("retries on a network error, not just a bad status", async () => {
      const fetchMock = jest
        .fn()
        .mockRejectedValueOnce(new Error("network down"))
        .mockResolvedValueOnce(
          ndjsonResponse(true, 200, [
            { type: "token", text: "hi" },
            { type: "sources", sources: [] },
          ])
        );
      global.fetch = fetchMock as unknown as typeof fetch;

      const promise = streamChatMessage("q");
      await jest.advanceTimersByTimeAsync(5000);
      const result = await promise;

      expect(result).toEqual({ answer: "hi", sources: [] });
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    it("gives up and throws after exhausting all retries", async () => {
      const fetchMock = jest
        .fn()
        .mockResolvedValue({ ok: false, status: 502, body: null });
      global.fetch = fetchMock as unknown as typeof fetch;

      const promise = streamChatMessage("q");
      const expectation = expect(promise).rejects.toMatchObject(
        new ChatApiError("Chat request failed with status 502", 502)
      );
      await jest.advanceTimersByTimeAsync(5000);
      await jest.advanceTimersByTimeAsync(15000);
      await expectation;

      expect(fetchMock).toHaveBeenCalledTimes(3);
    });
  });
});

describe("getActiveCorpus", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("returns the active corpus name and description", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ name: "example-docs", description: "FastAPI's own docs." }),
    }) as unknown as typeof fetch;

    const result = await getActiveCorpus();

    expect(result).toEqual({ name: "example-docs", description: "FastAPI's own docs." });
    expect(global.fetch).toHaveBeenCalledWith("http://localhost:8000/active-corpus");
  });

  it("throws a ChatApiError on a non-ok response", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
    }) as unknown as typeof fetch;

    await expect(getActiveCorpus()).rejects.toBeInstanceOf(ChatApiError);
  });
});

describe("submitFeedback", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("posts the query, answer, and rating to /feedback", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 200 }) as unknown as typeof fetch;

    await submitFeedback("when are fees due", "In September.", 1);

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/feedback",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "when are fees due", answer: "In September.", rating: 1 }),
      })
    );
  });

  it("throws a ChatApiError on a non-ok response", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 }) as unknown as typeof fetch;

    await expect(submitFeedback("q", "a", -1)).rejects.toBeInstanceOf(ChatApiError);
  });
});
