"use client";

import { useEffect, useRef, useState, memo, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { cn } from "@/lib/utils";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Expand,
  X,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Download,
  Maximize2,
} from "lucide-react";
import "katex/dist/katex.min.css";

interface MarkdownProps {
  content: string;
  className?: string;
}

// Modern mermaid theme - clean blues and grays
const mermaidThemeVariables = {
  // Main colors - soft blue palette
  primaryColor: "#e0f2fe", // sky-100
  primaryTextColor: "#0c4a6e", // sky-900
  primaryBorderColor: "#7dd3fc", // sky-300

  // Secondary colors
  secondaryColor: "#f0f9ff", // sky-50
  secondaryTextColor: "#0369a1", // sky-700
  secondaryBorderColor: "#bae6fd", // sky-200

  // Tertiary colors
  tertiaryColor: "#f8fafc", // slate-50
  tertiaryTextColor: "#334155", // slate-700
  tertiaryBorderColor: "#e2e8f0", // slate-200

  // Lines and text
  lineColor: "#64748b", // slate-500
  textColor: "#1e293b", // slate-800

  // Background
  mainBkg: "#ffffff",
  nodeBkg: "#f0f9ff",
  nodeBorder: "#7dd3fc",

  // Cluster/subgraph colors
  clusterBkg: "#f8fafc",
  clusterBorder: "#cbd5e1",

  // Special elements
  edgeLabelBackground: "#ffffff",

  // Font
  fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif",
  fontSize: "14px",
};

// Helper to render mermaid diagram
async function renderMermaidSvg(code: string, id: string): Promise<string> {
  const mermaid = (await import("mermaid")).default;

  mermaid.initialize({
    startOnLoad: false,
    theme: "base",
    securityLevel: "loose",
    fontFamily: mermaidThemeVariables.fontFamily,
    themeVariables: mermaidThemeVariables,
    flowchart: {
      htmlLabels: true,
      curve: "basis",
      padding: 15,
    },
  });

  const { svg } = await mermaid.render(id, code);
  return svg;
}

// Fullscreen Mermaid Viewer Component
const MermaidFullscreenViewer = memo(function MermaidFullscreenViewer({
  code,
  isOpen,
  onClose,
}: {
  code: string;
  isOpen: boolean;
  onClose: () => void;
}) {
  const [svg, setSvg] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    setIsLoading(true);

    const render = async () => {
      try {
        const id = `mermaid-fullscreen-${Math.random().toString(36).substr(2, 9)}`;
        const renderedSvg = await renderMermaidSvg(code, id);
        if (isMounted) {
          setSvg(renderedSvg);
          setIsLoading(false);
          // Reset view when opening
          setScale(1);
          setPosition({ x: 0, y: 0 });
        }
      } catch {
        if (isMounted) setIsLoading(false);
      }
    };

    render();
    return () => {
      isMounted = false;
    };
  }, [code, isOpen]);

  const handleZoomIn = () => setScale((s) => Math.min(s + 0.25, 4));
  const handleZoomOut = () => setScale((s) => Math.max(s - 0.25, 0.1));
  const handleReset = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  // Fit diagram to screen
  const handleFitToScreen = () => {
    if (!containerRef.current || !contentRef.current) return;

    const container = containerRef.current.getBoundingClientRect();
    const content = contentRef.current.getBoundingClientRect();

    // Calculate scale to fit with padding
    const padding = 80;
    const scaleX = (container.width - padding) / (content.width / scale);
    const scaleY = (container.height - padding) / (content.height / scale);
    const newScale = Math.min(scaleX, scaleY, 2); // Cap at 200%

    setScale(Math.max(0.1, newScale));
    setPosition({ x: 0, y: 0 });
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Only left click
    // Don't start drag on double-click
    if (e.detail === 2) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  // Use native wheel event for better control
  useEffect(() => {
    if (!isOpen) return;
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.15 : 0.15;
      setScale((s) => Math.max(0.1, Math.min(4, s + delta)));
    };

    // Small delay to ensure DOM is ready
    const timer = setTimeout(() => {
      container.addEventListener("wheel", handleWheel, { passive: false });
    }, 100);

    return () => {
      clearTimeout(timer);
      container.removeEventListener("wheel", handleWheel);
    };
  }, [isOpen]);

  const handleDoubleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Double-click to zoom in by 50%
    setScale((s) => Math.min(s + 0.5, 4));
  };

  const handleDownload = () => {
    if (!svg) return;
    const blob = new Blob([svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "diagram.svg";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        hideCloseButton
        className="max-w-[95vw] w-[95vw] max-h-[95vh] h-[95vh] p-0 gap-0 overflow-hidden flex flex-col"
      >
        <DialogTitle className="sr-only">Mermaid Diagram Viewer</DialogTitle>
        {/* Toolbar */}
        <div className="flex-shrink-0 flex items-center justify-between px-4 py-2 border-b bg-background/95 backdrop-blur-sm">
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleZoomOut}
              title="Zoom Out (-)"
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-sm text-muted-foreground w-14 text-center tabular-nums font-mono">
              {Math.round(scale * 100)}%
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleZoomIn}
              title="Zoom In (+)"
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
            <div className="w-px h-4 bg-border mx-2" />
            <Button
              variant="ghost"
              size="sm"
              onClick={handleFitToScreen}
              title="Fit to Screen"
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              title="Reset View"
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
            <div className="w-px h-4 bg-border mx-2" />
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDownload}
              title="Download SVG"
            >
              <Download className="h-4 w-4" />
            </Button>
          </div>
          <div className="text-xs text-muted-foreground hidden sm:block">
            Scroll or double-click to zoom • Drag to pan
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            title="Close (Esc)"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Diagram Container - Clean white with subtle dot grid */}
        <div
          ref={containerRef}
          className="flex-1 overflow-hidden cursor-grab active:cursor-grabbing select-none"
          style={{
            backgroundColor: "#ffffff",
            backgroundImage: `radial-gradient(circle, #e2e8f0 1px, transparent 1px)`,
            backgroundSize: "24px 24px",
          }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onDoubleClick={handleDoubleClick}
          onWheelCapture={(e) => {
            e.stopPropagation();
            const delta = e.deltaY > 0 ? -0.15 : 0.15;
            setScale((s) => Math.max(0.1, Math.min(4, s + delta)));
          }}
        >
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="flex items-center gap-2 text-muted-foreground">
                <div className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                Loading diagram...
              </div>
            </div>
          ) : (
            <div
              className="w-full h-full flex items-center justify-center"
              style={{
                transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
                transformOrigin: "center center",
                transition: isDragging ? "none" : "transform 0.15s ease-out",
              }}
            >
              <div
                ref={contentRef}
                className="mermaid-fullscreen-content bg-white rounded-lg shadow-sm p-6"
                style={{
                  boxShadow:
                    "0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.04)",
                }}
                dangerouslySetInnerHTML={{ __html: svg }}
              />
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
});

