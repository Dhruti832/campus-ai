import { fireEvent, render, screen } from "@testing-library/react";

import { ConversationSidebar } from "../ConversationSidebar";
import type { Conversation } from "../types";

const conversations: Conversation[] = [
  { id: "a", title: "Older chat", messages: [], updatedAt: 1 },
  { id: "b", title: "Newer chat", messages: [], updatedAt: 2 },
];

describe("ConversationSidebar", () => {
  it("lists conversations newest first", () => {
    render(
      <ConversationSidebar
        conversations={conversations}
        activeId="b"
        onSelect={jest.fn()}
        onNewChat={jest.fn()}
        open={false}
      />
    );

    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Newer chat");
    expect(items[1]).toHaveTextContent("Older chat");
  });

  it("marks the active conversation with aria-current", () => {
    render(
      <ConversationSidebar
        conversations={conversations}
        activeId="a"
        onSelect={jest.fn()}
        onNewChat={jest.fn()}
        open={false}
      />
    );

    expect(screen.getByRole("button", { name: "Older chat" })).toHaveAttribute(
      "aria-current",
      "true"
    );
    expect(screen.getByRole("button", { name: "Newer chat" })).not.toHaveAttribute("aria-current");
  });

  it("calls onSelect with the conversation id when clicked", () => {
    const onSelect = jest.fn();
    render(
      <ConversationSidebar
        conversations={conversations}
        activeId="a"
        onSelect={onSelect}
        onNewChat={jest.fn()}
        open={false}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Newer chat" }));
    expect(onSelect).toHaveBeenCalledWith("b");
  });

  it("calls onNewChat when the New chat button is clicked", () => {
    const onNewChat = jest.fn();
    render(
      <ConversationSidebar
        conversations={conversations}
        activeId="a"
        onSelect={jest.fn()}
        onNewChat={onNewChat}
        open={false}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /new chat/i }));
    expect(onNewChat).toHaveBeenCalled();
  });
});
