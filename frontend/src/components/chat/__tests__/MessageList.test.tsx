import { render, screen } from "@testing-library/react";

import { MessageList } from "../MessageList";

describe("MessageList", () => {
  it("shows an empty-state prompt when there are no messages and not loading", () => {
    render(<MessageList messages={[]} />);
    expect(screen.getByText(/ask a question about the active corpus/i)).toBeInTheDocument();
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
});
