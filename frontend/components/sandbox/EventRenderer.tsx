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
  Loader2,
  Plug,
  Database,
  FileSearch,
  Send,
  Key,
  Zap,
  BookOpen,
  DollarSign,
  Hash,
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
// Grep Card - Search results display
// ============================================================================

interface GrepOutput {
  mode: "files_with_matches" | "content" | "count"
  filenames?: string[]
  content?: string
  numFiles?: number
  truncated?: boolean
  durationMs?: number
}

function parseGrepOutput(output: string): GrepOutput | null {
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
      // If it's plain text content (like grep content output), return as content mode
      if (output && !output.startsWith("{")) {
        return { mode: "content", content: output }
      }
      return null
    }
  }
}

interface GrepCardProps {
  pattern: string
  path?: string
  outputMode?: string
  output?: string
  status?: "running" | "completed" | "error"
  timestamp?: string
}

function GrepCard({ pattern, path, outputMode, output, status = "completed", timestamp }: GrepCardProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showAll, setShowAll] = useState(false)

  const parsed = output ? parseGrepOutput(output) : null
  const filenames = parsed?.filenames || []
  const numFiles = parsed?.numFiles ?? filenames.length
  const truncated = parsed?.truncated || false
  const mode = parsed?.mode || outputMode || "files_with_matches"
  const contentOutput = parsed?.content || (parsed?.mode === "content" ? output : null)

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (mode === "files_with_matches") {
      navigator.clipboard.writeText(filenames.join("\n"))
    } else if (contentOutput) {
      navigator.clipboard.writeText(contentOutput)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Group files by directory for better organization
  const groupedFiles = useMemo(() => {
    const groups: Record<string, string[]> = {}
    for (const filepath of filenames) {
      const parts = filepath.split("/")
      const filename = parts.pop() || filepath
      const dir = parts.join("/") || "."
      if (!groups[dir]) groups[dir] = []
      groups[dir].push(filename)
    }
    return groups
  }, [filenames])

  const sortedDirs = Object.keys(groupedFiles).sort()

  // Limit displayed directories/files initially
  const maxInitialDirs = 10
  const displayDirs = showAll ? sortedDirs : sortedDirs.slice(0, maxInitialDirs)
  const hasMoreDirs = sortedDirs.length > maxInitialDirs

  // For empty results or running state
  const isEmpty = numFiles === 0 && status !== "running"

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="rounded-lg border bg-card overflow-hidden">
        <CollapsibleTrigger asChild>
          <button className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/50 transition-colors">
            <Search className="h-4 w-4 shrink-0 text-orange-500" />
            <span className="font-medium text-sm">Grep</span>
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
                  !isEmpty && "bg-orange-500/10 text-orange-600 dark:text-orange-400 hover:bg-orange-500/20"
                )}
              >
                {numFiles} match{numFiles !== 1 ? "es" : ""}
                {truncated && "+"}
              </Badge>
            )}
            <span className="flex-1 text-xs text-muted-foreground font-mono truncate">
              {pattern}
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
          <div className="border-t px-3 py-2 bg-muted/30">
            {isEmpty ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                <Search className="h-4 w-4" />
                <span>No matches found</span>
              </div>
            ) : mode === "files_with_matches" ? (
              <>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                    Files ({numFiles})
                  </span>
                  <Button variant="ghost" size="sm" className="h-5 px-1.5" onClick={handleCopy}>
                    {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                  </Button>
                </div>
                <div className="text-xs font-mono max-h-72 overflow-y-auto space-y-2">
                  {displayDirs.map((dir) => (
                    <div key={dir}>
                      <div className="flex items-center gap-1.5 text-cyan-500 font-medium mb-0.5">
                        <FolderOpen className="h-3 w-3 shrink-0" />
                        <span className="truncate">{dir}/</span>
                        <span className="text-muted-foreground font-normal">
                          ({groupedFiles[dir].length})
                        </span>
                      </div>
                      <div className="ml-4 space-y-0.5">
                        {groupedFiles[dir].map((filename) => (
                          <div
                            key={`${dir}/${filename}`}
                            className="flex items-center gap-1.5 text-foreground hover:bg-muted/50 rounded px-1 -mx-1"
                          >
                            <File className="h-3 w-3 shrink-0 text-muted-foreground" />
                            <span className="truncate">{filename}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                {hasMoreDirs && !showAll && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setShowAll(true)
                    }}
                    className="mt-2 text-xs text-primary hover:underline"
                  >
                    Show all ({sortedDirs.length - maxInitialDirs} more directories)
                  </button>
                )}
                {truncated && (
                  <div className="mt-2 text-xs text-amber-500 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    Results truncated
                  </div>
                )}
              </>
            ) : contentOutput ? (
              <>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                    Results
                  </span>
                  <Button variant="ghost" size="sm" className="h-5 px-1.5" onClick={handleCopy}>
                    {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                  </Button>
                </div>
                <pre className="text-xs bg-background rounded p-2 overflow-x-auto max-h-64 overflow-y-auto font-mono border whitespace-pre-wrap">
                  {contentOutput}
                </pre>
              </>
            ) : null}
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
// Ask User Question Card - Beautiful question display
// ============================================================================

interface QuestionOption {
  label: string
  description?: string
}

interface Question {
  question: string
  header?: string
  options: QuestionOption[]
  multiSelect?: boolean
}

interface AskUserQuestionCardProps {
  questions: Question[]
  answer?: string
  status?: "running" | "completed"
  timestamp?: string
}

function AskUserQuestionCard({ questions, answer, status = "completed", timestamp }: AskUserQuestionCardProps) {
  const isWaiting = status === "running" && !answer

  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-amber-500/10 border-b border-amber-500/20">
        <MessageSquare className="h-4 w-4 text-amber-500 shrink-0" />
        <span className="font-medium text-sm text-amber-600 dark:text-amber-400">
          {isWaiting ? "Waiting for Response" : "Question"}
        </span>
        {isWaiting && (
          <Badge variant="secondary" className="text-[10px] h-5 bg-amber-500/20 text-amber-600 dark:text-amber-400">
            <Clock className="h-2.5 w-2.5 mr-1 animate-pulse" />
            Pending
          </Badge>
        )}
        {timestamp && (
          <span className="text-[10px] text-muted-foreground ml-auto">{timestamp}</span>
        )}
      </div>

      {/* Questions */}
      <div className="p-3 space-y-4">
        {questions.map((q, qIdx) => (
          <div key={qIdx} className="space-y-2">
            {/* Question header badge */}
            {q.header && (
              <Badge variant="outline" className="text-[10px] font-medium">
                {q.header}
              </Badge>
            )}

            {/* Question text */}
            <p className="text-sm font-medium">{q.question}</p>

            {/* Options */}
            <div className="space-y-1.5 ml-1">
              {q.options.map((opt, optIdx) => (
                <div
                  key={optIdx}
                  className="flex items-start gap-2 px-2.5 py-2 rounded-md bg-muted/50 hover:bg-muted/70 transition-colors"
                >
                  <div className={cn(
                    "mt-0.5 h-4 w-4 rounded-full border-2 shrink-0 flex items-center justify-center",
                    q.multiSelect ? "rounded-sm" : "rounded-full",
                    "border-muted-foreground/30"
                  )}>
                    {/* Empty circle/checkbox */}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{opt.label}</p>
                    {opt.description && (
                      <p className="text-xs text-muted-foreground mt-0.5">{opt.description}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Answer if provided */}
        {answer && (
          <div className="mt-3 pt-3 border-t">
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-xs font-medium text-muted-foreground">Response</p>
                <p className="text-sm">{answer}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// MCP Tool Card - Clean display for MCP server tool calls
// ============================================================================

// Parse MCP tool name: mcp__server__tool → { server: "server", tool: "tool" }
// Handles server names with underscores like "spec_workflow"
// Pattern: mcp__<server>__<tool> where server/tool can contain single underscores
function parseMcpToolName(toolName: string): { server: string; tool: string } | null {
  if (!toolName.startsWith("mcp__")) return null

  // Remove "mcp__" prefix and split by double underscore
  const withoutPrefix = toolName.slice(5) // Remove "mcp__"
  const lastDoubleUnderscoreIndex = withoutPrefix.lastIndexOf("__")

  if (lastDoubleUnderscoreIndex === -1) return null

  const server = withoutPrefix.slice(0, lastDoubleUnderscoreIndex)
  const tool = withoutPrefix.slice(lastDoubleUnderscoreIndex + 2)

  if (!server || !tool) return null

  return { server, tool }
}

// Get display-friendly server name
function formatServerName(server: string): string {
  return server
    .split("_")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

// Get display-friendly tool name
function formatToolName(tool: string): string {
  return tool
    .split(/[-_]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

// Get server-specific icon and color
function getMcpServerConfig(server: string): { icon: typeof Plug; color: string; bgColor: string } {
  const configs: Record<string, { icon: typeof Plug; color: string; bgColor: string }> = {
    spec_workflow: { icon: FileSearch, color: "text-violet-500", bgColor: "bg-violet-500/10" },
    database: { icon: Database, color: "text-cyan-500", bgColor: "bg-cyan-500/10" },
    api: { icon: Send, color: "text-blue-500", bgColor: "bg-blue-500/10" },
    auth: { icon: Key, color: "text-amber-500", bgColor: "bg-amber-500/10" },
  }
  return configs[server] || { icon: Plug, color: "text-indigo-500", bgColor: "bg-indigo-500/10" }
}

interface McpToolCardProps {
  server: string
  tool: string
  input: Record<string, unknown>
  output?: string
  status?: "running" | "completed" | "error"
  timestamp?: string
}

function McpToolCard({ server, tool, input, output, status = "completed", timestamp }: McpToolCardProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [copiedInput, setCopiedInput] = useState(false)
  const [copiedOutput, setCopiedOutput] = useState(false)

  const config = getMcpServerConfig(server)
  const Icon = config.icon
  const isRunning = status === "running"
  const hasOutput = !!output

  const handleCopyInput = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(JSON.stringify(input, null, 2))
    setCopiedInput(true)
    setTimeout(() => setCopiedInput(false), 2000)
  }

  const handleCopyOutput = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (output) {
      navigator.clipboard.writeText(output)
      setCopiedOutput(true)
      setTimeout(() => setCopiedOutput(false), 2000)
    }
  }

  // Format input as clean key-value pairs
  const inputEntries = Object.entries(input)
  const hasManyInputs = inputEntries.length > 3

  // Try to parse output as JSON for nicer formatting
  let parsedOutput: Record<string, unknown> | string | null = null
  let isJsonOutput = false
  if (output) {
    try {
      parsedOutput = JSON.parse(output)
      isJsonOutput = typeof parsedOutput === "object" && parsedOutput !== null
    } catch {
      parsedOutput = output
    }
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="rounded-lg border bg-card overflow-hidden">
        <CollapsibleTrigger asChild>
          <button className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/50 transition-colors">
            <Icon className={cn("h-4 w-4 shrink-0", config.color)} />
            <span className="font-medium text-sm">{formatToolName(tool)}</span>
            {isRunning ? (
              <Badge variant="secondary" className="text-[10px] h-5">
                <Loader2 className="h-2.5 w-2.5 mr-1 animate-spin" />
                Running
              </Badge>
            ) : (
              <Badge variant="secondary" className={cn("text-[10px] h-5", config.bgColor, config.color)}>
                {formatServerName(server)}
              </Badge>
            )}
            {/* Show first input value as summary */}
            {inputEntries.length > 0 && (
              <span className="flex-1 text-xs text-muted-foreground truncate">
                {String(inputEntries[0][1]).slice(0, 40)}
                {String(inputEntries[0][1]).length > 40 && "..."}
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
          <div className="border-t px-3 py-2 space-y-3 bg-muted/30">
            {/* Input Section */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Input</span>
                <Button variant="ghost" size="sm" className="h-5 px-1.5" onClick={handleCopyInput}>
                  {copiedInput ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                </Button>
              </div>
              {hasManyInputs ? (
                // Show as JSON for complex inputs
                <pre className="text-xs bg-background rounded p-2 overflow-x-auto max-h-32 overflow-y-auto font-mono border">
                  {JSON.stringify(input, null, 2)}
                </pre>
              ) : (
                // Show as clean key-value pairs for simple inputs
                <div className="space-y-1">
                  {inputEntries.map(([key, value]) => (
                    <div key={key} className="flex items-start gap-2 px-2 py-1.5 rounded bg-background border">
                      <span className="text-xs font-medium text-muted-foreground min-w-[80px] shrink-0">
                        {key}:
                      </span>
                      <span className="text-xs font-mono text-foreground break-all">
                        {typeof value === "string" ? value : JSON.stringify(value)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Output Section */}
            {hasOutput && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Output</span>
                  <Button variant="ghost" size="sm" className="h-5 px-1.5" onClick={handleCopyOutput}>
                    {copiedOutput ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                  </Button>
                </div>
                <pre className="text-xs bg-background rounded p-2 overflow-x-auto max-h-48 overflow-y-auto font-mono border whitespace-pre-wrap">
                  {isJsonOutput ? JSON.stringify(parsedOutput, null, 2) : output}
                </pre>
              </div>
            )}

            {/* Running indicator */}
            {isRunning && !hasOutput && (
              <div className="flex items-center gap-2 py-2">
                <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                <span className="text-xs text-muted-foreground italic">Waiting for response...</span>
              </div>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

// ============================================================================
// Skill Invoked Card - Shows when a skill is invoked
// ============================================================================

interface SkillInvokedCardProps {
  skillName: string
  input?: Record<string, unknown>
  timestamp?: string
}

function SkillInvokedCard({ skillName, input, timestamp }: SkillInvokedCardProps) {
  // Format skill name for display
  const displayName = skillName
    .split(/[-_]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")

  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2.5 bg-violet-500/10 border-b border-violet-500/20">
        <Zap className="h-4 w-4 text-violet-500 shrink-0" />
        <span className="font-medium text-sm text-violet-600 dark:text-violet-400">
          Skill Invoked
        </span>
        <Badge variant="secondary" className="text-[10px] h-5 bg-violet-500/20 text-violet-600 dark:text-violet-400 font-mono">
          {skillName}
        </Badge>
        <span className="flex-1" />
        {timestamp && (
          <span className="text-[10px] text-muted-foreground">{timestamp}</span>
        )}
      </div>
      <div className="px-3 py-2">
        <p className="text-sm text-foreground">
          Executing <span className="font-medium text-violet-600 dark:text-violet-400">{displayName}</span> skill
        </p>
        {input && Object.keys(input).length > 0 && (
          <div className="mt-2 text-xs text-muted-foreground">
            {Object.entries(input).map(([key, value]) => (
              <span key={key} className="mr-3">
                <span className="font-medium">{key}:</span> {String(value)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// Subagent Card - Shows subagent invocation and completion
// ============================================================================

interface SubagentCardProps {
  subagentType: string
  description?: string
  prompt?: string
  status: "running" | "completed"
  timestamp?: string
  result?: string
  usage?: { input_tokens?: number; output_tokens?: number }
  costUsd?: number
  durationMs?: number
}

function SubagentCard({ subagentType, description, prompt, status, timestamp, result, usage, costUsd, durationMs }: SubagentCardProps) {
  const [isOpen, setIsOpen] = useState(false)
  const isRunning = status === "running"

  // Format subagent type for display
  const displayType = subagentType
    .split(/[-_]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")

  // Format duration for display
  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  // Format cost for display
  const formatCost = (cost: number) => {
    if (cost < 0.01) return `$${cost.toFixed(4)}`
    return `$${cost.toFixed(2)}`
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="rounded-lg border bg-card overflow-hidden">
        <CollapsibleTrigger asChild>
          <button className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/50 transition-colors">
            <GitBranch className={cn(
              "h-4 w-4 shrink-0",
              isRunning ? "text-blue-500" : "text-green-500"
            )} />
            <span className="font-medium text-sm">
              {isRunning ? "Subagent Running" : "Subagent Completed"}
            </span>
            {isRunning ? (
              <Badge variant="secondary" className="text-[10px] h-5 bg-blue-500/10 text-blue-600 dark:text-blue-400">
                <Loader2 className="h-2.5 w-2.5 mr-1 animate-spin" />
                {displayType}
              </Badge>
            ) : (
              <Badge variant="secondary" className="text-[10px] h-5 bg-green-500/10 text-green-600 dark:text-green-400">
                <CheckCircle className="h-2.5 w-2.5 mr-1" />
                {displayType}
              </Badge>
            )}
            {description && (
              <span className="flex-1 text-xs text-muted-foreground truncate">
                {description}
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
          <div className="border-t px-3 py-2 bg-muted/30 space-y-3">
            {/* Metadata row - duration, cost, tokens */}
            {!isRunning && (durationMs || costUsd || usage) && (
              <div className="flex flex-wrap gap-3 text-[10px] text-muted-foreground">
                {durationMs && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatDuration(durationMs)}
                  </span>
                )}
                {costUsd !== undefined && costUsd !== null && (
                  <span className="flex items-center gap-1">
                    <DollarSign className="h-3 w-3" />
                    {formatCost(costUsd)}
                  </span>
                )}
                {usage && (
                  <span className="flex items-center gap-1">
                    <Hash className="h-3 w-3" />
                    {usage.input_tokens?.toLocaleString() || 0} in / {usage.output_tokens?.toLocaleString() || 0} out
                  </span>
                )}
              </div>
            )}

            {/* Prompt section */}
            {prompt && (
              <div>
                <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Prompt</span>
                <p className="text-xs text-foreground mt-1 whitespace-pre-wrap">{prompt}</p>
              </div>
            )}

            {/* Result section */}
            {result && !isRunning && (
              <div>
                <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Result</span>
                <div className="mt-1 p-2 rounded bg-background border">
                  <p className="text-xs text-foreground whitespace-pre-wrap">{result}</p>
                </div>
              </div>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

// ============================================================================
// Read Card - File content display with syntax highlighting
// ============================================================================

interface ReadCardProps {
  filePath: string
  content?: string
  numLines?: number
  timestamp?: string
  status?: "running" | "completed"
}

function ReadCard({ filePath, content, numLines, timestamp, status = "completed" }: ReadCardProps) {
  const [expanded, setExpanded] = useState(true)
  const [showFullContent, setShowFullContent] = useState(false)
  const [copied, setCopied] = useState(false)

  const language = getLanguageFromPath(filePath)
  const fileName = filePath.split("/").pop() || filePath
  const isRunning = status === "running"

  // Split content into lines for display
  const lines = content?.split("\n") || []
  const maxLines = 30
  const displayContent = showFullContent ? content : lines.slice(0, maxLines).join("\n")
  const hasMoreLines = lines.length > maxLines

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (content) {
      navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Get file icon based on extension
  const getFileIcon = () => {
    if (language === "python") return "🐍"
    if (language === "javascript" || language === "typescript") return "📜"
    if (language === "jsx" || language === "tsx") return "⚛️"
    if (language === "rust") return "🦀"
    if (language === "go") return "🐹"
    if (language === "docker") return "🐳"
    if (language === "json" || language === "yaml" || language === "toml") return "📋"
    if (language === "markdown") return "📝"
    if (language === "html" || language === "css") return "🎨"
    return null
  }

  const fileIcon = getFileIcon()

  return (
    <div className="rounded-lg border border-border overflow-hidden bg-card">
      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2.5 bg-blue-500/10 cursor-pointer hover:bg-blue-500/15 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <BookOpen className="h-4 w-4 text-blue-500 shrink-0" />
        <span className="font-medium text-sm text-blue-600 dark:text-blue-400">Read</span>

        {isRunning && (
          <Badge variant="secondary" className="text-[10px] h-5">
            <Loader2 className="h-2.5 w-2.5 mr-1 animate-spin" />
            Reading
          </Badge>
        )}

        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          {fileIcon && <span className="text-sm">{fileIcon}</span>}
          <span className="text-xs text-muted-foreground font-mono truncate">
            {filePath}
          </span>
        </div>

        {numLines && (
          <span className="text-[10px] text-muted-foreground shrink-0">
            {numLines} lines
          </span>
        )}

        {content && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
            onClick={handleCopy}
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
        )}

        {timestamp && (
          <span className="text-[10px] text-muted-foreground shrink-0">{timestamp}</span>
        )}
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
        )}
      </div>

      {/* Content */}
      {expanded && content && (
        <div className="border-t border-border">
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
          >
            {displayContent || ""}
          </SyntaxHighlighter>

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

      {/* Running state */}
      {expanded && isRunning && !content && (
        <div className="border-t px-4 py-3 flex items-center gap-2">
          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
          <span className="text-xs text-muted-foreground italic">Reading file...</span>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Bash Command Card - Clean terminal-style display
// ============================================================================

interface BashCardProps {
  command: string
  description?: string
  output?: string
  exitCode?: number
  timestamp?: string
  status?: "running" | "completed" | "error"
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

function BashCard({ command, description, output, exitCode: providedExitCode, timestamp, status = "completed" }: BashCardProps) {
  const [expanded, setExpanded] = useState(true)
  const [copied, setCopied] = useState(false)

  // Parse the output
  const { stdout, stderr, exitCode: parsedExitCode } = parseBashOutput(output || "")
  const exitCode = providedExitCode ?? parsedExitCode
  const hasOutput = stdout || stderr
  const isError = (exitCode !== undefined && exitCode !== 0) || !!stderr
  const isRunning = status === "running"

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(stdout || output || "")
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Truncate command for header display
  const truncatedCommand = command.length > 60 ? command.slice(0, 60) + "..." : command

  return (
    <div className="rounded-lg border border-zinc-800 overflow-hidden bg-zinc-900">
      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 bg-zinc-800/50 cursor-pointer hover:bg-zinc-800 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <Terminal className="h-4 w-4 text-purple-400 shrink-0" />
        <span className="font-medium text-sm text-zinc-100">Terminal</span>
        {isRunning && (
          <Badge variant="secondary" className="text-[10px] h-5">
            <Play className="h-2.5 w-2.5 mr-1 animate-pulse" />
            Running
          </Badge>
        )}
        {isError && !isRunning && (
          <Badge variant="destructive" className="text-[10px] h-5">
            {stderr ? "Error" : `Exit ${exitCode}`}
          </Badge>
        )}
        {/* Show description if available, otherwise truncated command */}
        <span className="flex-1 text-xs text-zinc-400 truncate">
          {description || truncatedCommand}
        </span>

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
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-zinc-500 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-zinc-500 shrink-0" />
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

          {/* No output message - only show for completed commands */}
          {!stdout && !stderr && !isRunning && (
            <div className="px-4 pb-3">
              <span className="text-xs text-zinc-500 italic">Command completed with no output</span>
            </div>
          )}

          {/* Running indicator */}
          {isRunning && !stdout && !stderr && (
            <div className="px-4 pb-3 flex items-center gap-2">
              <Loader2 className="h-3 w-3 animate-spin text-zinc-500" />
              <span className="text-xs text-zinc-500 italic">Running...</span>
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

    // Skip messages that are actually subagent prompts (they're rendered by SubagentCard)
    // These typically come through as agent.message but should be suppressed
    const isSubagentContext = data.subagent_type || data.tool === "Task"
    if (isSubagentContext) return null

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

    // Skip Task tool - this is handled by agent.subagent_invoked/completed events
    if (tool === "Task") return null

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
      const oldString = getString(toolInput, "oldString") || getString(toolInput, "old_string") || ""
      const newString = getString(toolInput, "newString") || getString(toolInput, "new_string") || ""
      
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

    // Read tool - file content display
    if (tool === "Read") {
      const filePath = getString(toolInput, "filePath") || getString(toolInput, "file_path") || ""
      // Parse toolResponse to extract file content
      let fileContent = ""
      let numLines: number | undefined

      if (toolResponse) {
        // Try to extract content from Python dict format: {'type': 'text', 'file': {'content': '...'}}
        // Use regex to extract the content field directly
        // Use [\s\S] instead of . to match across newlines (since 's' flag not available)
        const contentMatch = toolResponse.match(/'content':\s*'((?:[^'\\]|\\[\s\S])*)'(?:,|\})/)
        if (contentMatch) {
          fileContent = contentMatch[1]
            // Unescape common escape sequences
            .replace(/\\n/g, "\n")
            .replace(/\\t/g, "\t")
            .replace(/\\r/g, "\r")
            .replace(/\\\\/g, "\\")
            .replace(/\\'/g, "'")
            .replace(/\\"/g, '"')
        } else {
          // Try standard JSON parsing
          try {
            const parsed = JSON.parse(toolResponse)
            if (parsed.file?.content) {
              fileContent = parsed.file.content
              numLines = parsed.file.numLines || parsed.file.totalLines
            } else if (typeof parsed === "string") {
              fileContent = parsed
            }
          } catch {
            // Not JSON, use raw response
            fileContent = toolResponse
          }
        }

        // Try to extract numLines/totalLines
        const numLinesMatch = toolResponse.match(/'(?:numLines|totalLines)':\s*(\d+)/)
        if (numLinesMatch) {
          numLines = parseInt(numLinesMatch[1], 10)
        }
      }

      return (
        <div className={className}>
          <ReadCard
            filePath={filePath}
            content={fileContent}
            numLines={numLines}
            timestamp={timestamp}
          />
        </div>
      )
    }

    // Bash tool
    if (tool === "Bash") {
      const command = getString(toolInput, "command")
      const description = getString(toolInput, "description")
      return (
        <div className={className}>
          <BashCard
            command={command}
            description={description}
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

    // Grep tool - search results display
    if (tool === "Grep") {
      const pattern = getString(toolInput, "pattern")
      const path = getString(toolInput, "path")
      const outputMode = getString(toolInput, "output_mode")
      return (
        <div className={className}>
          <GrepCard
            pattern={pattern}
            path={path}
            outputMode={outputMode}
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

    // AskUserQuestion tool
    if (tool === "AskUserQuestion" && toolInput.questions) {
      const questions = toolInput.questions as Question[]
      return (
        <div className={className}>
          <AskUserQuestionCard
            questions={questions}
            answer={toolResponse}
            timestamp={timestamp}
          />
        </div>
      )
    }

    // MCP tool calls - detect by mcp__ prefix
    const mcpParsed = parseMcpToolName(tool)
    if (mcpParsed) {
      return (
        <div className={className}>
          <McpToolCard
            server={mcpParsed.server}
            tool={mcpParsed.tool}
            input={toolInput}
            output={toolResponse}
            timestamp={timestamp}
          />
        </div>
      )
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

    // Skip Task tool - this is handled by agent.subagent_invoked/completed events
    if (tool === "Task") return null

    // Read tool - show running state
    if (tool === "Read") {
      const filePath = getString(toolInput, "filePath") || getString(toolInput, "file_path") || ""
      return (
        <div className={className}>
          <ReadCard
            filePath={filePath}
            status="running"
            timestamp={timestamp}
          />
        </div>
      )
    }

    // Bash tool - show running state with BashCard
    if (tool === "Bash") {
      const command = getString(toolInput, "command")
      const description = getString(toolInput, "description")
      return (
        <div className={className}>
          <BashCard
            command={command}
            description={description}
            status="running"
            timestamp={timestamp}
          />
        </div>
      )
    }

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

    // Grep tool - show running state with GrepCard
    if (tool === "Grep") {
      const pattern = getString(toolInput, "pattern")
      const path = getString(toolInput, "path")
      const outputMode = getString(toolInput, "output_mode")
      return (
        <div className={className}>
          <GrepCard
            pattern={pattern}
            path={path}
            outputMode={outputMode}
            status="running"
            timestamp={timestamp}
          />
        </div>
      )
    }

    // AskUserQuestion tool - show waiting state
    if (tool === "AskUserQuestion" && toolInput.questions) {
      const questions = toolInput.questions as Question[]
      return (
        <div className={className}>
          <AskUserQuestionCard
            questions={questions}
            status="running"
            timestamp={timestamp}
          />
        </div>
      )
    }

    // MCP tool calls - show running state
    const mcpParsed = parseMcpToolName(tool)
    if (mcpParsed) {
      return (
        <div className={className}>
          <McpToolCard
            server={mcpParsed.server}
            tool={mcpParsed.tool}
            input={toolInput}
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

  // Skill invoked events
  if (event_type === "agent.skill_invoked") {
    const input = (data.input || {}) as Record<string, unknown>
    const skillName = getString(input, "skill") || getString(data, "skill_name") || "unknown"
    return (
      <div className={className}>
        <SkillInvokedCard
          skillName={skillName}
          input={input}
          timestamp={timestamp}
        />
      </div>
    )
  }

  // Subagent invoked events
  if (event_type === "agent.subagent_invoked") {
    const toolInput = (data.tool_input || {}) as Record<string, unknown>
    const subagentType = getString(data, "subagent_type") || getString(toolInput, "subagent_type") || "unknown"
    const description = getString(data, "description") || getString(data, "subagent_description") || getString(toolInput, "description") || ""
    const prompt = getString(data, "subagent_prompt") || getString(toolInput, "prompt") || ""
    return (
      <div className={className}>
        <SubagentCard
          subagentType={subagentType}
          description={description}
          prompt={prompt}
          status="running"
          timestamp={timestamp}
        />
      </div>
    )
  }

  // Subagent completed events
  if (event_type === "agent.subagent_completed") {
    const toolInput = (data.tool_input || {}) as Record<string, unknown>
    const subagentType = getString(data, "subagent_type") || getString(toolInput, "subagent_type") || "unknown"
    const description = getString(data, "description") || getString(data, "subagent_description") || getString(toolInput, "description") || ""
    const prompt = getString(data, "subagent_prompt") || getString(toolInput, "prompt") || ""

    // Extract result data from completed subagent
    const result = getString(data, "subagent_result") || undefined
    const usage = data.subagent_usage as { input_tokens?: number; output_tokens?: number } | undefined
    const costUsd = typeof data.subagent_cost_usd === "number" ? data.subagent_cost_usd : undefined
    const durationMs = typeof data.subagent_duration_ms === "number" ? data.subagent_duration_ms : undefined

    return (
      <div className={className}>
        <SubagentCard
          subagentType={subagentType}
          description={description}
          prompt={prompt}
          status="completed"
          timestamp={timestamp}
          result={result}
          usage={usage}
          costUsd={costUsd}
          durationMs={durationMs}
        />
      </div>
    )
  }

  // Skip noise
  if (event_type.includes("heartbeat")) return null

  // ============================================================================
  // Iteration & Continuous Mode Events - Visible progress indicators
  // ============================================================================

  // Iteration started - clear indicator with iteration number
  if (event_type === "iteration.started") {
    const iterNum = getNumber(data, "iteration_num")
    return (
      <div className={cn(className)}>
        <div className="flex items-center gap-2 px-3 py-2 text-xs bg-blue-500/10 border border-blue-500/20 rounded-md">
          <Play className="h-4 w-4 text-blue-500" />
          <span className="font-medium text-blue-600 dark:text-blue-400">
            Iteration {iterNum} started
          </span>
        </div>
      </div>
    )
  }

  // Iteration completed - show cost and completion status
  if (event_type === "iteration.completed") {
    const iterNum = getNumber(data, "iteration_num")
    const costUsd = getNumber(data, "cost_usd")
    const outputPreview = getString(data, "output_preview")
    const completionCount = getNumber(data, "completion_signal_count")

    // If there's a meaningful output preview, show it more prominently
    if (outputPreview && outputPreview.length > 20) {
      return null // Skip - the actual content will be shown by other events
    }

    return (
      <div className={cn(className)}>
        <div className="flex items-center gap-2 px-3 py-2 text-xs bg-green-500/10 border border-green-500/20 rounded-md">
          <CheckCircle className="h-4 w-4 text-green-500" />
          <span className="font-medium text-green-600 dark:text-green-400">
            Iteration {iterNum} completed
          </span>
          {costUsd > 0 && (
            <span className="text-green-600/70 dark:text-green-400/70">
              ${costUsd.toFixed(4)}
            </span>
          )}
          {completionCount > 0 && (
            <Badge variant="outline" className="h-5 px-2 text-[10px] bg-green-500/20 text-green-600 border-green-500/30 font-medium">
              COMPLETE
            </Badge>
          )}
        </div>
      </div>
    )
  }

  // Iteration validation - show pass/fail status clearly
  if (event_type === "iteration.validation") {
    const passed = data.passed === true
    const errors = Array.isArray(data.errors) ? data.errors : []
    const feedback = getString(data, "feedback")

    // If validation passed - show success
    if (passed) {
      return (
        <div className={cn(className)}>
          <div className="flex items-center gap-2 px-3 py-2 text-xs bg-emerald-500/10 border border-emerald-500/20 rounded-md">
            <CheckCircle className="h-4 w-4 text-emerald-500" />
            <span className="font-medium text-emerald-600 dark:text-emerald-400">
              Validation passed
            </span>
          </div>
        </div>
      )
    }

    // If validation failed, show prominently with details
    return (
      <div className={cn(className)}>
        <div className="flex items-center gap-2 px-3 py-2 text-xs bg-amber-500/10 border border-amber-500/20 rounded-md">
          <AlertCircle className="h-4 w-4 text-amber-500" />
          <span className="font-medium text-amber-600 dark:text-amber-400">
            Validation: {feedback || errors.join(", ") || "checking..."}
          </span>
        </div>
      </div>
    )
  }

  // Completion signal - shows progress toward task completion
  if (event_type === "iteration.completion_signal") {
    const signalCount = getNumber(data, "signal_count")
    const threshold = getNumber(data, "threshold")

    return (
      <div className={cn(className)}>
        <div className="flex items-center gap-2 px-3 py-2 text-xs bg-purple-500/10 border border-purple-500/20 rounded-md">
          <Sparkles className="h-4 w-4 text-purple-500" />
          <span className="font-medium text-purple-600 dark:text-purple-400">
            TASK_COMPLETE signal ({signalCount}/{threshold})
          </span>
        </div>
      </div>
    )
  }

  // Continuous mode started - clear indicator
  if (event_type === "continuous.started") {
    return (
      <div className={cn(className)}>
        <div className="flex items-center gap-2 px-3 py-2 text-xs bg-indigo-500/10 border border-indigo-500/20 rounded-md">
          <Loader2 className="h-4 w-4 text-indigo-500 animate-spin" />
          <span className="font-medium text-indigo-600 dark:text-indigo-400">
            Continuous mode started
          </span>
        </div>
      </div>
    )
  }

  // Continuous mode completed - show summary with stats
  if (event_type === "continuous.completed") {
    const stopReason = getString(data, "stop_reason")
    const totalIterations = getNumber(data, "iteration_num")
    const totalCost = getNumber(data, "total_cost_usd")
    const elapsedSecs = getNumber(data, "elapsed_seconds")

    const reasonLabel = stopReason === "task_complete" ? "Task completed" :
                        stopReason === "max_iterations_reached" ? "Max iterations reached" :
                        stopReason === "validation_passed" ? "Validation passed" :
                        stopReason || "Completed"

    const isSuccess = stopReason === "task_complete" || stopReason === "validation_passed"
    const bgColor = isSuccess ? "bg-green-500/10 border-green-500/20" : "bg-amber-500/10 border-amber-500/20"
    const textColor = isSuccess ? "text-green-600 dark:text-green-400" : "text-amber-600 dark:text-amber-400"
    const iconColor = isSuccess ? "text-green-500" : "text-amber-500"

    return (
      <div className={cn(className)}>
        <div className={cn("flex items-center gap-3 px-3 py-2 text-xs border rounded-md", bgColor)}>
          <CheckCircle className={cn("h-4 w-4", iconColor)} />
          <span className={cn("font-medium", textColor)}>{reasonLabel}</span>
          <span className="text-muted-foreground">•</span>
          <span className="text-muted-foreground">{totalIterations} iterations</span>
          {totalCost > 0 && (
            <>
              <span className="text-muted-foreground">•</span>
              <span className="text-muted-foreground">${totalCost.toFixed(2)}</span>
            </>
          )}
          {elapsedSecs > 0 && (
            <>
              <span className="text-muted-foreground">•</span>
              <span className="text-muted-foreground">{Math.round(elapsedSecs)}s</span>
            </>
          )}
        </div>
      </div>
    )
  }

  // SANDBOX_SPAWNED and VALIDATION_SANDBOX_SPAWNED - subtle system events
  if (event_type === "SANDBOX_SPAWNED" || event_type === "VALIDATION_SANDBOX_SPAWNED") {
    const sandboxId = getString(data, "sandbox_id")
    const shortId = sandboxId ? sandboxId.slice(-8) : ""
    const isValidation = event_type.includes("VALIDATION")

    return (
      <div className={cn(className, "opacity-40 hover:opacity-100 transition-opacity")}>
        <div className="flex items-center gap-2 px-2 py-1 text-[10px] text-muted-foreground">
          <Terminal className="h-3 w-3" />
          <span>{isValidation ? "Validation sandbox" : "Sandbox"} spawned</span>
          {shortId && <code className="text-[9px] bg-muted px-1 rounded">{shortId}</code>}
        </div>
      </div>
    )
  }

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