// Mermaid diagram component - lazy loaded with fullscreen support
const MermaidDiagram = memo(function MermaidDiagram({
  code,
}: {
  code: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const renderDiagram = async () => {
      try {
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
        const renderedSvg = await renderMermaidSvg(code, id);

        if (isMounted) {
          setSvg(renderedSvg);
          setError(null);
          setIsLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(
            err instanceof Error ? err.message : "Failed to render diagram",
          );
          setIsLoading(false);
        }
      }
    };

    renderDiagram();

    return () => {
      isMounted = false;
    };
  }, [code]);

  if (isLoading) {
    return (
      <div className="my-3 p-4 rounded-lg bg-muted/50 text-center text-sm text-muted-foreground">
        Loading diagram...
      </div>
    );
  }

  if (error) {
    return (
      <div className="my-3 p-4 rounded-lg bg-destructive/10 border border-destructive/20">
        <p className="text-sm text-destructive font-medium mb-2">
          Failed to render Mermaid diagram
        </p>
        <pre className="text-xs text-muted-foreground overflow-x-auto">
          {code}
        </pre>
      </div>
    );
  }

  return (
    <>
      <div
        ref={containerRef}
        className="group relative my-3 overflow-x-auto rounded-lg border bg-white p-4 cursor-pointer transition-all hover:border-primary/30 hover:shadow-md"
        onClick={() => setIsFullscreen(true)}
        title="Click to view fullscreen"
      >
        {/* Expand hint */}
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-primary text-primary-foreground shadow-lg text-xs font-medium">
            <Expand className="h-3 w-3" />
            <span>Expand</span>
          </div>
        </div>
        <div dangerouslySetInnerHTML={{ __html: svg }} />
      </div>

      <MermaidFullscreenViewer
        code={code}
        isOpen={isFullscreen}
        onClose={() => setIsFullscreen(false)}
      />
    </>
  );
});

