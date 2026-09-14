import { MessageSquare, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import type { Conversation } from "./types";

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  open: boolean;
}

export function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  open,
}: ConversationSidebarProps) {
  const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);

  return (
    <div
      className={cn(
        "absolute inset-y-0 left-0 z-20 flex w-60 shrink-0 flex-col border-r border-border bg-muted/30 transition-transform duration-200 sm:static sm:translate-x-0",
        open ? "translate-x-0" : "-translate-x-full"
      )}
      aria-label="Past chats"
    >
      <div className="border-b border-border p-2">
        <Button variant="ghost" size="sm" className="w-full justify-start gap-2" onClick={onNewChat}>
          <Plus className="h-3.5 w-3.5" />
          New chat
        </Button>
      </div>
      <nav className="flex-1 overflow-y-auto p-2" aria-label="Conversation history">
        <ul className="flex flex-col gap-0.5">
          {sorted.map((conversation) => (
            <li key={conversation.id}>
              <button
                type="button"
                onClick={() => onSelect(conversation.id)}
                aria-current={conversation.id === activeId ? "true" : undefined}
                className={cn(
                  "flex w-full items-center gap-2 truncate rounded-md px-2 py-1.5 text-left text-xs text-muted-foreground transition-colors hover:bg-muted",
                  conversation.id === activeId && "bg-muted font-medium text-foreground"
                )}
              >
                <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{conversation.title}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
