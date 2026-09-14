import { ShieldCheck } from "lucide-react";

import { AdminPanel } from "@/components/admin/AdminPanel";
import { AppHeader } from "@/components/AppHeader";

export default function AdminPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />

      <main className="flex flex-1 flex-col items-center gap-6 px-4 py-10 sm:px-6">
        <div className="flex w-full max-w-2xl items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">CampusAI Admin</h1>
            <p className="text-sm text-muted-foreground">
              View ingested corpora, add or edit a website, switch which one is active, or
              trigger a re-crawl.
            </p>
          </div>
        </div>
        <div className="w-full max-w-2xl">
          <AdminPanel />
        </div>
      </main>
    </div>
  );
}
