import { render, screen } from "@testing-library/react";

import { MessageBubble } from "../MessageBubble";

describe("MessageBubble", () => {
  it("renders user message text", () => {
    render(<MessageBubble message={{ id: "1", role: "user", text: "Hi there" }} />);
    expect(screen.getByText("Hi there")).toBeInTheDocument();
  });

  it("renders assistant message with sources", () => {
    render(
      <MessageBubble
        message={{
          id: "2",
          role: "assistant",
          text: "Here's the answer",
          sources: [{ url: "https://x/a", title: "A", category: "General" }],
        }}
      />
    );
    expect(screen.getByText("Here's the answer")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "A" })).toBeInTheDocument();
  });

  it("does not render sources for a user message even if present", () => {
    render(
      <MessageBubble
        message={{
          id: "3",
          role: "user",
          text: "q",
          sources: [{ url: "https://x/a", title: "A", category: "General" }],
        }}
      />
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
