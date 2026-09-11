import type { Source } from "@/lib/api";

export function SourceCitations({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;

  return (
    <ul className="mt-2 flex flex-col gap-1 text-xs text-muted-foreground" aria-label="Sources">
      {sources.map((source) => (
        <li key={source.url}>
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-foreground"
          >
            {source.title}
          </a>{" "}
          <span className="rounded bg-muted px-1.5 py-0.5">{source.category}</span>
        </li>
      ))}
    </ul>
  );
}
