import { ChatWindow } from "@/components/chat/ChatWindow";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">DocuChat</h1>
        <p className="text-sm text-muted-foreground">
          Chat with any site&apos;s docs — config-driven, no hardcoded domain.
        </p>
      </div>
      <ChatWindow />
    </main>
  );
}
