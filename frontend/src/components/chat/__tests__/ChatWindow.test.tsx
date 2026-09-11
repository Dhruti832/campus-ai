import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ChatApiError, sendChatMessage } from "@/lib/api";

import { ChatWindow } from "../ChatWindow";

jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  sendChatMessage: jest.fn(),
}));

const mockedSendChatMessage = sendChatMessage as jest.MockedFunction<typeof sendChatMessage>;

function typeAndSend(query: string) {
  fireEvent.change(screen.getByLabelText("Message"), { target: { value: query } });
  fireEvent.submit(screen.getByLabelText("Send a message"));
}

describe("ChatWindow", () => {
  afterEach(() => jest.clearAllMocks());

  it("renders the user's message immediately, then the assistant's reply", async () => {
    mockedSendChatMessage.mockResolvedValue({
      answer: "Fees are due in September.",
      sources: [{ url: "https://x/fees", title: "Fees", category: "Fees" }],
    });

    render(<ChatWindow />);
    typeAndSend("when are fees due");

    expect(screen.getByText("when are fees due")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Fees are due in September.")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: "Fees" })).toBeInTheDocument();
  });

  it("shows the thinking indicator while the request is in flight", async () => {
    let resolvePromise: (value: { answer: string; sources: never[] }) => void = () => {};
    mockedSendChatMessage.mockReturnValue(
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

  it("shows an error message with the status code on a ChatApiError", async () => {
    mockedSendChatMessage.mockRejectedValue(new ChatApiError("boom", 429));

    render(<ChatWindow />);
    typeAndSend("hello");

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("status 429");
    });
  });

  it("shows a generic error message for a non-ChatApiError failure", async () => {
    mockedSendChatMessage.mockRejectedValue(new Error("network down"));

    render(<ChatWindow />);
    typeAndSend("hello");

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/couldn't reach the server/i);
    });
  });

  it("disables the input while a request is in flight", async () => {
    mockedSendChatMessage.mockReturnValue(new Promise(() => {}));

    render(<ChatWindow />);
    typeAndSend("hello");

    expect(screen.getByLabelText("Message")).toBeDisabled();
  });
});
