import { AppHeader } from "@/components/AppHeader";
import { ChatWindow } from "@/components/chat/ChatWindow";

export default function Home() {
  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <AppHeader />

      <main className="relative flex flex-1 overflow-hidden">
        <div className="bg-grid-fade pointer-events-none absolute inset-0" aria-hidden="true" />
        {/* Kept for accessibility/SEO (a page needs a heading) without
            spending visual space on marketing copy in what's meant to be
            a full-height chat surface, not a landing page. */}
        <h1 className="sr-only">Chat with any site&apos;s docs</h1>
        <div className="relative flex w-full flex-1">
          <ChatWindow />
        </div>
      </main>
    </div>
  );
}
