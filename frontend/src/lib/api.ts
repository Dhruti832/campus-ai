export interface Source {
  url: string;
  title: string;
  category: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
}

export class ChatApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ChatApiError";
    this.status = status;
  }
}

function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

export async function sendChatMessage(query: string): Promise<ChatResponse> {
  const response = await fetch(`${getApiBaseUrl()}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    throw new ChatApiError(`Chat request failed with status ${response.status}`, response.status);
  }

  return (await response.json()) as ChatResponse;
}
