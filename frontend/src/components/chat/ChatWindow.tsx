"use client";

import { useState } from "react";

import { Card } from "@/components/ui/card";
import { ChatApiError, sendChatMessage } from "@/lib/api";

import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";
import type { ChatMessage } from "./types";

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSend(query: string) {
    setError(null);
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text: query }]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(query);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: response.answer,
          sources: response.sources,
        },
      ]);
    } catch (err) {
      setError(
        err instanceof ChatApiError
          ? `Something went wrong (status ${err.status}). Please try again.`
          : "Couldn't reach the server. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Card className="flex h-[600px] w-full max-w-2xl flex-col p-4">
      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} isLoading={isLoading} />
      </div>
      {error && (
        <p className="mt-2 text-sm text-red-500" role="alert">
          {error}
        </p>
      )}
      <div className="mt-4">
        <MessageInput onSend={handleSend} disabled={isLoading} />
      </div>
    </Card>
  );
}
