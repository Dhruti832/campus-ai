import { fireEvent, render, screen } from "@testing-library/react";

import { MessageList } from "../MessageList";

describe("MessageList", () => {
  it("shows an empty-state prompt when there are no messages and not loading", () => {
    render(<MessageList messages={[]} />);
    expect(screen.getByText(/ask a question about the active corpus/i)).toBeInTheDocument();
  });

  it("does not show suggestion chips when onSuggestion is not provided", () => {
    render(<MessageList messages={[]} />);
    expect(screen.queryByText("What is this about?")).not.toBeInTheDocument();
  });

  it("calls onSuggestion with the chip's text when clicked", () => {
    const onSuggestion = jest.fn();
    render(<MessageList messages={[]} onSuggestion={onSuggestion} />);

    fireEvent.click(screen.getByText("What is this about?"));

    expect(onSuggestion).toHaveBeenCalledWith("What is this about?");
  });

  it("renders each message", () => {
    render(
      <MessageList
        messages={[
          { id: "1", role: "user", text: "Hi" },
          { id: "2", role: "assistant", text: "Hello!" },
        ]}
      />
    );
    expect(screen.getByText("Hi")).toBeInTheDocument();
    expect(screen.getByText("Hello!")).toBeInTheDocument();
  });

  it("shows a thinking indicator while loading", () => {
    render(<MessageList messages={[]} isLoading />);
    expect(screen.getByText(/thinking/i)).toBeInTheDocument();
  });

  it("renders the streaming text as a live assistant bubble instead of the thinking indicator", () => {
    render(<MessageList messages={[]} isLoading streamingText="Partial ans" />);
    expect(screen.getByText("Partial ans")).toBeInTheDocument();
    expect(screen.queryByText(/thinking/i)).not.toBeInTheDocument();
  });

  it("does not show the empty state once streaming text starts arriving", () => {
    render(<MessageList messages={[]} streamingText="Partial ans" />);
    expect(screen.queryByText(/ask a question about the active corpus/i)).not.toBeInTheDocument();
  });
});