// Detect and fix ASCII tree structures that got flattened (lost newlines)
function preprocessContent(content: string): string {
  // Pattern to detect ASCII tree characters followed by content
  // This catches trees where newlines were converted to spaces
  // Look for patterns like: `├── name │` or `└── name │` or `├── name ├──`
  const treePattern = /([├└│]──?\s+\S+[^│├└]*?)(\s+)([│├└])/g;

  // Check if this looks like a flattened tree (multiple tree chars on same "line")
  const treeCharsCount = (content.match(/[├└│]/g) || []).length;
  const newlineCount = (content.match(/\n/g) || []).length;

  // If we have many tree chars but few newlines, it's likely flattened
  if (treeCharsCount > 5 && treeCharsCount > newlineCount * 2) {
    // Try to restore newlines before tree characters
    let fixed = content;

    // Add newline before tree branch characters (├ └) that follow content
    // But be careful not to break actual code blocks
    if (!content.includes("```")) {
      // Replace space+tree-char with newline+tree-char
      fixed = fixed.replace(/\s+([├└]──)/g, "\n$1");
      // Also handle the vertical bar followed by space and then content
      fixed = fixed.replace(/([│])\s+([│├└]──)/g, "$1\n$2");
    }

    // If we made changes and it looks like a tree, wrap in code block
    if (fixed !== content && fixed.includes("\n├──")) {
      // Find the tree section and wrap it
      const lines = fixed.split("\n");
      let inTree = false;
      let treeStart = -1;
      let treeEnd = -1;

      for (let i = 0; i < lines.length; i++) {
        const hasTreeChar =
          /[├└│]──/.test(lines[i]) || /^[`']?[\/\w].*[│]$/.test(lines[i]);
        if (hasTreeChar && !inTree) {
          inTree = true;
          treeStart = i;
        } else if (!hasTreeChar && inTree && lines[i].trim() !== "") {
          treeEnd = i;
          inTree = false;
        }
      }

      if (treeStart >= 0) {
        if (treeEnd < 0) treeEnd = lines.length;
        // Wrap the tree section in a code block
        const before = lines.slice(0, treeStart).join("\n");
        const tree = lines.slice(treeStart, treeEnd).join("\n");
        const after = lines.slice(treeEnd).join("\n");
        return `${before}\n\`\`\`\n${tree}\n\`\`\`\n${after}`;
      }
    }

    return fixed;
  }

  return content;
}

export function Markdown({ content, className }: MarkdownProps) {
  // Preprocess content to fix common formatting issues
  const processedContent = preprocessContent(content);

  // Memoize the code component to prevent unnecessary re-renders
  const CodeComponent = useCallback(
    ({
      className: codeClassName,
      children,
      ...props
    }: {
      className?: string;
      children?: React.ReactNode;
    }) => {
      const match = /language-(\w+)/.exec(codeClassName || "");
      const isInline = !match && !codeClassName?.includes("language-");

      if (isInline) {
        return (
          <code
            className="px-1.5 py-0.5 rounded bg-muted font-mono text-[0.85em] text-foreground"
            {...props}
          >
            {children}
          </code>
        );
      }

      const language = match ? match[1] : "text";
      const codeString = String(children).replace(/\n$/, "");

      // Handle Mermaid diagrams
      if (language === "mermaid") {
        return <MermaidDiagram code={codeString} />;
      }

      // Block code with syntax highlighting - light theme
      return (
        <SyntaxHighlighter
          style={oneLight}
          language={language}
          PreTag="div"
          customStyle={{
            margin: 0,
            padding: "1rem",
            borderRadius: "0.5rem",
            fontSize: "0.875rem",
            backgroundColor: "#FAFAF8", // Light beige background like screenshots
          }}
        >
          {codeString}
        </SyntaxHighlighter>
      );
    },
    [],
  );

  return (
    <div className={cn("prose prose-sm max-w-none", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // Headings
          h1: ({ children }) => (
            <h1 className="text-xl font-bold mt-4 mb-2 first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-semibold mt-3 mb-2 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-semibold mt-2 mb-1 first:mt-0">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-sm font-semibold mt-2 mb-1 first:mt-0">
              {children}
            </h4>
          ),

          // Paragraphs
          p: ({ children }) => (
            <p className="my-2 first:mt-0 last:mb-0 leading-relaxed">
              {children}
            </p>
          ),

          // Lists
          ul: ({ children }) => (
            <ul className="my-2 ml-4 list-disc space-y-1">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="my-2 ml-4 list-decimal space-y-1">{children}</ol>
          ),
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,

          // Code with syntax highlighting and Mermaid support
          code: CodeComponent,
          pre: ({ children }) => (
            <div className="my-3 overflow-hidden rounded-lg">{children}</div>
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
          em: ({ children }) => <em className="italic">{children}</em>,

          // Horizontal rule
          hr: () => <hr className="my-4 border-border" />,

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
          tbody: ({ children }) => <tbody>{children}</tbody>,
          tr: ({ children }) => (
            <tr className="border-b border-border">{children}</tr>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 text-left font-semibold">{children}</th>
          ),
          td: ({ children }) => <td className="px-3 py-2">{children}</td>,

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
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}
