import { Bot, Pin, ThumbsDown, ThumbsUp, User } from "lucide-react";

import { cn } from "@/lib/utils";

import { MarkdownContent } from "./MarkdownContent";
import { SourceCitations } from "./SourceCitations";
import type { ChatMessage } from "./types";

interface MessageBubbleProps {
  message: ChatMessage;
  onTogglePin?: (id: string) => void;
  onFeedback?: (id: string, rating: 1 | -1) => void;
}

export function MessageBubble({ message, onTogglePin, onFeedback }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "group flex animate-fade-in-up items-end gap-2",
        isUser ? "flex-row-reverse" : ""
      )}
    >
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
        )}
        aria-hidden="true"
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
      </div>
      <div
        className={cn(
          "relative max-w-[78%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed shadow-sm",
          isUser
            ? "rounded-br-sm bg-primary text-primary-foreground"
            : "rounded-bl-sm bg-muted text-foreground"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.text}</p>
        ) : (
          <MarkdownContent text={message.text} />
        )}
        {!isUser && message.sources && <SourceCitations sources={message.sources} />}
        {!isUser && onFeedback && (
          <div className="mt-1.5 flex items-center gap-0.5">
            <button
              type="button"
              onClick={() => onFeedback(message.id, 1)}
              disabled={Boolean(message.feedback)}
              aria-label="Good response"
              aria-pressed={message.feedback === 1}
              className={cn(
                "rounded-full p-1 transition-opacity disabled:cursor-default",
                message.feedback === 1
                  ? "text-emerald-500 opacity-100"
                  : message.feedback
                    ? "text-muted-foreground opacity-30"
                    : "text-muted-foreground opacity-0 hover:text-foreground group-hover:opacity-100 focus-visible:opacity-100"
              )}
            >
              <ThumbsUp className={cn("h-3 w-3", message.feedback === 1 && "fill-current")} />
            </button>
            <button
              type="button"
              onClick={() => onFeedback(message.id, -1)}
              disabled={Boolean(message.feedback)}
              aria-label="Bad response"
              aria-pressed={message.feedback === -1}
              className={cn(
                "rounded-full p-1 transition-opacity disabled:cursor-default",
                message.feedback === -1
                  ? "text-red-500 opacity-100"
                  : message.feedback
                    ? "text-muted-foreground opacity-30"
                    : "text-muted-foreground opacity-0 hover:text-foreground group-hover:opacity-100 focus-visible:opacity-100"
              )}
            >
              <ThumbsDown className={cn("h-3 w-3", message.feedback === -1 && "fill-current")} />
            </button>
          </div>
        )}
      </div>
      {onTogglePin && (
        <button
          type="button"
          onClick={() => onTogglePin(message.id)}
          aria-label={message.pinned ? "Unpin message" : "Pin message"}
          aria-pressed={Boolean(message.pinned)}
          className={cn(
            "shrink-0 rounded-full p-1 transition-opacity",
            message.pinned
              ? "text-primary opacity-100"
              : "text-muted-foreground opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
          )}
        >
          <Pin className={cn("h-3.5 w-3.5", message.pinned && "fill-current")} />
        </button>
      )}
    </div>
  );
}
