"use client"

import { use, useState } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  ArrowLeft,
  GitCommit,
  GitBranch,
  Clock,
  User,
  FileCode,
  Plus,
  Minus,
  ChevronRight,
  Copy,
  ExternalLink,
  CheckCircle,
  XCircle,
  AlertCircle,
  Eye,
  EyeOff,
} from "lucide-react"

interface CommitPageProps {
  params: Promise<{ commitSha: string }>
}

// Mock commit data
const mockCommit = {
  sha: "a1b2c3d4e5f6g7h8i9j0",
  shortSha: "a1b2c3d",
  message: "feat: Implement JWT authentication middleware",
  description: `This commit adds JWT-based authentication to the API.

Changes include:
- New auth middleware for route protection
- Token generation and validation utilities
- Refresh token rotation mechanism
- Unit tests for auth module`,
  author: {
    name: "Agent Worker-1",
    email: "agent@omoios.com",
    avatar: null,
  },
  timestamp: "2 hours ago",
  date: "Dec 5, 2024, 2:34 PM",
  branch: "feature/jwt-auth",
  parent: "b2c3d4e5",
  stats: {
    additions: 156,
    deletions: 23,
    filesChanged: 5,
  },
  verified: true,
  checks: {
    passed: 12,
    failed: 0,
    pending: 1,
  },
}

// Mock file changes
const mockFiles = [
  {
    path: "src/auth/jwt.ts",
    status: "added",
    additions: 67,
    deletions: 0,
    hunks: [
      {
        header: "@@ -0,0 +1,67 @@",
        lines: [
          { type: "add", number: 1, content: "import jwt from 'jsonwebtoken';" },
          { type: "add", number: 2, content: "import { config } from '../config';" },
          { type: "add", number: 3, content: "" },
          { type: "add", number: 4, content: "interface TokenPayload {" },
          { type: "add", number: 5, content: "  userId: string;" },
          { type: "add", number: 6, content: "  email: string;" },
          { type: "add", number: 7, content: "  role: string;" },
          { type: "add", number: 8, content: "}" },
          { type: "add", number: 9, content: "" },
          { type: "add", number: 10, content: "export function generateAccessToken(payload: TokenPayload): string {" },
          { type: "add", number: 11, content: "  return jwt.sign(payload, config.jwtSecret, {" },
          { type: "add", number: 12, content: "    expiresIn: '15m'," },
          { type: "add", number: 13, content: "  });" },
          { type: "add", number: 14, content: "}" },
        ],
      },
    ],
  },
  {
    path: "src/auth/middleware.ts",
    status: "added",
    additions: 45,
    deletions: 0,
    hunks: [
      {
        header: "@@ -0,0 +1,45 @@",
        lines: [
          { type: "add", number: 1, content: "import { Request, Response, NextFunction } from 'express';" },
          { type: "add", number: 2, content: "import { verifyToken } from './jwt';" },
          { type: "add", number: 3, content: "" },
          { type: "add", number: 4, content: "export const authMiddleware = async (" },
          { type: "add", number: 5, content: "  req: Request," },
          { type: "add", number: 6, content: "  res: Response," },
          { type: "add", number: 7, content: "  next: NextFunction" },
          { type: "add", number: 8, content: ") => {" },
          { type: "add", number: 9, content: "  const token = req.headers.authorization?.split(' ')[1];" },
          { type: "add", number: 10, content: "" },
          { type: "add", number: 11, content: "  if (!token) {" },
          { type: "add", number: 12, content: "    return res.status(401).json({ error: 'No token provided' });" },
          { type: "add", number: 13, content: "  }" },
        ],
      },
    ],
  },
  {
    path: "src/api/routes.ts",
    status: "modified",
    additions: 23,
    deletions: 8,
    hunks: [
      {
        header: "@@ -15,8 +15,23 @@",
        lines: [
          { type: "context", number: 15, content: "import express from 'express';" },
          { type: "context", number: 16, content: "import { userRoutes } from './routes/user';" },
          { type: "del", number: 17, content: "import { publicRoutes } from './routes/public';" },
          { type: "add", number: 17, content: "import { authRoutes } from './routes/auth';" },
          { type: "add", number: 18, content: "import { authMiddleware } from '../auth/middleware';" },
          { type: "context", number: 19, content: "" },
          { type: "context", number: 20, content: "const router = express.Router();" },
          { type: "context", number: 21, content: "" },
          { type: "del", number: 22, content: "router.use('/public', publicRoutes);" },
          { type: "add", number: 22, content: "// Public routes" },
          { type: "add", number: 23, content: "router.use('/auth', authRoutes);" },
          { type: "add", number: 24, content: "" },
          { type: "add", number: 25, content: "// Protected routes" },
          { type: "add", number: 26, content: "router.use('/users', authMiddleware, userRoutes);" },
        ],
      },
    ],
  },
  {
    path: "tests/auth/jwt.test.ts",
    status: "added",
    additions: 89,
    deletions: 0,
    hunks: [
      {
        header: "@@ -0,0 +1,89 @@",
        lines: [
          { type: "add", number: 1, content: "import { describe, it, expect } from 'vitest';" },
          { type: "add", number: 2, content: "import { generateAccessToken, verifyToken } from '../../src/auth/jwt';" },
          { type: "add", number: 3, content: "" },
          { type: "add", number: 4, content: "describe('JWT Utils', () => {" },
          { type: "add", number: 5, content: "  describe('generateAccessToken', () => {" },
          { type: "add", number: 6, content: "    it('should generate a valid token', () => {" },
          { type: "add", number: 7, content: "      const payload = { userId: '123', email: 'test@test.com', role: 'user' };" },
          { type: "add", number: 8, content: "      const token = generateAccessToken(payload);" },
          { type: "add", number: 9, content: "      expect(token).toBeDefined();" },
          { type: "add", number: 10, content: "    });" },
          { type: "add", number: 11, content: "  });" },
          { type: "add", number: 12, content: "});" },
        ],
      },
    ],
  },
  {
    path: "src/types/auth.ts",
    status: "deleted",
    additions: 0,
    deletions: 15,
    hunks: [
      {
        header: "@@ -1,15 +0,0 @@",
        lines: [
          { type: "del", number: 1, content: "// Old auth types - deprecated" },
          { type: "del", number: 2, content: "export interface OldAuthConfig {" },
          { type: "del", number: 3, content: "  secret: string;" },
          { type: "del", number: 4, content: "  expiry: number;" },
          { type: "del", number: 5, content: "}" },
        ],
      },
    ],
  },
]

