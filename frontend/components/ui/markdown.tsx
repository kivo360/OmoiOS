"use client"

import { useEffect, useRef, useState, memo, useCallback } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"
import rehypeKatex from "rehype-katex"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism"
import { cn } from "@/lib/utils"
import "katex/dist/katex.min.css"

interface MarkdownProps {
  content: string
  className?: string
}

// Mermaid diagram component - lazy loaded
const MermaidDiagram = memo(function MermaidDiagram({ code }: { code: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [svg, setSvg] = useState<string>("")
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let isMounted = true

    const renderDiagram = async () => {
      try {
        // Dynamically import mermaid to reduce bundle size
        const mermaid = (await import("mermaid")).default

        // Initialize mermaid with dark theme support
        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          securityLevel: "loose",
          fontFamily: "inherit",
          themeVariables: {
            primaryColor: "#7c3aed",
            primaryTextColor: "#fff",
            primaryBorderColor: "#5b21b6",
            lineColor: "#6b7280",
            secondaryColor: "#1f2937",
            tertiaryColor: "#374151",
          },
        })

        // Generate unique ID for this diagram
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`

        // Render the diagram
        const { svg: renderedSvg } = await mermaid.render(id, code)

        if (isMounted) {
          setSvg(renderedSvg)
          setError(null)
          setIsLoading(false)
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to render diagram")
          setIsLoading(false)
        }
      }
    }

    renderDiagram()

    return () => {
      isMounted = false
    }
  }, [code])

  if (isLoading) {
    return (
      <div className="my-3 p-4 rounded-lg bg-muted/50 text-center text-sm text-muted-foreground">
        Loading diagram...
      </div>
    )
  }

  if (error) {
    return (
      <div className="my-3 p-4 rounded-lg bg-destructive/10 border border-destructive/20">
        <p className="text-sm text-destructive font-medium mb-2">Failed to render Mermaid diagram</p>
        <pre className="text-xs text-muted-foreground overflow-x-auto">{code}</pre>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="my-3 overflow-x-auto rounded-lg bg-muted/30 p-4"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
})

export function Markdown({ content, className }: MarkdownProps) {
  // Memoize the code component to prevent unnecessary re-renders
  const CodeComponent = useCallback(
    ({ className: codeClassName, children, ...props }: { className?: string; children?: React.ReactNode }) => {
      const match = /language-(\w+)/.exec(codeClassName || "")
      const isInline = !match && !codeClassName?.includes("language-")

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

      const language = match ? match[1] : "text"
      const codeString = String(children).replace(/\n$/, "")

      // Handle Mermaid diagrams
      if (language === "mermaid") {
        return <MermaidDiagram code={codeString} />
      }

      // Block code with syntax highlighting
      return (
        <SyntaxHighlighter
          style={oneDark}
          language={language}
          PreTag="div"
          customStyle={{
            margin: 0,
            padding: "1rem",
            borderRadius: "0.5rem",
            fontSize: "0.875rem",
          }}
        >
          {codeString}
        </SyntaxHighlighter>
      )
    },
    []
  )

  return (
    <div className={cn("prose prose-sm dark:prose-invert max-w-none", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
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

          // Code with syntax highlighting and Mermaid support
          code: CodeComponent,
          pre: ({ children }) => (
            <div className="my-3 overflow-hidden rounded-lg">
              {children}
            </div>
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
