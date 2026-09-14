export interface Source {
  url: string;
  title: string;
  category: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
}

export interface HistoryTurn {
  role: "user" | "assistant";
  text: string;
}

export interface ActiveCorpus {
  name: string;
  description: string;
}

interface StreamEvent {
  type: "token" | "sources";
  text?: string;
  sources?: Source[];
}

export class ChatApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ChatApiError";
    this.status = status;
  }
}

// Render's free tier can OOM-restart the backend on a cold embedding-model
// load (see docs/architecture.md) — a 502/503/504 right after a period of
// inactivity is often transient. Retry a couple of times with backoff
// before surfacing an error, rather than making the user manually resend.
const RETRYABLE_STATUSES = new Set([502, 503, 504]);
const RETRY_DELAYS_MS = [5000, 15000];

function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithRetry(url: string, init: RequestInit): Promise<Response> {
  let lastError: unknown;

  for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt++) {
    try {
      const response = await fetch(url, init);
      if (response.ok || !RETRYABLE_STATUSES.has(response.status)) {
        return response;
      }
      lastError = new ChatApiError(
        `Chat request failed with status ${response.status}`,
        response.status
      );
    } catch (err) {
      lastError = err;
    }

    if (attempt < RETRY_DELAYS_MS.length) {
      await delay(RETRY_DELAYS_MS[attempt]);
    }
  }

  throw lastError;
}

/**
 * Streams a reply from POST /chat/stream (newline-delimited JSON — see
 * routes/chat.py). Calls onToken as each answer chunk arrives and resolves
 * with the full answer + sources once the stream ends.
 */
export async function streamChatMessage(
  query: string,
  onToken?: (chunk: string) => void,
  history?: HistoryTurn[]
): Promise<ChatResponse> {
  const response = await fetchWithRetry(`${getApiBaseUrl()}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, history: history ?? [] }),
  });

  if (!response.ok || !response.body) {
    throw new ChatApiError(`Chat request failed with status ${response.status}`, response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let answer = "";
  let sources: Source[] = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let newlineIndex = buffer.indexOf("\n");
    while (newlineIndex !== -1) {
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      newlineIndex = buffer.indexOf("\n");
      if (!line) continue;

      const event = JSON.parse(line) as StreamEvent;
      if (event.type === "token" && event.text) {
        answer += event.text;
        onToken?.(event.text);
      } else if (event.type === "sources" && event.sources) {
        sources = event.sources;
      }
    }
  }

  return { answer, sources };
}

/** GET /active-corpus — public, no admin key needed. Tells the chat UI
 * which corpus it's actually talking to, since it has no other way to
 * know (it never loads corpus configs itself). */
export async function getActiveCorpus(): Promise<ActiveCorpus> {
  const response = await fetch(`${getApiBaseUrl()}/active-corpus`);
  if (!response.ok) {
    throw new ChatApiError(
      `Failed to load active corpus (status ${response.status})`,
      response.status
    );
  }
  return (await response.json()) as ActiveCorpus;
}

/** POST /feedback — thumbs up/down on one answer. Fire-and-forget from the
 * caller's perspective (the caller decides whether to surface a failure). */
export async function submitFeedback(
  query: string,
  answer: string,
  rating: 1 | -1
): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, answer, rating }),
  });
  if (!response.ok) {
    throw new ChatApiError(
      `Feedback request failed with status ${response.status}`,
      response.status
    );
  }
}