export default function CommitPage({ params }: CommitPageProps) {
  const { commitSha } = use(params)
  const [expandedFiles, setExpandedFiles] = useState<string[]>(mockFiles.map((f) => f.path))
  const [showWhitespace, setShowWhitespace] = useState(false)

  const toggleFile = (path: string) => {
    setExpandedFiles((prev) =>
      prev.includes(path) ? prev.filter((p) => p !== path) : [...prev, path]
    )
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success("Copied to clipboard")
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "added":
        return "text-green-600"
      case "deleted":
        return "text-red-500"
      case "modified":
        return "text-amber-500"
      default:
        return "text-muted-foreground"
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "added":
        return <Badge className="bg-green-100 text-green-700 hover:bg-green-100">Added</Badge>
      case "deleted":
        return <Badge className="bg-red-100 text-red-700 hover:bg-red-100">Deleted</Badge>
      case "modified":
        return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100">Modified</Badge>
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
  }

  return (
    <div className="container mx-auto max-w-6xl p-6 space-y-6">
      <Link
        href="/agents"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back
      </Link>

      {/* Commit Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <CardTitle className="text-xl">{mockCommit.message}</CardTitle>
              <CardDescription className="whitespace-pre-wrap">
                {mockCommit.description}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {mockCommit.verified && (
                <Badge variant="outline" className="gap-1 text-green-600 border-green-200">
                  <CheckCircle className="h-3 w-3" />
                  Verified
                </Badge>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(mockCommit.sha)}
              >
                <Copy className="mr-1 h-3 w-3" />
                {mockCommit.shortSha}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <User className="h-4 w-4 text-muted-foreground" />
              <span>{mockCommit.author.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span>{mockCommit.date}</span>
            </div>
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-muted-foreground" />
              <Badge variant="secondary">{mockCommit.branch}</Badge>
            </div>
            <div className="flex items-center gap-2">
              <GitCommit className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-xs">parent: {mockCommit.parent}</span>
            </div>
          </div>

          {/* Stats */}
          <div className="mt-4 flex items-center gap-6">
            <div className="flex items-center gap-2">
              <FileCode className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">{mockCommit.stats.filesChanged} files changed</span>
            </div>
            <div className="flex items-center gap-1">
              <Plus className="h-4 w-4 text-green-600" />
              <span className="text-sm text-green-600">{mockCommit.stats.additions}</span>
            </div>
            <div className="flex items-center gap-1">
              <Minus className="h-4 w-4 text-red-500" />
              <span className="text-sm text-red-500">{mockCommit.stats.deletions}</span>
            </div>
            <div className="ml-auto flex items-center gap-2 text-sm">
              <span className="flex items-center gap-1 text-green-600">
                <CheckCircle className="h-4 w-4" />
                {mockCommit.checks.passed}
              </span>
              {mockCommit.checks.failed > 0 && (
                <span className="flex items-center gap-1 text-red-500">
                  <XCircle className="h-4 w-4" />
                  {mockCommit.checks.failed}
                </span>
              )}
              {mockCommit.checks.pending > 0 && (
                <span className="flex items-center gap-1 text-amber-500">
                  <AlertCircle className="h-4 w-4" />
                  {mockCommit.checks.pending}
                </span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* File Changes */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Changed Files</h2>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowWhitespace(!showWhitespace)}
          >
            {showWhitespace ? (
              <EyeOff className="mr-1 h-4 w-4" />
            ) : (
              <Eye className="mr-1 h-4 w-4" />
            )}
            Whitespace
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              setExpandedFiles(
                expandedFiles.length === mockFiles.length
                  ? []
                  : mockFiles.map((f) => f.path)
              )
            }
          >
            {expandedFiles.length === mockFiles.length ? "Collapse All" : "Expand All"}
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        {mockFiles.map((file) => (
          <Card key={file.path} className="overflow-hidden">
            <Collapsible
              open={expandedFiles.includes(file.path)}
              onOpenChange={() => toggleFile(file.path)}
            >
              <CollapsibleTrigger asChild>
                <button className="w-full flex items-center justify-between p-4 hover:bg-accent/50 transition-colors">
                  <div className="flex items-center gap-3">
                    <ChevronRight 
                      className={`h-4 w-4 transition-transform duration-200 ${
                        expandedFiles.includes(file.path) ? "rotate-90" : ""
                      }`} 
                    />
                    <FileCode className={`h-4 w-4 ${getStatusColor(file.status)}`} />
                    <span className="font-mono text-sm">{file.path}</span>
                    {getStatusBadge(file.status)}
                  </div>
                  <div className="flex items-center gap-3 text-sm font-mono">
                    {file.additions > 0 && (
                      <span className="text-green-600">+{file.additions}</span>
                    )}
                    {file.deletions > 0 && (
                      <span className="text-red-500">-{file.deletions}</span>
                    )}
                  </div>
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="border-t bg-muted/30">
                  {file.hunks.map((hunk, hunkIndex) => (
                    <div key={hunkIndex}>
                      <div className="bg-muted px-4 py-1 text-xs font-mono text-muted-foreground">
                        {hunk.header}
                      </div>
                      <div className="font-mono text-sm">
                        {hunk.lines.map((line, lineIndex) => (
                          <div
                            key={lineIndex}
                            className={`flex ${
                              line.type === "add"
                                ? "bg-green-50 dark:bg-green-950/30"
                                : line.type === "del"
                                ? "bg-red-50 dark:bg-red-950/30"
                                : ""
                            }`}
                          >
                            <span className="w-12 shrink-0 px-2 py-0.5 text-right text-xs text-muted-foreground select-none border-r">
                              {line.number}
                            </span>
                            <span
                              className={`w-6 shrink-0 text-center py-0.5 select-none ${
                                line.type === "add"
                                  ? "text-green-600"
                                  : line.type === "del"
                                  ? "text-red-500"
                                  : "text-muted-foreground"
                              }`}
                            >
                              {line.type === "add" ? "+" : line.type === "del" ? "-" : " "}
                            </span>
                            <code className="flex-1 px-2 py-0.5 whitespace-pre overflow-x-auto">
                              {line.content}
                            </code>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </CollapsibleContent>
            </Collapsible>
          </Card>
        ))}
      </div>
    </div>
  )
}
