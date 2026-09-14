export interface CorpusStat {
  name: string;
  sources: number;
  chunks: number;
  active: boolean;
  thumbs_up: number;
  thumbs_down: number;
  editable: boolean;
}

export interface CorpusDetail {
  name: string;
  website_url: string;
  persona: string;
  max_pages: number;
}

export interface IngestResult {
  sources_ingested: number;
  chunks_ingested: number;
}

export class AdminApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "AdminApiError";
    this.status = status;
  }
}

function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

async function adminFetch<T>(path: string, apiKey: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": apiKey,
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const message =
      response.status === 403
        ? "Invalid admin key."
        : `Admin request failed with status ${response.status}.`;
    throw new AdminApiError(message, response.status);
  }

  return (await response.json()) as T;
}

export function getCorpusStats(apiKey: string): Promise<CorpusStat[]> {
  return adminFetch<CorpusStat[]>("/admin/corpora", apiKey);
}

export function setActiveCorpus(apiKey: string, corpus: string): Promise<{ active_corpus: string }> {
  return adminFetch("/admin/active-corpus", apiKey, {
    method: "POST",
    body: JSON.stringify({ corpus }),
  });
}

export function triggerIngest(apiKey: string, corpus: string): Promise<IngestResult> {
  return adminFetch<IngestResult>("/admin/ingest", apiKey, {
    method: "POST",
    body: JSON.stringify({ corpus }),
  });
}

export interface CreateCorpusInput {
  name: string;
  websiteUrl: string;
  persona?: string;
  maxPages?: number;
}

export function createCorpus(
  apiKey: string,
  input: CreateCorpusInput
): Promise<{ name: string }> {
  return adminFetch("/admin/corpora", apiKey, {
    method: "POST",
    body: JSON.stringify({
      name: input.name,
      website_url: input.websiteUrl,
      persona: input.persona || undefined,
      max_pages: input.maxPages,
    }),
  });
}

export function deleteCorpus(apiKey: string, name: string): Promise<{ deleted: string }> {
  return adminFetch(`/admin/corpora/${encodeURIComponent(name)}`, apiKey, {
    method: "DELETE",
  });
}

export function getCorpusDetail(apiKey: string, name: string): Promise<CorpusDetail> {
  return adminFetch<CorpusDetail>(`/admin/corpora/${encodeURIComponent(name)}`, apiKey);
}

export interface UpdateCorpusInput {
  websiteUrl?: string;
  persona?: string;
  maxPages?: number;
}

export function updateCorpus(
  apiKey: string,
  name: string,
  input: UpdateCorpusInput
): Promise<{ name: string }> {
  return adminFetch(`/admin/corpora/${encodeURIComponent(name)}`, apiKey, {
    method: "PATCH",
    body: JSON.stringify({
      website_url: input.websiteUrl || undefined,
      persona: input.persona || undefined,
      max_pages: input.maxPages,
    }),
  });
}
