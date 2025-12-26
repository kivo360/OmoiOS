"use client"

import { useState, useMemo } from "react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  Bot,
  User,
  Terminal,
  FileText,
  FileCode,
  FolderOpen,
  Search,
  Globe,
  GitBranch,
  CheckCircle,
  XCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Wrench,
  Brain,
  MessageSquare,
  ListTodo,
  Play,
  AlertCircle,
  Copy,
  Check,
  Sparkles,
  Edit3,
  Plus,
  Minus,
  File,
} from "lucide-react"
import type { SandboxEvent } from "@/lib/api/types"
import { Markdown } from "@/components/ui/markdown"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism"

// Helper to get string value safely
function getString(data: Record<string, unknown>, key: string): string {
  const value = data[key]
  return typeof value === "string" ? value : ""
}

// Helper to get number value safely
function getNumber(data: Record<string, unknown>, key: string): number {
  const value = data[key]
  return typeof value === "number" ? value : 0
}

// Format timestamp
function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
}

// ============================================================================
// Message Card - Agent/User messages
// ============================================================================

interface MessageCardProps {
  content: string
  isUser?: boolean
  isThinking?: boolean
  timestamp?: string
}

function MessageCard({ content, isUser, isThinking, timestamp }: MessageCardProps) {
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
        isUser ? "bg-primary text-primary-foreground" : "bg-muted"
      )}>
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className={cn("flex-1 space-y-1 max-w-[85%]", isUser && "text-right")}>
        <div className={cn(
          "inline-block rounded-lg px-4 py-2.5 text-sm",
          isUser 
            ? "bg-primary text-primary-foreground" 
            : isThinking 
              ? "bg-amber-500/10 border border-amber-500/20 text-foreground"
              : "bg-muted"
        )}>
          {isThinking && (
            <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 text-xs font-medium mb-1">
              <Brain className="h-3 w-3" />
              Thinking
            </div>
          )}
          {isUser ? (
            <span className="whitespace-pre-wrap">{content}</span>
          ) : (
            <Markdown content={content} />
          )}
        </div>
        {timestamp && (
          <p className="text-[10px] text-muted-foreground px-1">{timestamp}</p>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// File Write Card - Cursor-style file diff display with syntax highlighting
// ============================================================================

// Map file extensions to Prism language names
const extensionToLanguage: Record<string, string> = {
  py: "python",
  js: "javascript",
  jsx: "jsx",
  ts: "typescript",
  tsx: "tsx",
  rs: "rust",
  go: "go",
  rb: "ruby",
  java: "java",
  c: "c",
  cpp: "cpp",
  cs: "csharp",
  php: "php",
  swift: "swift",
  kt: "kotlin",
  scala: "scala",
  sql: "sql",
  sh: "bash",
  bash: "bash",
  zsh: "bash",
  json: "json",
  yaml: "yaml",
  yml: "yaml",
  xml: "xml",
  html: "html",
  css: "css",
  scss: "scss",
  less: "less",
  md: "markdown",
  dockerfile: "docker",
  makefile: "makefile",
  toml: "toml",
  ini: "ini",
  env: "bash",
  gitignore: "git",
}

function getLanguageFromPath(filePath: string): string {
  const fileName = filePath.split("/").pop()?.toLowerCase() || ""
  const ext = fileName.split(".").pop()?.toLowerCase() || ""
  
  // Handle special filenames
  if (fileName === "dockerfile") return "docker"
  if (fileName === "makefile") return "makefile"
  if (fileName.startsWith(".env")) return "bash"
  
  return extensionToLanguage[ext] || "text"
}

// Parse unified diff into structured lines
interface DiffLine {
  type: "addition" | "deletion" | "context" | "header"
  content: string
  oldLineNum?: number
  newLineNum?: number
}

function parseDiff(diffText: string): { lines: DiffLine[]; addedCount: number; removedCount: number } {
  const rawLines = diffText.split("\n")
  const lines: DiffLine[] = []
  let oldLine = 0
  let newLine = 0
  let addedCount = 0
  let removedCount = 0
  
  for (const line of rawLines) {
    // Skip diff metadata headers
    if (line.startsWith("---") || line.startsWith("+++") || line.startsWith("diff ")) {
      continue
    }
    
    // Parse hunk headers to get line numbers
    if (line.startsWith("@@")) {
      const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/)
      if (match) {
        oldLine = parseInt(match[1], 10)
        newLine = parseInt(match[2], 10)
      }
      continue // Skip the @@ line itself
    }
    
    if (line.startsWith("+")) {
      lines.push({
        type: "addition",
        content: line.slice(1),
        newLineNum: newLine++,
      })
      addedCount++
    } else if (line.startsWith("-")) {
      lines.push({
        type: "deletion",
        content: line.slice(1),
        oldLineNum: oldLine++,
      })
      removedCount++
    } else if (line.startsWith(" ") || line === "") {
      lines.push({
        type: "context",
        content: line.startsWith(" ") ? line.slice(1) : line,
        oldLineNum: oldLine++,
        newLineNum: newLine++,
      })
    }
  }
  
  return { lines, addedCount, removedCount }
}

interface FileWriteCardProps {
  filePath: string
  content?: string
  diff?: string
  linesAdded?: number
  linesRemoved?: number
  changeType?: "created" | "modified" | "deleted"
  timestamp?: string
}

function FileWriteCard({ 
  filePath, 
  content, 
  diff, 
  linesAdded = 0, 
  linesRemoved = 0,
  changeType = "modified",
  timestamp 
}: FileWriteCardProps) {
  const [expanded, setExpanded] = useState(true)
  const [showFullContent, setShowFullContent] = useState(false)
  const [copied, setCopied] = useState(false)

  const language = getLanguageFromPath(filePath)
  const fileName = filePath.split("/").pop() || filePath
  const isNewFile = changeType === "created" || !diff
  
  // Parse the content
  const parsedData = useMemo(() => {
    if (diff) {
      return parseDiff(diff)
    }
    // For new files, just split content into lines
    const contentLines = content?.split("\n") || []
    return {
      lines: contentLines.map((line, idx) => ({
        type: "addition" as const,
        content: line,
        newLineNum: idx + 1,
      })),
      addedCount: contentLines.length,
      removedCount: 0,
    }
  }, [diff, content])

  const { lines } = parsedData
  const actualAdded = linesAdded || parsedData.addedCount
  const actualRemoved = linesRemoved || parsedData.removedCount
  
  // Limit displayed lines
  const maxLines = 25
  const displayLines = showFullContent ? lines : lines.slice(0, maxLines)
  const hasMoreLines = lines.length > maxLines

  const actionLabel = changeType === "created" ? "Created" : changeType === "deleted" ? "Deleted" : "Modified"
  const ActionIcon = changeType === "created" ? Plus : changeType === "deleted" ? Minus : Edit3

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    const textToCopy = content || lines.map(l => l.content).join("\n")
    navigator.clipboard.writeText(textToCopy)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Get file icon based on extension
  const getFileIcon = () => {
    if (language === "python") return "🐍"
    if (language === "javascript" || language === "typescript") return "📜"
    if (language === "jsx" || language === "tsx") return "⚛️"
    if (language === "rust") return "🦀"
    if (language === "go") return "🐹"
    if (language === "docker") return "🐳"
    if (language === "json" || language === "yaml") return "📋"
    if (language === "markdown") return "📝"
    if (language === "html" || language === "css") return "🎨"
    return null
  }

  const fileIcon = getFileIcon()

  return (
    <div className="rounded-lg border border-border overflow-hidden bg-card">
      {/* Header */}
      <div 
        className="flex items-center gap-2 px-3 py-2.5 bg-zinc-900 dark:bg-zinc-950 cursor-pointer hover:bg-zinc-800 dark:hover:bg-zinc-900 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <ActionIcon className={cn(
          "h-4 w-4 shrink-0",
          changeType === "created" ? "text-green-500" : 
          changeType === "deleted" ? "text-red-500" : "text-amber-500"
        )} />
        
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          {fileIcon && <span className="text-sm">{fileIcon}</span>}
          <span className="text-sm font-medium text-zinc-100 truncate">
            {fileName}
          </span>
          <span className="text-xs text-zinc-500 truncate hidden sm:inline">
            {filePath !== fileName && filePath.replace(fileName, "").replace(/\/$/, "")}
          </span>
        </div>
        
        {/* Stats */}
        <div className="flex items-center gap-2 shrink-0">
          {(actualAdded > 0 || actualRemoved > 0) && (
            <div className="flex items-center gap-1 text-xs font-mono">
              {actualAdded > 0 && (
                <span className="text-green-400">+{actualAdded}</span>
              )}
              {actualRemoved > 0 && (
                <span className="text-red-400">-{actualRemoved}</span>
              )}
            </div>
          )}
          
          {/* Copy button */}
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-6 w-6 p-0 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700"
            onClick={handleCopy}
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
          
          {timestamp && (
            <span className="text-[10px] text-zinc-500 hidden sm:inline">{timestamp}</span>
          )}
          
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-zinc-500 shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-zinc-500 shrink-0" />
          )}
        </div>
      </div>

      {/* Code Content */}
      {expanded && lines.length > 0 && (
        <div className="border-t border-zinc-800">
          <div className="overflow-x-auto">
            {isNewFile ? (
              // For new files, use full syntax highlighting
              <SyntaxHighlighter
                language={language}
                style={oneDark}
                showLineNumbers
                customStyle={{
                  margin: 0,
                  padding: "0.75rem 0",
                  fontSize: "0.75rem",
                  background: "#18181b",
                  borderRadius: 0,
                }}
                lineNumberStyle={{
                  minWidth: "3rem",
                  paddingRight: "1rem",
                  color: "#52525b",
                  textAlign: "right",
                }}
                wrapLines
                lineProps={() => ({
                  style: { 
                    display: "block",
                    backgroundColor: "rgba(34, 197, 94, 0.08)",
                  },
                })}
              >
                {(showFullContent ? lines : lines.slice(0, maxLines)).map(l => l.content).join("\n")}
              </SyntaxHighlighter>
            ) : (
              // For diffs, show line-by-line with colors
              <table className="w-full text-xs">
                <tbody>
                  {displayLines.map((line, idx) => (
                    <tr 
                      key={idx}
                      className={cn(
                        line.type === "addition" ? "bg-green-500/10" : "",
                        line.type === "deletion" ? "bg-red-500/10" : "",
                      )}
                    >
                      {/* Line numbers */}
                      <td className="w-10 px-2 py-0.5 text-right text-zinc-600 select-none border-r border-zinc-800 bg-zinc-900/50 font-mono">
                        {line.type !== "addition" ? line.oldLineNum : ""}
                      </td>
                      <td className="w-10 px-2 py-0.5 text-right text-zinc-600 select-none border-r border-zinc-800 bg-zinc-900/50 font-mono">
                        {line.type !== "deletion" ? line.newLineNum : ""}
                      </td>
                      
                      {/* Change indicator */}
                      <td className="w-6 px-1 py-0.5 text-center select-none font-mono">
                        {line.type === "addition" && (
                          <span className="text-green-400">+</span>
                        )}
                        {line.type === "deletion" && (
                          <span className="text-red-400">-</span>
                        )}
                      </td>
                      
                      {/* Code content with syntax highlighting */}
                      <td className="py-0.5 pr-4">
                        <SyntaxHighlighter
                          language={language}
                          style={oneDark}
                          customStyle={{
                            margin: 0,
                            padding: 0,
                            background: "transparent",
                            fontSize: "0.75rem",
                          }}
                          codeTagProps={{
                            style: {
                              color: line.type === "addition" 
                                ? "#86efac" 
                                : line.type === "deletion" 
                                  ? "#fca5a5" 
                                  : undefined,
                            }
                          }}
                        >
                          {line.content || " "}
                        </SyntaxHighlighter>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          
          {/* Show more button */}
          {hasMoreLines && !showFullContent && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                setShowFullContent(true)
              }}
              className="w-full py-2 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors border-t border-zinc-800"
            >
              Show all ({lines.length - maxLines} more lines)
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Glob Card - Tree-style file listing display
// ============================================================================

interface GlobOutput {
  filenames: string[]
  durationMs: number
  numFiles: number
  truncated: boolean
}

interface FileTreeNode {
  name: string
  path: string
  isFile: boolean
  children: Map<string, FileTreeNode>
}

function parseGlobOutput(output: string): GlobOutput | null {
  if (!output) return null

  try {
    // Handle Python dict format with single quotes
    const jsonLike = output
      .replace(/'/g, '"')
      .replace(/True/g, 'true')
      .replace(/False/g, 'false')
    return JSON.parse(jsonLike)
  } catch {
    // Try standard JSON
    try {
      return JSON.parse(output)
    } catch {
      return null
    }
  }
}

function buildFileTree(filenames: string[]): FileTreeNode {
  const root: FileTreeNode = { name: "", path: "", isFile: false, children: new Map() }

  for (const filepath of filenames) {
    const parts = filepath.split("/").filter(Boolean)
    let current = root
    let currentPath = ""

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      currentPath = currentPath ? `${currentPath}/${part}` : part
      const isFile = i === parts.length - 1

      if (!current.children.has(part)) {
        current.children.set(part, {
          name: part,
          path: currentPath,
          isFile,
          children: new Map(),
        })
      }
      current = current.children.get(part)!
    }
  }

  return root
}

interface GlobCardProps {
  pattern: string
  output?: string
  status?: "running" | "completed" | "error"
  timestamp?: string
}

function GlobCard({ pattern, output, status = "completed", timestamp }: GlobCardProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  const parsed = output ? parseGlobOutput(output) : null
  const filenames = parsed?.filenames || []
  const numFiles = parsed?.numFiles ?? filenames.length
  const durationMs = parsed?.durationMs
  const truncated = parsed?.truncated || false

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(filenames.join("\n"))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Build file tree for display
  const fileTree = buildFileTree(filenames)

  // Render tree recursively
  const renderTree = (node: FileTreeNode, depth: number = 0, isLast: boolean = true, prefix: string = ""): React.ReactNode[] => {
    const result: React.ReactNode[] = []
    const children = Array.from(node.children.values()).sort((a, b) => {
      // Directories first, then files
      if (a.isFile !== b.isFile) return a.isFile ? 1 : -1
      return a.name.localeCompare(b.name)
    })

    children.forEach((child, index) => {
      const isLastChild = index === children.length - 1
      const connector = isLastChild ? "└── " : "├── "
      const childPrefix = prefix + (isLastChild ? "    " : "│   ")

      result.push(
        <div
          key={child.path}
          className={cn(
            "flex items-center gap-1 hover:bg-muted/50 rounded px-1 -mx-1",
            child.isFile ? "text-foreground" : "text-cyan-500 font-medium"
          )}
        >
          <span className="text-muted-foreground font-mono select-none whitespace-pre">{prefix}{connector}</span>
          {child.isFile ? (
            <File className="h-3 w-3 shrink-0 text-muted-foreground" />
          ) : (
            <FolderOpen className="h-3 w-3 shrink-0" />
          )}
          <span className="truncate">{child.name}{!child.isFile && "/"}</span>
        </div>
      )

      if (!child.isFile && child.children.size > 0) {
        result.push(...renderTree(child, depth + 1, isLastChild, childPrefix))
      }
    })

    return result
  }

  // For empty results or running state
  const isEmpty = numFiles === 0 && status !== "running"

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="rounded-lg border bg-card overflow-hidden">
        <CollapsibleTrigger asChild>
          <button className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/50 transition-colors">
            <FolderOpen className="h-4 w-4 shrink-0 text-cyan-500" />
            <span className="font-medium text-sm">Glob</span>
            {status === "running" ? (
              <Badge variant="secondary" className="text-[10px] h-5">
                <Play className="h-2.5 w-2.5 mr-1 animate-pulse" />
                Running
              </Badge>
            ) : (
              <Badge
                variant={isEmpty ? "secondary" : "default"}
                className={cn(
                  "text-[10px] h-5",
                  !isEmpty && "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/20"
                )}
              >
                {numFiles} file{numFiles !== 1 ? "s" : ""}
                {truncated && "+"}
              </Badge>
            )}
            <span className="flex-1 text-xs text-muted-foreground font-mono truncate">
              {pattern}
            </span>
            {durationMs !== undefined && (
              <span className="text-[10px] text-muted-foreground shrink-0">
                {durationMs}ms
              </span>
            )}
            {timestamp && (
              <span className="text-[10px] text-muted-foreground shrink-0">{timestamp}</span>
            )}
            {isOpen ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
            )}
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="border-t px-3 py-2 bg-muted/30">
            {isEmpty ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                <Search className="h-4 w-4" />
                <span>No files found</span>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                    Results
                  </span>
                  <Button variant="ghost" size="sm" className="h-5 px-1.5" onClick={handleCopy}>
                    {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                  </Button>
                </div>
                <div className="text-xs font-mono max-h-64 overflow-y-auto space-y-0.5">
                  {renderTree(fileTree)}
                </div>
                {truncated && (
                  <div className="mt-2 text-xs text-amber-500 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    Results truncated
                  </div>
                )}
              </>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

// ============================================================================
// Tool Card - Collapsible tool usage display
// ============================================================================

interface ToolCardProps {
  tool: string
  input: Record<string, unknown>
  output?: string
  status?: "running" | "completed" | "error"
  timestamp?: string
}

function ToolCard({ tool, input, output, status = "completed", timestamp }: ToolCardProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  const toolConfig: Record<string, { icon: typeof Wrench; label: string; color: string }> = {
    Read: { icon: FileText, label: "Read", color: "text-blue-500" },
    Write: { icon: FileCode, label: "Write", color: "text-green-500" },
    Edit: { icon: Edit3, label: "Edit", color: "text-amber-500" },
    Bash: { icon: Terminal, label: "Bash", color: "text-purple-500" },
    Glob: { icon: FolderOpen, label: "Glob", color: "text-cyan-500" },
    Grep: { icon: Search, label: "Grep", color: "text-orange-500" },
    WebFetch: { icon: Globe, label: "WebFetch", color: "text-indigo-500" },
    Task: { icon: GitBranch, label: "Task", color: "text-pink-500" },
    TodoWrite: { icon: ListTodo, label: "TodoWrite", color: "text-emerald-500" },
    TodoRead: { icon: ListTodo, label: "TodoRead", color: "text-emerald-500" },
    default: { icon: Wrench, label: tool, color: "text-muted-foreground" },
  }

  const config = toolConfig[tool] || toolConfig.default
  const Icon = config.icon

  // Get summary based on tool type
  const getSummary = (): string => {
    if (tool === "Read" || tool === "Write" || tool === "Edit") {
      return getString(input, "filePath") || getString(input, "file_path") || ""
    }
    if (tool === "Bash") {
      const cmd = getString(input, "command")
      return cmd.length > 60 ? cmd.slice(0, 60) + "..." : cmd
    }
    if (tool === "Glob") return getString(input, "pattern")
    if (tool === "Grep") return getString(input, "pattern")
    if (tool === "WebFetch") return getString(input, "url")
    if (tool === "Task") return getString(input, "description")
    return ""
  }

  const summary = getSummary()

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(JSON.stringify(input, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="rounded-lg border bg-card overflow-hidden">
        <CollapsibleTrigger asChild>
          <button className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/50 transition-colors">
            <Icon className={cn("h-4 w-4 shrink-0", config.color)} />
            <span className="font-medium text-sm">{config.label}</span>
            {status === "running" && (
              <Badge variant="secondary" className="text-[10px] h-5">
                <Play className="h-2.5 w-2.5 mr-1 animate-pulse" />
                Running
              </Badge>
            )}
            <span className="flex-1 text-xs text-muted-foreground font-mono truncate">
              {summary}
            </span>
            {timestamp && (
              <span className="text-[10px] text-muted-foreground shrink-0">{timestamp}</span>
            )}
            {isOpen ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
            )}
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="border-t px-3 py-2 space-y-2 bg-muted/30">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Input</span>
              <Button variant="ghost" size="sm" className="h-5 px-1.5" onClick={handleCopy}>
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              </Button>
            </div>
            <pre className="text-xs bg-background rounded p-2 overflow-x-auto max-h-40 overflow-y-auto font-mono border">
              {JSON.stringify(input, null, 2)}
            </pre>
            {output && (
              <>
                <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Output</span>
                <pre className="text-xs bg-background rounded p-2 overflow-x-auto max-h-40 overflow-y-auto font-mono border">
                  {output}
                </pre>
              </>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

// ============================================================================
// Todo Card - Task list display
// ============================================================================

interface TodoCardProps {
  todos: Array<{ content: string; status: string; priority?: string; id?: string }>
  timestamp?: string
}

function TodoCard({ todos, timestamp }: TodoCardProps) {
  const statusConfig = {
    completed: { icon: CheckCircle, color: "text-green-500", bg: "bg-green-500/10" },
    in_progress: { icon: Play, color: "text-blue-500", bg: "bg-blue-500/10" },
    pending: { icon: Clock, color: "text-muted-foreground", bg: "" },
    cancelled: { icon: XCircle, color: "text-red-500", bg: "bg-red-500/10" },
  }

  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 bg-muted/50">
        <ListTodo className="h-4 w-4 text-emerald-500" />
        <span className="font-medium text-sm">Todo List</span>
        <span className="text-xs text-muted-foreground">
          {todos.filter(t => t.status === "completed").length}/{todos.length} completed
        </span>
        {timestamp && (
          <span className="text-[10px] text-muted-foreground ml-auto">{timestamp}</span>
        )}
      </div>
      <div className="p-2 space-y-1">
        {todos.map((todo, i) => {
          const config = statusConfig[todo.status as keyof typeof statusConfig] || statusConfig.pending
          const StatusIcon = config.icon
          return (
            <div 
              key={todo.id || i} 
              className={cn(
                "flex items-start gap-2 px-2 py-1.5 rounded text-sm",
                config.bg
              )}
            >
              <StatusIcon className={cn("h-4 w-4 mt-0.5 shrink-0", config.color)} />
              <span className={cn(
                "flex-1",
                todo.status === "completed" && "line-through text-muted-foreground"
              )}>
                {todo.content}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================================
// Bash Command Card - Clean terminal-style display
// ============================================================================

interface BashCardProps {
  command: string
  output?: string
  exitCode?: number
  timestamp?: string
}

// Parse Bash output which may be JSON with stdout/stderr fields
function parseBashOutput(output: string): { stdout: string; stderr: string; exitCode?: number } {
  if (!output) return { stdout: "", stderr: "" }

  // Try to parse as JSON first (standard tool response format)
  try {
    const parsed = JSON.parse(output)
    if (typeof parsed === "object" && parsed !== null) {
      return {
        stdout: parsed.stdout || parsed.output || "",
        stderr: parsed.stderr || parsed.error || "",
        exitCode: parsed.exit_code ?? parsed.exitCode,
      }
    }
  } catch {
    // Not valid JSON, try Python dict format
  }

  // Handle Python dict format: {'stdout': '...', 'stderr': '...', 'interrupted': False, 'isImage': False}
  // Use regex to extract the field values directly instead of trying to convert to JSON
  if (output.startsWith("{") && (output.includes("'stdout'") || output.includes('"stdout"'))) {
    try {
      // Extract stdout value - handle both single and double quoted strings
      // Match 'stdout': "..." or 'stdout': '...' or "stdout": "..."
      const stdoutMatch = output.match(/['"]stdout['"]\s*:\s*(['"])([\s\S]*?)(?<!\\)\1\s*[,}]/)
      const stderrMatch = output.match(/['"]stderr['"]\s*:\s*(['"])([\s\S]*?)(?<!\\)\1\s*[,}]/)
      const exitCodeMatch = output.match(/['"](?:exit_code|exitCode)['"]\s*:\s*(\d+)/)

      // If we found stdout, extract it
      if (stdoutMatch) {
        const stdout = stdoutMatch[2]
          // Unescape common escape sequences
          .replace(/\\n/g, "\n")
          .replace(/\\t/g, "\t")
          .replace(/\\r/g, "\r")
          .replace(/\\\\/g, "\\")
          .replace(/\\'/g, "'")
          .replace(/\\"/g, '"')

        const stderr = stderrMatch ? stderrMatch[2]
          .replace(/\\n/g, "\n")
          .replace(/\\t/g, "\t")
          .replace(/\\r/g, "\r")
          .replace(/\\\\/g, "\\")
          .replace(/\\'/g, "'")
          .replace(/\\"/g, '"')
        : ""

        return {
          stdout,
          stderr,
          exitCode: exitCodeMatch ? parseInt(exitCodeMatch[1], 10) : undefined,
        }
      }
    } catch {
      // Regex failed, fall through to raw output
    }
  }

  return { stdout: output, stderr: "" }
}

function BashCard({ command, output, exitCode: providedExitCode, timestamp }: BashCardProps) {
  const [expanded, setExpanded] = useState(true)
  const [copied, setCopied] = useState(false)
  
  // Parse the output
  const { stdout, stderr, exitCode: parsedExitCode } = parseBashOutput(output || "")
  const exitCode = providedExitCode ?? parsedExitCode
  const hasOutput = stdout || stderr
  const isError = (exitCode !== undefined && exitCode !== 0) || !!stderr

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(stdout || output || "")
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="rounded-lg border border-zinc-800 overflow-hidden bg-zinc-900">
      {/* Header */}
      <div 
        className="flex items-center gap-2 px-3 py-2 bg-zinc-800/50 cursor-pointer hover:bg-zinc-800 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <Terminal className="h-4 w-4 text-purple-400 shrink-0" />
        <span className="font-medium text-sm text-zinc-100">Terminal</span>
        {isError && (
          <Badge variant="destructive" className="text-[10px] h-5">
            {stderr ? "Error" : `Exit ${exitCode}`}
          </Badge>
        )}
        <code className="flex-1 text-xs text-zinc-400 font-mono truncate">
          {command.length > 50 ? command.slice(0, 50) + "..." : command}
        </code>
        
        {hasOutput && (
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-6 w-6 p-0 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700"
            onClick={handleCopy}
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
        )}
        
        {timestamp && (
          <span className="text-[10px] text-zinc-500">{timestamp}</span>
        )}
        {hasOutput && (
          expanded ? (
            <ChevronDown className="h-4 w-4 text-zinc-500 shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-zinc-500 shrink-0" />
          )
        )}
      </div>
      
      {/* Terminal content */}
      {expanded && (
        <div className="border-t border-zinc-800">
          {/* Command line */}
          <div className="px-4 py-2 flex items-start gap-2">
            <span className="text-green-400 font-mono text-xs select-none">$</span>
            <code className="text-xs text-zinc-100 font-mono whitespace-pre-wrap break-all">
              {command}
            </code>
          </div>
          
          {/* Output */}
          {stdout && (
            <div className="px-4 pb-3">
              <pre className="text-xs text-zinc-300 font-mono whitespace-pre-wrap break-words overflow-x-auto max-h-48 overflow-y-auto">
                {stdout}
              </pre>
            </div>
          )}
          
          {/* Stderr */}
          {stderr && (
            <div className="px-4 pb-3">
              <pre className="text-xs text-red-400 font-mono whitespace-pre-wrap break-words overflow-x-auto max-h-32 overflow-y-auto">
                {stderr}
              </pre>
            </div>
          )}
          
          {/* No output message */}
          {!stdout && !stderr && (
            <div className="px-4 pb-3">
              <span className="text-xs text-zinc-500 italic">Command completed with no output</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// System Event Card - Status messages
// ============================================================================

interface SystemEventCardProps {
  eventType: string
  message?: string
  timestamp?: string
}

function SystemEventCard({ eventType, message, timestamp }: SystemEventCardProps) {
  const isStart = eventType.includes("start") || eventType.includes("STARTED")
  const isComplete = eventType.includes("complete") || eventType.includes("COMPLETED")
  const isError = eventType.includes("error") || eventType.includes("ERROR")

  const label = message || eventType.replace(/_/g, " ").replace(/\./g, " ").replace(/agent /i, "")

  return (
    <div className={cn(
      "flex items-center justify-center gap-2 py-2 text-xs rounded-lg",
      isError ? "bg-red-500/10 text-red-600 dark:text-red-400" : 
      isComplete ? "bg-green-500/10 text-green-600 dark:text-green-400" : 
      "text-muted-foreground"
    )}>
      {isError ? (
        <AlertCircle className="h-3.5 w-3.5" />
      ) : isComplete ? (
        <CheckCircle className="h-3.5 w-3.5" />
      ) : isStart ? (
        <Sparkles className="h-3.5 w-3.5" />
      ) : (
        <Clock className="h-3.5 w-3.5" />
      )}
      <span className="capitalize">{label}</span>
      {timestamp && <span className="opacity-70">• {timestamp}</span>}
    </div>
  )
}

// ============================================================================
// Main EventRenderer Component
// ============================================================================

interface EventRendererProps {
  event: SandboxEvent
  className?: string
}

export function EventRenderer({ event, className }: EventRendererProps) {
  const { event_type, event_data, created_at } = event
  const timestamp = formatTime(created_at)
  const data = event_data as Record<string, unknown>

  // Agent messages
  if (event_type === "agent.message" || event_type === "agent.assistant_message") {
    const content = getString(data, "content")
    if (!content) return null
    return <div className={className}><MessageCard content={content} timestamp={timestamp} /></div>
  }

  // Agent thinking
  if (event_type === "agent.thinking") {
    const content = getString(data, "content")
    if (!content) return null
    return <div className={className}><MessageCard content={content} isThinking timestamp={timestamp} /></div>
  }

  // User messages
  if (event_type === "agent.user_message" || event_type === "SANDBOX_MESSAGE_QUEUED" || event_type === "agent.message_injected") {
    const content = getString(data, "content") || getString(data, "message")
    if (!content) return null
    return <div className={className}><MessageCard content={content} isUser timestamp={timestamp} /></div>
  }

  // Tool completed - special handling for different tools
  if (event_type === "agent.tool_completed") {
    const tool = getString(data, "tool")
    const toolInput = (data.tool_input || {}) as Record<string, unknown>
    const toolResponse = getString(data, "tool_response")

    // Write tool - show full file content
    if (tool === "Write") {
      const filePath = getString(toolInput, "filePath") || getString(toolInput, "file_path") || ""
      const content = getString(toolInput, "content") || ""
      return (
        <div className={className}>
          <FileWriteCard 
            filePath={filePath}
            content={content}
            changeType="created"
            timestamp={timestamp}
          />
        </div>
      )
    }
    
    // Edit tool - construct a diff from oldString/newString
    if (tool === "Edit") {
      const filePath = getString(toolInput, "filePath") || getString(toolInput, "file_path") || ""
      const oldString = getString(toolInput, "oldString") || ""
      const newString = getString(toolInput, "newString") || ""
      
      // Create a simple unified diff format
      const oldLines = oldString.split("\n")
      const newLines = newString.split("\n")
      const diffLines: string[] = []
      
      // Add deletions (old lines)
      for (const line of oldLines) {
        diffLines.push(`-${line}`)
      }
      // Add additions (new lines)
      for (const line of newLines) {
        diffLines.push(`+${line}`)
      }
      
      return (
        <div className={className}>
          <FileWriteCard 
            filePath={filePath}
            diff={diffLines.join("\n")}
            linesAdded={newLines.length}
            linesRemoved={oldLines.length}
            changeType="modified"
            timestamp={timestamp}
          />
        </div>
      )
    }

    // Bash tool
    if (tool === "Bash") {
      const command = getString(toolInput, "command")
      return (
        <div className={className}>
          <BashCard
            command={command}
            output={toolResponse}
            timestamp={timestamp}
          />
        </div>
      )
    }

    // Glob tool - tree-style file listing
    if (tool === "Glob") {
      const pattern = getString(toolInput, "pattern")
      return (
        <div className={className}>
          <GlobCard
            pattern={pattern}
            output={toolResponse}
            timestamp={timestamp}
          />
        </div>
      )
    }

    // TodoWrite tool
    if (tool === "TodoWrite" && toolInput.todos) {
      const todos = toolInput.todos as Array<{ content: string; status: string }>
      return <div className={className}><TodoCard todos={todos} timestamp={timestamp} /></div>
    }

    // Default tool card
    return (
      <div className={className}>
        <ToolCard tool={tool} input={toolInput} output={toolResponse} timestamp={timestamp} />
      </div>
    )
  }

  // Tool use (in progress)
  if (event_type === "agent.tool_use") {
    const tool = getString(data, "tool")
    const toolInput = (data.tool_input || data.input || {}) as Record<string, unknown>

    // Glob tool - show running state with GlobCard
    if (tool === "Glob") {
      const pattern = getString(toolInput, "pattern")
      return (
        <div className={className}>
          <GlobCard
            pattern={pattern}
            status="running"
            timestamp={timestamp}
          />
        </div>
      )
    }

    return (
      <div className={className}>
        <ToolCard tool={tool} input={toolInput} status="running" timestamp={timestamp} />
      </div>
    )
  }

  // Tool result - show as compact inline result
  if (event_type === "agent.user_tool_result") {
    const result = getString(data, "result")
    // Skip trivial results, empty results, or very long results (likely file contents)
    if (!result || result.length < 10 || result.length > 500) return null
    
    // Skip results that look like file snippets (from Edit tool)
    if (result.includes("The file") && result.includes("has been")) return null
    
    return (
      <div className={className}>
        <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
          <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm text-emerald-600 dark:text-emerald-400">Result</span>
              <span className="text-[10px] text-muted-foreground">{timestamp}</span>
            </div>
            <p className="text-sm text-foreground mt-1 font-mono whitespace-pre-wrap break-words">
              {result}
            </p>
          </div>
        </div>
      </div>
    )
  }

  // File edits (from file_edited events)
  if (event_type === "agent.file_edited") {
    const filePath = getString(data, "file_path")
    const changeType = (getString(data, "change_type") || "modified") as "created" | "modified" | "deleted"
    const linesAdded = getNumber(data, "lines_added")
    const linesRemoved = getNumber(data, "lines_removed")
    const diff = getString(data, "diff_preview") || getString(data, "full_diff")

    return (
      <div className={className}>
        <FileWriteCard
          filePath={filePath}
          diff={diff}
          linesAdded={linesAdded}
          linesRemoved={linesRemoved}
          changeType={changeType}
          timestamp={timestamp}
        />
      </div>
    )
  }

  // System events
  if (event_type === "agent.system_message") {
    return <div className={className}><SystemEventCard eventType={event_type} timestamp={timestamp} /></div>
  }

  // Agent lifecycle events
  if (
    event_type === "agent.started" || event_type === "AGENT_STARTED" ||
    event_type === "agent.completed" || event_type === "AGENT_COMPLETED" ||
    event_type === "agent.error" || event_type === "AGENT_ERROR"
  ) {
    const message = getString(data, "error") || getString(data, "message")
    return <div className={className}><SystemEventCard eventType={event_type} message={message} timestamp={timestamp} /></div>
  }

  // Waiting state
  if (event_type === "agent.waiting") {
    return (
      <div className={className}>
        <div className="flex items-center justify-center gap-2 py-3 text-xs text-muted-foreground">
          <Clock className="h-3.5 w-3.5 animate-pulse" />
          <span>Waiting for input...</span>
        </div>
      </div>
    )
  }

  // Skip noise
  if (event_type.includes("heartbeat")) return null

  // Unknown events - show collapsed
  const hasContent = Object.keys(data).length > 0
  if (!hasContent) return null

  return (
    <div className={className}>
      <Collapsible>
        <CollapsibleTrigger asChild>
          <button className="flex w-full items-center gap-2 px-3 py-2 rounded-lg border bg-muted/30 text-left hover:bg-muted/50 transition-colors">
            <MessageSquare className="h-4 w-4 text-muted-foreground shrink-0" />
            <span className="font-mono text-xs text-muted-foreground flex-1 truncate">
              {event_type}
            </span>
            <span className="text-[10px] text-muted-foreground">{timestamp}</span>
            <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <pre className="text-xs p-3 mt-1 rounded-lg border bg-muted/30 overflow-x-auto max-h-40 overflow-y-auto font-mono">
            {JSON.stringify(data, null, 2)}
          </pre>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}
