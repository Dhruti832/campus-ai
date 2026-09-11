import { MessageBubble } from "./MessageBubble";
import type { ChatMessage } from "./types";

interface MessageListProps {
  messages: ChatMessage[];
  isLoading?: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  if (messages.length === 0 && !isLoading) {
    return (
      <p className="text-sm text-muted-foreground">
        Ask a question about the active corpus to get started.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3" role="log" aria-live="polite">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {isLoading && (
        <p className="text-sm text-muted-foreground">
          Thinking… first response can take up to a minute if the server was asleep.
        </p>
      )}
    </div>
  );
}
