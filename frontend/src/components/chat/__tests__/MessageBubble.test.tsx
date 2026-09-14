import { fireEvent, render, screen } from "@testing-library/react";

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

  it("renders markdown in an assistant message (bold, code, links)", () => {
    render(
      <MessageBubble
        message={{
          id: "4",
          role: "assistant",
          text: "Run `fastapi run` to deploy. **Note:** see the [docs](https://x/docs).",
        }}
      />
    );
    expect(screen.getByText("fastapi run")).toBeInTheDocument();
    expect(screen.getByText("fastapi run").tagName).toBe("CODE");
    expect(screen.getByText("Note:").tagName).toBe("STRONG");
    expect(screen.getByRole("link", { name: "docs" })).toHaveAttribute("href", "https://x/docs");
  });

  it("renders a fenced code block in an assistant message", () => {
    render(
      <MessageBubble
        message={{
          id: "5",
          role: "assistant",
          text: "```bash\nfastapi run --host 0.0.0.0\n```",
        }}
      />
    );
    expect(screen.getByText("fastapi run --host 0.0.0.0")).toBeInTheDocument();
  });

  it("does not render markdown syntax literally in a user message", () => {
    render(<MessageBubble message={{ id: "6", role: "user", text: "**not bold**" }} />);
    expect(screen.getByText("**not bold**")).toBeInTheDocument();
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

  it("does not render a pin button when onTogglePin is not provided", () => {
    render(<MessageBubble message={{ id: "1", role: "user", text: "Hi" }} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders an unpressed pin button for an unpinned message", () => {
    render(
      <MessageBubble message={{ id: "1", role: "user", text: "Hi" }} onTogglePin={jest.fn()} />
    );
    expect(screen.getByRole("button", { name: "Pin message" })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
  });

  it("renders a pressed pin button for a pinned message", () => {
    render(
      <MessageBubble
        message={{ id: "1", role: "user", text: "Hi", pinned: true }}
        onTogglePin={jest.fn()}
      />
    );
    expect(screen.getByRole("button", { name: "Unpin message" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
  });

  it("calls onTogglePin with the message id when clicked", () => {
    const onTogglePin = jest.fn();
    render(
      <MessageBubble message={{ id: "abc", role: "user", text: "Hi" }} onTogglePin={onTogglePin} />
    );
    fireEvent.click(screen.getByRole("button", { name: "Pin message" }));
    expect(onTogglePin).toHaveBeenCalledWith("abc");
  });

  it("does not render feedback buttons for a user message even if onFeedback is provided", () => {
    render(
      <MessageBubble message={{ id: "1", role: "user", text: "Hi" }} onFeedback={jest.fn()} />
    );
    expect(screen.queryByRole("button", { name: "Good response" })).not.toBeInTheDocument();
  });

  it("renders feedback buttons for an assistant message when onFeedback is provided", () => {
    render(
      <MessageBubble
        message={{ id: "1", role: "assistant", text: "Hi" }}
        onFeedback={jest.fn()}
      />
    );
    expect(screen.getByRole("button", { name: "Good response" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Bad response" })).toBeInTheDocument();
  });

  it("calls onFeedback with the message id and rating when a thumb is clicked", () => {
    const onFeedback = jest.fn();
    render(
      <MessageBubble
        message={{ id: "abc", role: "assistant", text: "Hi" }}
        onFeedback={onFeedback}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "Good response" }));
    expect(onFeedback).toHaveBeenCalledWith("abc", 1);
  });

  it("disables both feedback buttons once a rating has been given", () => {
    render(
      <MessageBubble
        message={{ id: "abc", role: "assistant", text: "Hi", feedback: 1 }}
        onFeedback={jest.fn()}
      />
    );
    expect(screen.getByRole("button", { name: "Good response" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Bad response" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Good response" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
  });
});
