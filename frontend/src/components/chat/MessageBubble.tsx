import { cn } from "@/lib/utils";

import { SourceCitations } from "./SourceCitations";
import type { ChatMessage } from "./types";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] rounded-lg px-3 py-2 text-sm",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
        )}
      >
        <p className="whitespace-pre-wrap">{message.text}</p>
        {!isUser && message.sources && <SourceCitations sources={message.sources} />}
      </div>
    </div>
  );
}
