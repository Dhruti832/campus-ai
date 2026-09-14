"use client";

import { Menu, Pin } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  ChatApiError,
  getActiveCorpus,
  streamChatMessage,
  submitFeedback,
  type HistoryTurn,
} from "@/lib/api";
import {
  loadActiveConversationId,
  loadConversations,
  saveActiveConversationId,
  saveConversations,
} from "@/lib/conversationStorage";
import { cn } from "@/lib/utils";

import { ConversationSidebar } from "./ConversationSidebar";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";
import type { ChatMessage, Conversation } from "./types";

function deriveTitle(query: string): string {
  const clean = query.trim().replace(/\s+/g, " ");
  return clean.length > 42 ? `${clean.slice(0, 42)}…` : clean;
}

function createConversation(): Conversation {
  return { id: crypto.randomUUID(), title: "New conversation", messages: [], updatedAt: Date.now() };
}

// Mirrors the backend's MAX_HISTORY_TURNS (app/llm/prompt_builder.py) —
// trimmed here too so the request body doesn't grow unbounded as a
// conversation gets long, even though the server re-trims regardless.
const HISTORY_LIMIT = 6;

export function ChatWindow() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showPinnedOnly, setShowPinnedOnly] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [activeCorpusName, setActiveCorpusName] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    getActiveCorpus()
      .then((corpus) => {
        if (!cancelled) setActiveCorpusName(corpus.name);
      })
      .catch(() => {
        // Leave the generic "Live corpus" label if this fails — not
        // worth surfacing as a user-facing error for a display-only label.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let convos = loadConversations();
    let active = loadActiveConversationId();

    if (convos.length === 0) {
      const fresh = createConversation();
      convos = [fresh];
      active = fresh.id;
    }
    if (!active || !convos.some((c) => c.id === active)) {
      active = convos[0].id;
    }

    setConversations(convos);
    setActiveId(active);
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) saveConversations(conversations);
  }, [conversations, hydrated]);

  useEffect(() => {
    if (hydrated) saveActiveConversationId(activeId);
  }, [activeId, hydrated]);

  const activeConversation = conversations.find((c) => c.id === activeId);
  const messages = useMemo(
    () => activeConversation?.messages ?? [],
    [activeConversation]
  );

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isLoading, streamingText]);

  function updateActiveConversation(updater: (conv: Conversation) => Conversation) {
    setConversations((prev) => prev.map((c) => (c.id === activeId ? updater(c) : c)));
  }

  async function handleSend(query: string) {
    setError(null);
    const history: HistoryTurn[] = messages.slice(-HISTORY_LIMIT).map((m) => ({
      role: m.role,
      text: m.text,
    }));
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", text: query };
    updateActiveConversation((conv) => ({
      ...conv,
      messages: [...conv.messages, userMessage],
      title: conv.messages.length === 0 ? deriveTitle(query) : conv.title,
      updatedAt: Date.now(),
    }));
    setIsLoading(true);
    setStreamingText("");

    try {
      const response = await streamChatMessage(
        query,
        (chunk) => {
          setStreamingText((prev) => prev + chunk);
        },
        history
      );
      updateActiveConversation((conv) => ({
        ...conv,
        messages: [
          ...conv.messages,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            text: response.answer,
            sources: response.sources,
          },
        ],
        updatedAt: Date.now(),
      }));
    } catch (err) {
      setError(
        err instanceof ChatApiError
          ? `Something went wrong (status ${err.status}). Please try again.`
          : "Couldn't reach the server. Please try again."
      );
    } finally {
      setIsLoading(false);
      setStreamingText("");
    }
  }

  function handleFeedback(id: string, rating: 1 | -1) {
    const idx = messages.findIndex((m) => m.id === id);
    if (idx === -1 || messages[idx].feedback) return;
    const assistantMessage = messages[idx];
    const precedingUser = messages.slice(0, idx).findLast((m) => m.role === "user");

    updateActiveConversation((conv) => ({
      ...conv,
      messages: conv.messages.map((m) => (m.id === id ? { ...m, feedback: rating } : m)),
    }));
    submitFeedback(precedingUser?.text ?? "", assistantMessage.text, rating).catch(() => {
      // Best-effort signal — not worth surfacing a failed feedback POST to the user.
    });
  }

  function handleTogglePin(id: string) {
    updateActiveConversation((conv) => ({
      ...conv,
      messages: conv.messages.map((message) =>
        message.id === id ? { ...message, pinned: !message.pinned } : message
      ),
    }));
  }

  function handleNewChat() {
    setSidebarOpen(false);
    if (activeConversation && activeConversation.messages.length === 0) return;
    const fresh = createConversation();
    setConversations((prev) => [fresh, ...prev]);
    setActiveId(fresh.id);
    setShowPinnedOnly(false);
  }

  function handleSelectConversation(id: string) {
    setActiveId(id);
    setShowPinnedOnly(false);
    setSidebarOpen(false);
  }

  const pinnedCount = messages.filter((m) => m.pinned).length;
  const visibleMessages = showPinnedOnly ? messages.filter((m) => m.pinned) : messages;

  return (
    <Card className="relative flex h-full min-h-0 w-full flex-1 overflow-hidden rounded-none border-0 shadow-none">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={handleSelectConversation}
        onNewChat={handleNewChat}
        open={sidebarOpen}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 sm:hidden"
              onClick={() => setSidebarOpen((v) => !v)}
              aria-label="Toggle chat history"
              aria-pressed={sidebarOpen}
            >
              <Menu className="h-4 w-4" />
            </Button>
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <span className="text-xs font-medium text-muted-foreground">
              {activeCorpusName ?? "Live corpus"}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {pinnedCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className={cn("gap-1 text-xs", showPinnedOnly && "bg-muted")}
                onClick={() => setShowPinnedOnly((v) => !v)}
                aria-pressed={showPinnedOnly}
              >
                <Pin className="h-3.5 w-3.5" />
                {pinnedCount}
              </Button>
            )}
          </div>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4">
          {showPinnedOnly && visibleMessages.length === 0 ? (
            <p className="pt-8 text-center text-sm text-muted-foreground">
              No pinned messages yet. Pin a reply to find it here later.
            </p>
          ) : (
            <MessageList
              messages={visibleMessages}
              isLoading={isLoading && !showPinnedOnly}
              streamingText={showPinnedOnly ? "" : streamingText}
              onSuggestion={handleSend}
              onTogglePin={handleTogglePin}
              onFeedback={handleFeedback}
            />
          )}
        </div>

        {error && (
          <p className="border-t border-border px-4 py-2 text-sm text-red-500" role="alert">
            {error}
          </p>
        )}

        <div className="border-t border-border p-3">
          <MessageInput onSend={handleSend} disabled={isLoading} />
        </div>
      </div>
    </Card>
  );
}
