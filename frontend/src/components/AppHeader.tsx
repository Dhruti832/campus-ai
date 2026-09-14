import { MessageSquareText } from "lucide-react";
import Link from "next/link";

import { ThemeToggle } from "@/components/ThemeToggle";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-10 border-b border-border/60 bg-background/80 backdrop-blur-sm">
      <div className="flex w-full items-center justify-between px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <MessageSquareText className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold">CampusAI</span>
        </Link>
        <ThemeToggle />
      </div>
    </header>
  );
}
