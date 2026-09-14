import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import { ChatApiError, getActiveCorpus, streamChatMessage, submitFeedback } from "@/lib/api";

import { ChatWindow } from "../ChatWindow";

jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  streamChatMessage: jest.fn(),
  getActiveCorpus: jest.fn(),
  submitFeedback: jest.fn(),
}));

const mockedStreamChatMessage = streamChatMessage as jest.MockedFunction<typeof streamChatMessage>;
const mockedGetActiveCorpus = getActiveCorpus as jest.MockedFunction<typeof getActiveCorpus>;
const mockedSubmitFeedback = submitFeedback as jest.MockedFunction<typeof submitFeedback>;

function typeAndSend(query: string) {
  fireEvent.change(screen.getByLabelText("Message"), { target: { value: query } });
  fireEvent.submit(screen.getByLabelText("Send a message"));
}

function log() {
  return within(screen.getByRole("log"));
}

describe("ChatWindow", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mockedGetActiveCorpus.mockResolvedValue({ name: "example-docs", description: "" });
    mockedSubmitFeedback.mockResolvedValue(undefined);
  });

  afterEach(() => jest.clearAllMocks());

  it("shows the active corpus name once it loads", async () => {
    mockedGetActiveCorpus.mockResolvedValue({ name: "acme-docs", description: "" });
    render(<ChatWindow />);

    await waitFor(() => expect(screen.getByText("acme-docs")).toBeInTheDocument());
    expect(screen.queryByText("Live corpus")).not.toBeInTheDocument();
  });

  it("falls back to the generic label if the active corpus fails to load", async () => {
    mockedGetActiveCorpus.mockRejectedValue(new Error("network down"));
    render(<ChatWindow />);

    await waitFor(() => expect(screen.getByText("Live corpus")).toBeInTheDocument());
  });

  it("renders the user's message immediately, then the assistant's reply", async () => {
    mockedStreamChatMessage.mockResolvedValue({
      answer: "Fees are due in September.",
      sources: [{ url: "https://x/fees", title: "Fees", category: "Fees" }],
    });

    render(<ChatWindow />);
    typeAndSend("when are fees due");

    expect(log().getByText("when are fees due")).toBeInTheDocument();

    await waitFor(() => {
      expect(log().getByText("Fees are due in September.")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: "Fees" })).toBeInTheDocument();
  });

  it("shows the thinking indicator while the request is in flight", async () => {
    let resolvePromise: (value: { answer: string; sources: never[] }) => void = () => {};
    mockedStreamChatMessage.mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve;
      })
    );

    render(<ChatWindow />);
    typeAndSend("hello");

    expect(screen.getByText(/thinking/i)).toBeInTheDocument();

    resolvePromise({ answer: "hi", sources: [] });
    await waitFor(() => {
      expect(screen.queryByText(/thinking/i)).not.toBeInTheDocument();
    });
  });

  it("renders answer tokens incrementally as they stream in, then settles on the final text", async () => {
    let deliverTokens: (() => void) | undefined;
    mockedStreamChatMessage.mockImplementation(
      (_query, onToken) =>
        new Promise((resolve) => {
          deliverTokens = () => {
            onToken?.("Fees ");
            onToken?.("are due.");
            resolve({ answer: "Fees are due.", sources: [] });
          };
        })
    );

    render(<ChatWindow />);
    typeAndSend("when are fees due");

    expect(screen.getByText(/thinking/i)).toBeInTheDocument();

    await act(async () => {
      deliverTokens?.();
    });
    await waitFor(() => expect(log().getByText("Fees are due.")).toBeInTheDocument());
    expect(screen.queryByText(/thinking/i)).not.toBeInTheDocument();
  });

  it("shows an error message with the status code on a ChatApiError", async () => {
    mockedStreamChatMessage.mockRejectedValue(new ChatApiError("boom", 429));

    render(<ChatWindow />);
    typeAndSend("hello");

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("status 429");
    });
  });

  it("shows a generic error message for a non-ChatApiError failure", async () => {
    mockedStreamChatMessage.mockRejectedValue(new Error("network down"));

    render(<ChatWindow />);
    typeAndSend("hello");

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/couldn't reach the server/i);
    });
  });

  it("disables the input while a request is in flight", async () => {
    mockedStreamChatMessage.mockReturnValue(new Promise(() => {}));

    render(<ChatWindow />);
    typeAndSend("hello");

    expect(screen.getByLabelText("Message")).toBeDisabled();
  });

  describe("conversation persistence", () => {
    it("restores a saved conversation on mount", async () => {
      window.localStorage.setItem(
        "campus-ai-conversations",
        JSON.stringify([
          {
            id: "conv-1",
            title: "previously asked",
            messages: [{ id: "1", role: "user", text: "previously asked" }],
            updatedAt: 1,
          },
        ])
      );

      render(<ChatWindow />);

      await waitFor(() => {
        expect(log().getByText("previously asked")).toBeInTheDocument();
      });
    });

    it("persists new messages across a remount", async () => {
      mockedStreamChatMessage.mockResolvedValue({ answer: "hi there", sources: [] });
      const { unmount } = render(<ChatWindow />);
      typeAndSend("hello");
      await waitFor(() => expect(log().getByText("hi there")).toBeInTheDocument());
      unmount();

      render(<ChatWindow />);
      await waitFor(() => expect(log().getByText("hi there")).toBeInTheDocument());
    });

    it("starts a new, empty conversation when New chat is clicked, keeping the old one in history", async () => {
      mockedStreamChatMessage.mockResolvedValue({ answer: "hi there", sources: [] });
      render(<ChatWindow />);
      typeAndSend("hello");
      await waitFor(() => expect(log().getByText("hi there")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: "New chat" }));

      expect(screen.queryByText("hi there")).not.toBeInTheDocument();

      const stored = JSON.parse(window.localStorage.getItem("campus-ai-conversations") ?? "[]");
      expect(stored).toHaveLength(2);
      expect(screen.getByRole("button", { name: /hello/i })).toBeInTheDocument();
    });

    it("does not create a duplicate conversation when New chat is clicked on an already-empty chat", () => {
      render(<ChatWindow />);

      fireEvent.click(screen.getByRole("button", { name: "New chat" }));

      const stored = JSON.parse(window.localStorage.getItem("campus-ai-conversations") ?? "[]");
      expect(stored).toHaveLength(1);
    });

    it("sends no history on the first message, then the prior turn as history on a follow-up", async () => {
      mockedStreamChatMessage.mockResolvedValue({ answer: "hi there", sources: [] });
      render(<ChatWindow />);
      typeAndSend("first question");
      await waitFor(() => expect(log().getByText("hi there")).toBeInTheDocument());

      expect(mockedStreamChatMessage.mock.calls[0][2]).toEqual([]);

      mockedStreamChatMessage.mockResolvedValue({ answer: "second reply", sources: [] });
      typeAndSend("a follow-up question");
      await waitFor(() => expect(log().getByText("second reply")).toBeInTheDocument());

      expect(mockedStreamChatMessage.mock.calls[1][2]).toEqual([
        { role: "user", text: "first question" },
        { role: "assistant", text: "hi there" },
      ]);
    });

    it("keeps the conversation's title from its first message when a second message is sent", async () => {
      mockedStreamChatMessage.mockResolvedValue({ answer: "hi there", sources: [] });
      render(<ChatWindow />);
      typeAndSend("first question");
      await waitFor(() => expect(log().getByText("hi there")).toBeInTheDocument());

      typeAndSend("a follow-up question");
      await waitFor(() => expect(log().getAllByText("hi there")).toHaveLength(2));

      expect(screen.getByRole("button", { name: /first question/i })).toBeInTheDocument();
    });

    it("truncates long first messages into a short sidebar title", async () => {
      mockedStreamChatMessage.mockResolvedValue({ answer: "ok", sources: [] });
      render(<ChatWindow />);
      const longQuery =
        "This is a very long first message that should be truncated for the sidebar title";
      typeAndSend(longQuery);
      await waitFor(() => expect(log().getByText("ok")).toBeInTheDocument());

      const stored: { title: string }[] = JSON.parse(
        window.localStorage.getItem("campus-ai-conversations") ?? "[]"
      );
      expect(stored[0].title.endsWith("…")).toBe(true);
      expect(stored[0].title.length).toBeLessThan(longQuery.length);
    });

    it("respects a stored active conversation id across a remount", async () => {
      window.localStorage.setItem(
        "campus-ai-conversations",
        JSON.stringify([
          { id: "conv-a", title: "Chat A", messages: [], updatedAt: 1 },
          { id: "conv-b", title: "Chat B", messages: [], updatedAt: 2 },
        ])
      );
      window.localStorage.setItem("campus-ai-active-conversation", "conv-a");

      const { unmount } = render(<ChatWindow />);
      expect(screen.getByRole("button", { name: "Chat A" })).toHaveAttribute(
        "aria-current",
        "true"
      );
      unmount();

      render(<ChatWindow />);
      expect(screen.getByRole("button", { name: "Chat A" })).toHaveAttribute(
        "aria-current",
        "true"
      );
    });

    it("switches between conversations from the sidebar", async () => {
      mockedStreamChatMessage.mockResolvedValue({ answer: "reply one", sources: [] });
      render(<ChatWindow />);
      typeAndSend("first chat question");
      await waitFor(() => expect(log().getByText("reply one")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: "New chat" }));
      mockedStreamChatMessage.mockResolvedValue({ answer: "reply two", sources: [] });
      typeAndSend("second chat question");
      await waitFor(() => expect(log().getByText("reply two")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: /first chat question/i }));

      expect(log().getByText("reply one")).toBeInTheDocument();
      expect(screen.queryByText("reply two")).not.toBeInTheDocument();
    });
  });

  describe("pinning", () => {
    it("shows a pin count button once a message is pinned", async () => {
      mockedStreamChatMessage.mockResolvedValue({ answer: "hi there", sources: [] });
      render(<ChatWindow />);
      typeAndSend("hello");
      await waitFor(() => expect(log().getByText("hi there")).toBeInTheDocument());

      expect(screen.queryByRole("button", { name: "1" })).not.toBeInTheDocument();
      fireEvent.click(screen.getAllByRole("button", { name: "Pin message" })[0]);

      expect(screen.getByRole("button", { name: "1" })).toBeInTheDocument();
    });

    it("filters to only pinned messages when the pin count is clicked", async () => {
      mockedStreamChatMessage.mockResolvedValue({ answer: "hi there", sources: [] });
      render(<ChatWindow />);
      typeAndSend("hello");
      await waitFor(() => expect(log().getByText("hi there")).toBeInTheDocument());
      // Pin only the user's "hello" message (the first pin button).
      fireEvent.click(screen.getAllByRole("button", { name: "Pin message" })[0]);

      fireEvent.click(screen.getByRole("button", { name: "1" }));

      expect(log().getByText("hello")).toBeInTheDocument();
      expect(screen.queryByText("hi there")).not.toBeInTheDocument();
    });
  });

  describe("feedback", () => {
    it("submits the preceding query, the answer, and the rating when a thumb is clicked", async () => {
      mockedStreamChatMessage.mockResolvedValue({ answer: "hi there", sources: [] });
      render(<ChatWindow />);
      typeAndSend("hello");
      await waitFor(() => expect(log().getByText("hi there")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: "Good response" }));

      expect(mockedSubmitFeedback).toHaveBeenCalledWith("hello", "hi there", 1);
    });

    it("disables the buttons after a rating is given", async () => {
      mockedStreamChatMessage.mockResolvedValue({ answer: "hi there", sources: [] });
      render(<ChatWindow />);
      typeAndSend("hello");
      await waitFor(() => expect(log().getByText("hi there")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: "Bad response" }));

      expect(screen.getByRole("button", { name: "Bad response" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Good response" })).toBeDisabled();
    });
  });

  describe("mobile sidebar toggle", () => {
    it("toggles the history sidebar open and closed", () => {
      render(<ChatWindow />);
      const toggle = screen.getByRole("button", { name: "Toggle chat history" });

      expect(toggle).toHaveAttribute("aria-pressed", "false");
      fireEvent.click(toggle);
      expect(toggle).toHaveAttribute("aria-pressed", "true");
    });
  });
});
