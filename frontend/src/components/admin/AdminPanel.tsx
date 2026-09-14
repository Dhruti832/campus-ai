"use client";

import { Database, KeyRound, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  AdminApiError,
  type CorpusStat,
  createCorpus,
  deleteCorpus,
  getCorpusDetail,
  getCorpusStats,
  setActiveCorpus,
  triggerIngest,
  updateCorpus,
} from "@/lib/adminApi";

const STORAGE_KEY = "campus-ai-admin-key";

export function AdminPanel() {
  const [apiKey, setApiKey] = useState("");
  const [keyInput, setKeyInput] = useState("");
  const [stats, setStats] = useState<CorpusStat[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [busyCorpus, setBusyCorpus] = useState<string | null>(null);

  const [showAddForm, setShowAddForm] = useState(false);
  const [addName, setAddName] = useState("");
  const [addUrl, setAddUrl] = useState("");
  const [addPersona, setAddPersona] = useState("");
  const [addMaxPages, setAddMaxPages] = useState("100");
  const [addBusy, setAddBusy] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const [editingCorpus, setEditingCorpus] = useState<string | null>(null);
  const [editUrl, setEditUrl] = useState("");
  const [editPersona, setEditPersona] = useState("");
  const [editMaxPages, setEditMaxPages] = useState("100");
  const [editLoading, setEditLoading] = useState(false);
  const [editBusy, setEditBusy] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  useEffect(() => {
    const saved = window.sessionStorage.getItem(STORAGE_KEY);
    if (saved) {
      setApiKey(saved);
      setKeyInput(saved);
    }
  }, []);

  const loadStats = useCallback(async (key: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getCorpusStats(key);
      setStats(result);
      window.sessionStorage.setItem(STORAGE_KEY, key);
    } catch (err) {
      setStats(null);
      setError(err instanceof AdminApiError ? err.message : "Couldn't reach the server.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (apiKey) void loadStats(apiKey);
  }, [apiKey, loadStats]);

  function handleUnlock(event: React.FormEvent) {
    event.preventDefault();
    setApiKey(keyInput.trim());
  }

  async function handleSetActive(corpus: string) {
    setBusyCorpus(corpus);
    setError(null);
    try {
      await setActiveCorpus(apiKey, corpus);
      await loadStats(apiKey);
    } catch (err) {
      setError(err instanceof AdminApiError ? err.message : "Couldn't reach the server.");
    } finally {
      setBusyCorpus(null);
    }
  }

  async function handleIngest(corpus: string) {
    setBusyCorpus(corpus);
    setError(null);
    try {
      await triggerIngest(apiKey, corpus);
      await loadStats(apiKey);
    } catch (err) {
      setError(err instanceof AdminApiError ? err.message : "Couldn't reach the server.");
    } finally {
      setBusyCorpus(null);
    }
  }

  async function handleDelete(corpus: string) {
    if (!window.confirm(`Delete "${corpus}" and all of its ingested data? This can't be undone.`)) {
      return;
    }
    setBusyCorpus(corpus);
    setError(null);
    try {
      await deleteCorpus(apiKey, corpus);
      await loadStats(apiKey);
    } catch (err) {
      setError(err instanceof AdminApiError ? err.message : "Couldn't reach the server.");
    } finally {
      setBusyCorpus(null);
    }
  }

  async function handleStartEdit(corpus: string) {
    setEditingCorpus(corpus);
    setEditError(null);
    setEditLoading(true);
    setShowAddForm(false);
    try {
      const detail = await getCorpusDetail(apiKey, corpus);
      setEditUrl(detail.website_url);
      setEditPersona(detail.persona);
      setEditMaxPages(String(detail.max_pages));
    } catch (err) {
      setEditError(err instanceof AdminApiError ? err.message : "Couldn't reach the server.");
    } finally {
      setEditLoading(false);
    }
  }

  async function handleSaveEdit(event: React.FormEvent) {
    event.preventDefault();
    if (!editingCorpus) return;
    setEditBusy(true);
    setEditError(null);
    try {
      await updateCorpus(apiKey, editingCorpus, {
        websiteUrl: editUrl.trim(),
        persona: editPersona.trim(),
        maxPages: Number(editMaxPages) || undefined,
      });
      setEditingCorpus(null);
      await loadStats(apiKey);
    } catch (err) {
      setEditError(err instanceof AdminApiError ? err.message : "Couldn't reach the server.");
    } finally {
      setEditBusy(false);
    }
  }

  async function handleAddWebsite(event: React.FormEvent) {
    event.preventDefault();
    setAddBusy(true);
    setAddError(null);
    try {
      const created = await createCorpus(apiKey, {
        name: addName.trim(),
        websiteUrl: addUrl.trim(),
        persona: addPersona.trim(),
        maxPages: Number(addMaxPages) || undefined,
      });
      setAddName("");
      setAddUrl("");
      setAddPersona("");
      setAddMaxPages("100");
      setShowAddForm(false);
      await loadStats(apiKey);
      await handleIngest(created.name);
    } catch (err) {
      setAddError(err instanceof AdminApiError ? err.message : "Couldn't reach the server.");
    } finally {
      setAddBusy(false);
    }
  }

  if (!stats) {
    return (
      <Card className="mx-auto flex w-full max-w-sm animate-fade-in-up flex-col gap-4 rounded-2xl border-border/60 p-6 shadow-xl shadow-black/5">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10">
          <KeyRound className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h2 className="text-base font-semibold">Admin access</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter the admin key to view and manage corpora.
          </p>
        </div>
        <form onSubmit={handleUnlock} className="flex flex-col gap-3">
          <label htmlFor="admin-key" className="sr-only">
            Admin key
          </label>
          <Input
            id="admin-key"
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder="Enter admin key"
            autoFocus
          />
          <Button type="submit" disabled={loading || !keyInput.trim()} className="w-full">
            {loading ? "Checking…" : "Unlock"}
          </Button>
          {error && (
            <p className="text-sm text-red-500" role="alert">
              {error}
            </p>
          )}
        </form>
      </Card>
    );
  }

  return (
    <Card className="flex animate-fade-in-up flex-col gap-4 rounded-2xl border-border/60 p-5 shadow-xl shadow-black/5 sm:p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Corpora</h2>
          <p className="text-xs text-muted-foreground">
            {stats.length} corpus{stats.length === 1 ? "" : "es"} configured
          </p>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => loadStats(apiKey)}
            disabled={loading}
            className="gap-1.5"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Refresh
          </Button>
          <Button
            size="sm"
            className="gap-1.5"
            onClick={() => {
              setShowAddForm((v) => !v);
              setAddError(null);
            }}
          >
            <Plus className="h-3.5 w-3.5" />
            Add website
          </Button>
        </div>
      </div>
      {error && (
        <p className="text-sm text-red-500" role="alert">
          {error}
        </p>
      )}

      {showAddForm && (
        <form
          onSubmit={handleAddWebsite}
          className="flex flex-col gap-3 rounded-xl border border-border/60 bg-muted/30 p-4"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="add-name" className="text-xs font-medium text-muted-foreground">
                Corpus name
              </label>
              <Input
                id="add-name"
                value={addName}
                onChange={(e) => setAddName(e.target.value)}
                placeholder="acme-docs"
                pattern="[a-z0-9][a-z0-9-]{1,48}"
                title="Lowercase letters, digits, and hyphens"
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="add-url" className="text-xs font-medium text-muted-foreground">
                Website URL
              </label>
              <Input
                id="add-url"
                type="url"
                value={addUrl}
                onChange={(e) => setAddUrl(e.target.value)}
                placeholder="https://docs.example.com"
                required
              />
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="add-persona" className="text-xs font-medium text-muted-foreground">
                Persona (optional)
              </label>
              <Input
                id="add-persona"
                value={addPersona}
                onChange={(e) => setAddPersona(e.target.value)}
                placeholder="You are a helpful assistant for Acme's docs."
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="add-max-pages" className="text-xs font-medium text-muted-foreground">
                Max pages
              </label>
              <Input
                id="add-max-pages"
                type="number"
                min={1}
                max={2000}
                value={addMaxPages}
                onChange={(e) => setAddMaxPages(e.target.value)}
                className="w-28"
              />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Crawls same-domain pages reachable from that URL, up to the page limit, and starts
            ingesting right away.
          </p>
          {addError && (
            <p className="text-sm text-red-500" role="alert">
              {addError}
            </p>
          )}
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={addBusy}>
              {addBusy ? "Adding…" : "Add and crawl"}
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setShowAddForm(false)}
              disabled={addBusy}
            >
              Cancel
            </Button>
          </div>
        </form>
      )}

      <div className="flex flex-col gap-2">
        {stats.map((corpus) =>
          editingCorpus === corpus.name ? (
            <form
              key={corpus.name}
              onSubmit={handleSaveEdit}
              className="flex flex-col gap-3 rounded-xl border border-border/60 bg-muted/30 p-4"
            >
              <p className="text-sm font-medium">Editing {corpus.name}</p>
              {editLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
              ) : (
                <>
                  <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
                    <div className="flex flex-col gap-1.5">
                      <label
                        htmlFor="edit-url"
                        className="text-xs font-medium text-muted-foreground"
                      >
                        Website URL
                      </label>
                      <Input
                        id="edit-url"
                        type="url"
                        value={editUrl}
                        onChange={(e) => setEditUrl(e.target.value)}
                        required
                      />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <label
                        htmlFor="edit-max-pages"
                        className="text-xs font-medium text-muted-foreground"
                      >
                        Max pages
                      </label>
                      <Input
                        id="edit-max-pages"
                        type="number"
                        min={1}
                        max={2000}
                        value={editMaxPages}
                        onChange={(e) => setEditMaxPages(e.target.value)}
                        className="w-28"
                      />
                    </div>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label
                      htmlFor="edit-persona"
                      className="text-xs font-medium text-muted-foreground"
                    >
                      Persona
                    </label>
                    <Input
                      id="edit-persona"
                      value={editPersona}
                      onChange={(e) => setEditPersona(e.target.value)}
                    />
                  </div>
                  {editError && (
                    <p className="text-sm text-red-500" role="alert">
                      {editError}
                    </p>
                  )}
                  <div className="flex gap-2">
                    <Button type="submit" size="sm" disabled={editBusy}>
                      {editBusy ? "Saving…" : "Save changes"}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingCorpus(null)}
                      disabled={editBusy}
                    >
                      Cancel
                    </Button>
                  </div>
                </>
              )}
            </form>
          ) : (
            <div
              key={corpus.name}
              className={cn(
                "flex flex-col gap-3 rounded-xl border p-3.5 transition-colors sm:flex-row sm:items-center sm:justify-between",
                corpus.active ? "border-primary/30 bg-primary/[0.03]" : "border-border/60"
              )}
            >
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
                    corpus.active
                      ? "bg-primary/10 text-primary"
                      : "bg-muted text-muted-foreground"
                  )}
                >
                  <Database className="h-4 w-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{corpus.name}</span>
                    {corpus.active && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                        Active
                      </span>
                    )}
                  </div>
                  <p className="text-xs tabular-nums text-muted-foreground">
                    {corpus.sources} source{corpus.sources === 1 ? "" : "s"} · {corpus.chunks}{" "}
                    chunk
                    {corpus.chunks === 1 ? "" : "s"}
                    {(corpus.thumbs_up > 0 || corpus.thumbs_down > 0) && (
                      <>
                        {" "}
                        · 👍 {corpus.thumbs_up} · 👎 {corpus.thumbs_down}
                      </>
                    )}
                  </p>
                </div>
              </div>
              <div className="flex gap-1.5 sm:shrink-0">
                <Button
                  size="sm"
                  variant="ghost"
                  className="gap-1"
                  disabled={corpus.active || busyCorpus === corpus.name}
                  onClick={() => handleSetActive(corpus.name)}
                >
                  Set active
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="gap-1"
                  disabled={busyCorpus === corpus.name}
                  onClick={() => handleIngest(corpus.name)}
                >
                  <RefreshCw
                    className={cn("h-3 w-3", busyCorpus === corpus.name && "animate-spin")}
                  />
                  {busyCorpus === corpus.name ? "Ingesting…" : "Re-ingest"}
                </Button>
                {corpus.editable && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="gap-1"
                    disabled={busyCorpus === corpus.name}
                    onClick={() => handleStartEdit(corpus.name)}
                    aria-label={`Edit ${corpus.name}`}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="ghost"
                  className="gap-1 text-muted-foreground hover:text-red-500"
                  disabled={corpus.active || busyCorpus === corpus.name}
                  onClick={() => handleDelete(corpus.name)}
                  aria-label={`Delete ${corpus.name}`}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          )
        )}
      </div>
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Pencil className="h-3 w-3" />
        Built-in corpora (config/corpora/*.yaml) can&apos;t be deleted here — only ones added
        above.
      </p>
    </Card>
  );
}
