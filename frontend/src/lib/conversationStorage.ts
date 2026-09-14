import type { Conversation } from "@/components/chat/types";

const CONVERSATIONS_KEY = "campus-ai-conversations";
const ACTIVE_ID_KEY = "campus-ai-active-conversation";

export function loadConversations(): Conversation[] {
  try {
    const raw = window.localStorage.getItem(CONVERSATIONS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as Conversation[]) : [];
  } catch {
    return [];
  }
}

export function saveConversations(conversations: Conversation[]): void {
  try {
    window.localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(conversations));
  } catch {
    // Private browsing / storage disabled / quota exceeded — conversations
    // just won't persist across reloads.
  }
}

export function loadActiveConversationId(): string | null {
  try {
    return window.localStorage.getItem(ACTIVE_ID_KEY);
  } catch {
    return null;
  }
}

export function saveActiveConversationId(id: string): void {
  try {
    window.localStorage.setItem(ACTIVE_ID_KEY, id);
  } catch {
    // ignore
  }
}
