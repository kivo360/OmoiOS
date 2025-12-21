"use client"

import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"

interface MarkdownProps {
  content: string
  className?: string
}

export function Markdown({ content, className }: MarkdownProps) {
  return (
    <div className={cn("prose prose-sm dark:prose-invert max-w-none", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
        // Headings
        h1: ({ children }) => (
          <h1 className="text-xl font-bold mt-4 mb-2 first:mt-0">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-lg font-semibold mt-3 mb-2 first:mt-0">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-base font-semibold mt-2 mb-1 first:mt-0">{children}</h3>
        ),
        h4: ({ children }) => (
          <h4 className="text-sm font-semibold mt-2 mb-1 first:mt-0">{children}</h4>
        ),
        
        // Paragraphs
        p: ({ children }) => (
          <p className="my-2 first:mt-0 last:mb-0 leading-relaxed">{children}</p>
        ),
        
        // Lists
        ul: ({ children }) => (
          <ul className="my-2 ml-4 list-disc space-y-1">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="my-2 ml-4 list-decimal space-y-1">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="leading-relaxed">{children}</li>
        ),
        
        // Code
        code: ({ className, children, ...props }) => {
          const isInline = !className
          if (isInline) {
            return (
              <code 
                className="px-1.5 py-0.5 rounded bg-muted font-mono text-[0.85em] text-foreground"
                {...props}
              >
                {children}
              </code>
            )
          }
          // Block code is handled by pre
          return (
            <code className={cn("font-mono text-sm", className)} {...props}>
              {children}
            </code>
          )
        },
        pre: ({ children }) => (
          <pre className="my-2 p-3 rounded-lg bg-zinc-900 dark:bg-zinc-950 overflow-x-auto text-zinc-100 text-sm">
            {children}
          </pre>
        ),
        
        // Blockquotes
        blockquote: ({ children }) => (
          <blockquote className="my-2 pl-4 border-l-2 border-muted-foreground/30 text-muted-foreground italic">
            {children}
          </blockquote>
        ),
        
        // Links
        a: ({ href, children }) => (
          <a 
            href={href} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-primary underline underline-offset-2 hover:text-primary/80"
          >
            {children}
          </a>
        ),
        
        // Strong/Bold
        strong: ({ children }) => (
          <strong className="font-semibold">{children}</strong>
        ),
        
        // Emphasis/Italic
        em: ({ children }) => (
          <em className="italic">{children}</em>
        ),
        
        // Horizontal rule
        hr: () => (
          <hr className="my-4 border-border" />
        ),
        
        // Tables (GFM)
        table: ({ children }) => (
          <div className="my-2 overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-muted/50">{children}</thead>
        ),
        tbody: ({ children }) => (
          <tbody>{children}</tbody>
        ),
        tr: ({ children }) => (
          <tr className="border-b border-border">{children}</tr>
        ),
        th: ({ children }) => (
          <th className="px-3 py-2 text-left font-semibold">{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2">{children}</td>
        ),
        
        // Task lists (GFM)
        input: ({ checked, ...props }) => (
          <input
            type="checkbox"
            checked={checked}
            readOnly
            className="mr-2 h-4 w-4 rounded border-border"
            {...props}
          />
        ),
        
        // Images
        img: ({ src, alt }) => (
          <img 
            src={src} 
            alt={alt || ""} 
            className="my-2 max-w-full rounded-lg"
          />
        ),
      }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
