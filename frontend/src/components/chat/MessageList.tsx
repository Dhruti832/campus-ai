import { Sparkles } from "lucide-react";

import { MessageBubble } from "./MessageBubble";
import type { ChatMessage } from "./types";

const SUGGESTIONS = [
  "What is this about?",
  "Summarize the key points",
  "How do I get started?",
];

interface MessageListProps {
  messages: ChatMessage[];
  isLoading?: boolean;
  streamingText?: string;
  onSuggestion?: (text: string) => void;
  onTogglePin?: (id: string) => void;
  onFeedback?: (id: string, rating: 1 | -1) => void;
}

export function MessageList({
  messages,
  isLoading,
  streamingText,
  onSuggestion,
  onTogglePin,
  onFeedback,
}: MessageListProps) {
  if (messages.length === 0 && !isLoading && !streamingText) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
          <Sparkles className="h-5 w-5 text-muted-foreground" />
        </div>
        <p className="text-sm text-muted-foreground">
          Ask a question about the active corpus to get started.
        </p>
        {onSuggestion && (
          <div className="flex flex-wrap justify-center gap-2">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => onSuggestion(suggestion)}
                className="rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary hover:text-foreground"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4" role="log" aria-live="polite">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          onTogglePin={onTogglePin}
          onFeedback={onFeedback}
        />
      ))}
      {streamingText ? (
        <MessageBubble message={{ id: "__streaming__", role: "assistant", text: streamingText }} />
      ) : (
        isLoading && (
          <div className="flex animate-fade-in-up items-center gap-2 text-sm text-muted-foreground">
            <span className="flex gap-1" aria-hidden="true">
              <span
                className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground"
                style={{ animationDelay: "0ms" }}
              />
              <span
                className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground"
                style={{ animationDelay: "120ms" }}
              />
              <span
                className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground"
                style={{ animationDelay: "240ms" }}
              />
            </span>
            <span>Thinking… first response can take up to a minute if the server was asleep.</span>
          </div>
        )
      )}
    </div>
  );
}
