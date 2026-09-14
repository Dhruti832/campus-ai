import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

/**
 * Renders LLM output as markdown (code blocks, lists, bold, links) instead
 * of raw text with literal backticks/asterisks — replies routinely contain
 * fenced code blocks (e.g. deployment commands) that read poorly unstyled.
 */
export function MarkdownContent({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-2 whitespace-pre-wrap last:mb-0">{children}</p>,
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2"
          >
            {children}
          </a>
        ),
        ul: ({ children }) => <ul className="mb-2 ml-4 list-disc last:mb-0">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal last:mb-0">{children}</ol>,
        li: ({ children }) => <li className="mb-0.5">{children}</li>,
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        h1: ({ children }) => (
          <h3 className="mb-1 mt-2 text-base font-semibold first:mt-0">{children}</h3>
        ),
        h2: ({ children }) => (
          <h3 className="mb-1 mt-2 text-base font-semibold first:mt-0">{children}</h3>
        ),
        h3: ({ children }) => (
          <h3 className="mb-1 mt-2 text-sm font-semibold first:mt-0">{children}</h3>
        ),
        pre: ({ children }) => (
          <pre className="my-2 overflow-x-auto rounded-lg bg-background/80 p-3 text-xs">
            {children}
          </pre>
        ),
        code: ({ className, children }) => {
          const isBlock = /language-/.test(className ?? "");
          return (
            <code
              className={cn(
                isBlock ? className : "rounded bg-background/60 px-1 py-0.5 text-[0.85em]"
              )}
            >
              {children}
            </code>
          );
        },
      }}
    >
      {text}
    </ReactMarkdown>
  );
}
