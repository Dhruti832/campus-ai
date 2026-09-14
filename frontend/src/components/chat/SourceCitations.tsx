import { ExternalLink } from "lucide-react";

import type { Source } from "@/lib/api";

export function SourceCitations({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;

  return (
    <ul className="mt-2.5 flex flex-col gap-1.5 border-t border-border/60 pt-2.5" aria-label="Sources">
      {sources.map((source) => (
        <li key={source.url} className="flex items-center gap-1.5 text-xs">
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-muted-foreground underline decoration-border underline-offset-2 hover:text-foreground hover:decoration-foreground"
          >
            {source.title}
            <ExternalLink className="h-3 w-3" />
          </a>
          <span className="rounded-full bg-background px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
            {source.category}
          </span>
        </li>
      ))}
    </ul>
  );
}
