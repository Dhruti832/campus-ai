import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DocuChat",
  description: "Chat with any site's docs — config-driven RAG chatbot.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
