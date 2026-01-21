# Full Dev Environment Access - Design Document

**Created**: 2025-01-20
**Status**: Draft
**Purpose**: Enable users to watch agents code, test, and debug in isolated sandboxes with complete transparency

## Overview

"Full Dev Environment Access" provides a real-time window into agent execution, allowing users to see exactly what agents are doing in their sandboxes. This feature transforms opaque agent execution into transparent, observable development workflows.

![Feature Mockup](../../assets/full_dev_environment_mockup.png)

### Key Components

1. **File Explorer** - Tree view of workspace files with real-time updates
2. **Code Editor** - Syntax-highlighted file viewer with diff support
3. **Live Terminal** - Streaming command output as agents execute
4. **File Watcher** - Real-time notifications when agents modify files

---

## Current State Analysis

### What Daytona SDK Provides (But We Don't Use Yet)

| Capability | SDK Method | Current Usage |
|------------|-----------|---------------|
| **List Files** | `sandbox.fs.list_files(path)` | Not used |
| **Search Files** | `sandbox.fs.search_files(path, pattern)` | Not used |
| **Find in Files** | `sandbox.fs.find_files(path, pattern)` | Not used |
| **File Info** | `sandbox.fs.get_file_info(path)` | Not used |
| **Sessions** | `sandbox.process.create_session()` | Not used |
| **Streaming Logs** | `sandbox.process.get_session_command_logs_async()` | Not used |
| **LSP Server** | `sandbox.create_lsp_server()` | Not used |
| Read/Write/Upload/Download | Various | Partially used |

### What We Currently Have

```
Backend:
├── DaytonaWorkspace class with basic file ops
├── WebSocket infrastructure (events.py)
├── Redis pub/sub for real-time events
├── SandboxEvent model for persistence
└── API routes for sandbox operations

Frontend:
├── WebSocketProvider with auto-reconnect
├── useSandboxRealtimeEvents() hook
├── Monaco Editor (available via Next.js)
└── xterm.js (available)
```

---

## Architecture Design

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ FileExplorer │  │  CodeEditor  │  │     LiveTerminal         │  │
│  │   (Tree)     │  │   (Monaco)   │  │      (xterm.js)          │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘  │
│         │                 │                        │                 │
│         └─────────────────┴────────────────────────┘                 │
│                           │                                          │
│                    useSandboxDevEnv()                                │
│                           │                                          │
│                    WebSocketProvider                                 │
└───────────────────────────┼──────────────────────────────────────────┘
                            │ WebSocket
┌───────────────────────────┼──────────────────────────────────────────┐
│                           │         BACKEND                          │
├───────────────────────────┼──────────────────────────────────────────┤
│                    ┌──────┴───────┐                                  │
│                    │   WebSocket   │                                  │
│                    │   Handler     │                                  │
│                    └──────┬───────┘                                  │
│                           │                                          │
│  ┌────────────────────────┼────────────────────────────────────┐    │
│  │              SandboxDevEnvService                            │    │
│  ├──────────────────────────────────────────────────────────────┤    │
│  │  list_directory()    │  read_file()    │  stream_terminal()  │    │
│  │  get_file_tree()     │  watch_files()  │  execute_command()  │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                           │                                          │
│                    ┌──────┴───────┐                                  │
│                    │   Daytona    │                                  │
│                    │   Sandbox    │                                  │
│                    └──────────────┘                                  │
└──────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Opens Dev Environment View
         │
         ▼
┌─────────────────────────┐
│ 1. Connect WebSocket    │
│    /ws/sandbox/{id}/dev │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 2. Request File Tree    │
│    {type: "file_tree"}  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 3. Backend calls:       │
│    sandbox.fs.list_files│
│    Returns FileInfo[]   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 4. User clicks file     │
│    {type: "read_file"}  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 5. Backend calls:       │
│    sandbox.fs.download  │
│    Returns file content │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│ 6. File watcher pushes  │◄──────│ Agent modifies file     │
│    {type: "file_change"}│       │ inotifywait detects     │
└─────────────────────────┘       └─────────────────────────┘
```

---

## Implementation Plan

### Phase 1: File Explorer (Foundation)

**Backend Changes:**

```python
# backend/omoi_os/workspace/daytona.py - Add methods

class DaytonaWorkspace:
    # ... existing code ...

    def list_directory(self, path: str) -> list[FileInfo]:
        """List files and directories at path.

        Uses Daytona SDK's native list_files method.

        Returns:
            List of FileInfo with name, is_dir, size, mod_time
        """
        return self.sandbox.fs.list_files(path)

    def get_file_tree(self, path: str, max_depth: int = 3) -> dict:
        """Get recursive file tree structure.

        Args:
            path: Root path to start from
            max_depth: Maximum depth to traverse (default 3)

        Returns:
            Nested dict structure:
            {
                "name": "workspace",
                "type": "directory",
                "path": "/home/daytona/workspace",
                "children": [
                    {"name": "src", "type": "directory", "children": [...]},
                    {"name": "main.py", "type": "file", "size": 1234}
                ]
            }
        """
        def build_tree(current_path: str, depth: int) -> dict:
            if depth > max_depth:
                return {"truncated": True}

            files = self.sandbox.fs.list_files(current_path)
            children = []

            for f in files:
                node = {
                    "name": f.name,
                    "type": "directory" if f.is_dir else "file",
                    "path": f"{current_path}/{f.name}",
                }
                if not f.is_dir:
                    node["size"] = f.size
                    node["modified"] = f.mod_time
                else:
                    node["children"] = build_tree(
                        f"{current_path}/{f.name}", depth + 1
                    )
                children.append(node)

            return children

        return {
            "name": path.split("/")[-1] or path,
            "type": "directory",
            "path": path,
            "children": build_tree(path, 1)
        }

    def search_files(self, path: str, pattern: str) -> list[str]:
        """Search for files matching glob pattern.

        Args:
            path: Directory to search in
            pattern: Glob pattern (e.g., "*.py", "**/*.ts")

        Returns:
            List of matching file paths
        """
        return self.sandbox.fs.search_files(path, pattern)

    def find_in_files(self, path: str, pattern: str) -> list[dict]:
        """Search for content within files (grep-like).

        Args:
            path: Directory to search in
            pattern: Text/regex pattern to find

        Returns:
            List of matches: [{"path": str, "line": int, "content": str}]
        """
        matches = self.sandbox.fs.find_files(path, pattern)
        return [
            {"path": m.file, "line": m.line, "content": m.content}
            for m in matches
        ]
```

**New API Endpoint:**

```python
# backend/omoi_os/api/routes/sandbox.py - Add endpoint

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

class FileTreeRequest(BaseModel):
    path: str = "/home/daytona"
    max_depth: int = 3

class FileReadRequest(BaseModel):
    path: str

@router.get("/{sandbox_id}/files/tree")
async def get_file_tree(
    sandbox_id: str,
    path: str = "/home/daytona",
    max_depth: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get file tree for sandbox workspace."""
    workspace = get_sandbox_workspace(sandbox_id, db, current_user)
    return workspace.get_file_tree(path, max_depth)

@router.get("/{sandbox_id}/files/read")
async def read_file(
    sandbox_id: str,
    path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Read file content from sandbox."""
    workspace = get_sandbox_workspace(sandbox_id, db, current_user)
    content = workspace.read_file(path)

    # Detect encoding/binary
    try:
        text = content.decode("utf-8")
        return {"path": path, "content": text, "binary": False}
    except UnicodeDecodeError:
        # Return base64 for binary files
        import base64
        return {
            "path": path,
            "content": base64.b64encode(content).decode(),
            "binary": True
        }

@router.get("/{sandbox_id}/files/search")
async def search_files(
    sandbox_id: str,
    path: str,
    pattern: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search for files matching pattern."""
    workspace = get_sandbox_workspace(sandbox_id, db, current_user)
    return {"matches": workspace.search_files(path, pattern)}
```

**Frontend Component:**

```tsx
// frontend/components/sandbox/FileExplorer.tsx

import { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, File, Folder } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileNode {
  name: string;
  type: 'file' | 'directory';
  path: string;
  size?: number;
  modified?: string;
  children?: FileNode[];
}

interface FileExplorerProps {
  sandboxId: string;
  onFileSelect: (path: string) => void;
}

export function FileExplorer({ sandboxId, onFileSelect }: FileExplorerProps) {
  const [tree, setTree] = useState<FileNode | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<string | null>(null);

  // Fetch tree on mount
  useEffect(() => {
    fetchFileTree();
  }, [sandboxId]);

  const fetchFileTree = async () => {
    const res = await fetch(`/api/sandboxes/${sandboxId}/files/tree`);
    const data = await res.json();
    setTree(data);
  };

  const toggleExpand = (path: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const handleFileClick = (node: FileNode) => {
    if (node.type === 'directory') {
      toggleExpand(node.path);
    } else {
      setSelected(node.path);
      onFileSelect(node.path);
    }
  };

  const renderNode = (node: FileNode, depth: number = 0) => {
    const isExpanded = expanded.has(node.path);
    const isSelected = selected === node.path;

    return (
      <div key={node.path}>
        <div
          className={cn(
            "flex items-center gap-1 py-1 px-2 cursor-pointer hover:bg-accent rounded-sm",
            isSelected && "bg-accent"
          )}
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
          onClick={() => handleFileClick(node)}
        >
          {node.type === 'directory' ? (
            <>
              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              <Folder className="h-4 w-4 text-yellow-500" />
            </>
          ) : (
            <>
              <span className="w-4" />
              <File className="h-4 w-4 text-muted-foreground" />
            </>
          )}
          <span className="text-sm truncate">{node.name}</span>
          {node.type === 'file' && node.size && (
            <span className="text-xs text-muted-foreground ml-auto">
              {formatFileSize(node.size)}
            </span>
          )}
        </div>
        {node.type === 'directory' && isExpanded && node.children && (
          <div>
            {node.children.map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (!tree) return <div className="p-4">Loading...</div>;

  return (
    <div className="h-full overflow-auto">
      <div className="p-2 border-b text-sm font-medium">EXPLORER</div>
      <div className="py-2">
        {renderNode(tree)}
      </div>
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
```

---

### Phase 2: Code Editor View

**Frontend Component:**

```tsx
// frontend/components/sandbox/CodeEditor.tsx

import { useEffect, useState } from 'react';
import Editor from '@monaco-editor/react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

interface OpenFile {
  path: string;
  content: string;
  language: string;
  modified?: boolean;
}

interface CodeEditorProps {
  sandboxId: string;
  selectedPath: string | null;
}

export function CodeEditor({ sandboxId, selectedPath }: CodeEditorProps) {
  const [openFiles, setOpenFiles] = useState<OpenFile[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);

  // Load file when selected
  useEffect(() => {
    if (selectedPath && !openFiles.find(f => f.path === selectedPath)) {
      loadFile(selectedPath);
    } else if (selectedPath) {
      setActiveFile(selectedPath);
    }
  }, [selectedPath]);

  const loadFile = async (path: string) => {
    const res = await fetch(
      `/api/sandboxes/${sandboxId}/files/read?path=${encodeURIComponent(path)}`
    );
    const data = await res.json();

    if (data.binary) {
      // Handle binary files differently
      return;
    }

    const language = getLanguageFromPath(path);

    setOpenFiles(prev => [...prev, {
      path,
      content: data.content,
      language,
    }]);
    setActiveFile(path);
  };

  const closeFile = (path: string) => {
    setOpenFiles(prev => prev.filter(f => f.path !== path));
    if (activeFile === path) {
      const remaining = openFiles.filter(f => f.path !== path);
      setActiveFile(remaining.length > 0 ? remaining[remaining.length - 1].path : null);
    }
  };

  const currentFile = openFiles.find(f => f.path === activeFile);

  return (
    <div className="h-full flex flex-col">
      {openFiles.length > 0 ? (
        <>
          {/* Tabs */}
          <div className="flex border-b bg-muted/30">
            {openFiles.map(file => (
              <div
                key={file.path}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 border-r cursor-pointer text-sm",
                  activeFile === file.path && "bg-background"
                )}
                onClick={() => setActiveFile(file.path)}
              >
                <span className={file.modified ? "italic" : ""}>
                  {file.path.split('/').pop()}
                </span>
                <button
                  className="hover:bg-accent rounded p-0.5"
                  onClick={(e) => { e.stopPropagation(); closeFile(file.path); }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          {/* Editor */}
          {currentFile && (
            <Editor
              height="100%"
              language={currentFile.language}
              value={currentFile.content}
              theme="vs-dark"
              options={{
                readOnly: true,  // Read-only initially
                minimap: { enabled: true },
                fontSize: 13,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
              }}
            />
          )}
        </>
      ) : (
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          Select a file to view
        </div>
      )}
    </div>
  );
}

function getLanguageFromPath(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase();
  const langMap: Record<string, string> = {
    'py': 'python',
    'js': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'jsx': 'javascript',
    'json': 'json',
    'md': 'markdown',
    'yaml': 'yaml',
    'yml': 'yaml',
    'sh': 'shell',
    'bash': 'shell',
    'sql': 'sql',
    'html': 'html',
    'css': 'css',
    'go': 'go',
    'rs': 'rust',
  };
  return langMap[ext || ''] || 'plaintext';
}
```

---

### Phase 3: Live Terminal Streaming (The Hard Part)

This is the most complex phase because the Daytona SDK's async streaming requires careful WebSocket integration.

**Backend Service:**

```python
# backend/omoi_os/services/sandbox_terminal_service.py

import asyncio
from typing import Callable, Optional
from dataytona import SessionExecuteRequest

from omoi_os.logging import get_logger
from omoi_os.workspace.daytona import DaytonaWorkspace

logger = get_logger(__name__)


class SandboxTerminalService:
    """Manages terminal sessions with streaming output in Daytona sandboxes."""

    def __init__(self, workspace: DaytonaWorkspace):
        self.workspace = workspace
        self.sandbox = workspace.sandbox
        self._sessions: dict[str, str] = {}  # session_name -> session_id

    def create_session(self, name: str = "main") -> str:
        """Create a persistent terminal session.

        Returns:
            Session ID for subsequent commands
        """
        session_id = f"terminal-{name}-{self.workspace.sandbox_id[:8]}"
        self.sandbox.process.create_session(session_id)
        self._sessions[name] = session_id
        logger.info(f"Created terminal session: {session_id}")
        return session_id

    async def execute_with_streaming(
        self,
        command: str,
        session_name: str = "main",
        on_output: Optional[Callable[[str], None]] = None,
        timeout: int = 300,
    ) -> dict:
        """Execute command with real-time output streaming.

        Args:
            command: Shell command to execute
            session_name: Terminal session name
            on_output: Callback for each output chunk
            timeout: Command timeout in seconds

        Returns:
            {
                "exit_code": int,
                "stdout": str (full output),
                "stderr": str,
                "duration_ms": int
            }
        """
        import time
        start_time = time.time()

        session_id = self._sessions.get(session_name)
        if not session_id:
            session_id = self.create_session(session_name)

        # Execute command asynchronously
        request = SessionExecuteRequest(
            command=command,
            var_async=True,  # Run async to enable streaming
        )

        response = self.sandbox.process.execute_session_command(
            session_id, request, timeout=timeout
        )

        full_output = []

        # Stream logs as they arrive
        if on_output:
            await self.sandbox.process.get_session_command_logs_async(
                session_id,
                response.cmd_id,
                lambda chunk: (full_output.append(chunk), on_output(chunk))
            )
        else:
            # Just collect output without streaming
            logs = self.sandbox.process.get_session_command_logs(
                session_id, response.cmd_id
            )
            full_output.append(logs)

        # Get final command result
        cmd_result = self.sandbox.process.get_session_command(
            session_id, response.cmd_id
        )

        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "exit_code": cmd_result.exit_code,
            "stdout": "".join(full_output),
            "stderr": cmd_result.stderr or "",
            "duration_ms": duration_ms,
        }

    def list_sessions(self) -> list[dict]:
        """List all active terminal sessions."""
        sessions = self.sandbox.process.list_sessions()
        return [{"id": s.id, "name": s.name} for s in sessions]

    def delete_session(self, name: str) -> bool:
        """Delete a terminal session."""
        session_id = self._sessions.pop(name, None)
        if session_id:
            self.sandbox.process.delete_session(session_id)
            return True
        return False
```

**WebSocket Handler for Terminal:**

```python
# backend/omoi_os/api/routes/sandbox_terminal.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import json
import asyncio

from omoi_os.services.sandbox_terminal_service import SandboxTerminalService

router = APIRouter(prefix="/sandboxes", tags=["sandbox-terminal"])


@router.websocket("/{sandbox_id}/terminal")
async def terminal_websocket(
    websocket: WebSocket,
    sandbox_id: str,
):
    """WebSocket endpoint for terminal streaming.

    Protocol:

    Client -> Server:
    {
        "type": "execute",
        "command": "npm test",
        "session": "main"  // optional
    }

    Server -> Client:
    {
        "type": "output",
        "data": "Running tests...\n"
    }

    {
        "type": "exit",
        "exit_code": 0,
        "duration_ms": 1247
    }
    """
    await websocket.accept()

    # Get workspace for this sandbox
    workspace = await get_sandbox_workspace_async(sandbox_id)
    terminal_service = SandboxTerminalService(workspace)

    try:
        while True:
            # Receive command from client
            message = await websocket.receive_text()
            data = json.loads(message)

            if data["type"] == "execute":
                command = data["command"]
                session = data.get("session", "main")

                # Define streaming callback
                async def send_output(chunk: str):
                    await websocket.send_json({
                        "type": "output",
                        "data": chunk
                    })

                # Execute with streaming
                result = await terminal_service.execute_with_streaming(
                    command=command,
                    session_name=session,
                    on_output=lambda c: asyncio.create_task(send_output(c)),
                )

                # Send completion message
                await websocket.send_json({
                    "type": "exit",
                    "exit_code": result["exit_code"],
                    "duration_ms": result["duration_ms"],
                })

            elif data["type"] == "list_sessions":
                sessions = terminal_service.list_sessions()
                await websocket.send_json({
                    "type": "sessions",
                    "sessions": sessions
                })

    except WebSocketDisconnect:
        logger.info(f"Terminal WebSocket disconnected: {sandbox_id}")
    finally:
        # Cleanup sessions on disconnect
        pass
```

**Frontend Terminal Component:**

```tsx
// frontend/components/sandbox/LiveTerminal.tsx

import { useEffect, useRef, useState } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

interface LiveTerminalProps {
  sandboxId: string;
}

export function LiveTerminal({ sandboxId }: LiveTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const [terminal, setTerminal] = useState<Terminal | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // Initialize terminal
  useEffect(() => {
    if (!terminalRef.current) return;

    const term = new Terminal({
      cursorBlink: true,
      theme: {
        background: '#1a1a1a',
        foreground: '#d4d4d4',
        cursor: '#d4d4d4',
      },
      fontSize: 13,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    // Handle resize
    const resizeObserver = new ResizeObserver(() => fitAddon.fit());
    resizeObserver.observe(terminalRef.current);

    setTerminal(term);

    return () => {
      resizeObserver.disconnect();
      term.dispose();
    };
  }, []);

  // Connect WebSocket
  useEffect(() => {
    if (!terminal) return;

    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/api/v1/sandboxes/${sandboxId}/terminal`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setIsConnected(true);
      terminal.writeln('\x1b[32m● Connected to sandbox terminal\x1b[0m');
      terminal.writeln('');
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'output') {
        terminal.write(data.data);
      } else if (data.type === 'exit') {
        const color = data.exit_code === 0 ? '\x1b[32m' : '\x1b[31m';
        terminal.writeln('');
        terminal.writeln(
          `${color}Process exited with code ${data.exit_code} (${data.duration_ms}ms)\x1b[0m`
        );
        terminal.writeln('');
      }
    };

    socket.onclose = () => {
      setIsConnected(false);
      terminal.writeln('\x1b[31m● Disconnected from sandbox\x1b[0m');
    };

    setWs(socket);

    return () => socket.close();
  }, [terminal, sandboxId]);

  const executeCommand = (command: string) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    terminal?.writeln(`\x1b[36m$ ${command}\x1b[0m`);

    ws.send(JSON.stringify({
      type: 'execute',
      command,
    }));
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm font-medium">Terminal</span>
        </div>
        <span className="text-xs text-muted-foreground">
          Daytona Sandbox
        </span>
      </div>

      {/* Terminal */}
      <div ref={terminalRef} className="flex-1" />

      {/* Command Input (optional - for manual commands) */}
      <CommandInput onSubmit={executeCommand} disabled={!isConnected} />
    </div>
  );
}

function CommandInput({
  onSubmit,
  disabled
}: {
  onSubmit: (cmd: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim()) {
      onSubmit(value);
      setValue('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border-t p-2">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder="Enter command..."
        className="w-full bg-transparent text-sm outline-none"
      />
    </form>
  );
}
```

---

### Phase 4: File Watching

**Backend Implementation:**

```python
# backend/omoi_os/services/sandbox_file_watcher.py

import asyncio
from typing import Callable

from omoi_os.workspace.daytona import DaytonaWorkspace
from omoi_os.logging import get_logger

logger = get_logger(__name__)


class SandboxFileWatcher:
    """Watch for file changes in a Daytona sandbox."""

    def __init__(self, workspace: DaytonaWorkspace, watch_path: str = "/home/daytona"):
        self.workspace = workspace
        self.watch_path = watch_path
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self, on_change: Callable[[dict], None]):
        """Start watching for file changes.

        Args:
            on_change: Callback for file changes
                {
                    "event": "modify" | "create" | "delete",
                    "path": "/home/daytona/src/main.py",
                    "timestamp": "2025-01-20T10:30:45Z"
                }
        """
        self._running = True

        # Start inotifywait in sandbox
        cmd = f"inotifywait -r -m {self.watch_path} -e modify,create,delete --format '%e %w%f' 2>/dev/null"

        session_id = "file-watcher"
        self.workspace.sandbox.process.create_session(session_id)

        request = SessionExecuteRequest(command=cmd, var_async=True)
        response = self.workspace.sandbox.process.execute_session_command(
            session_id, request
        )

        # Stream inotify events
        async def process_events(chunk: str):
            if not self._running:
                return

            for line in chunk.strip().split("\n"):
                if not line:
                    continue

                parts = line.split(" ", 1)
                if len(parts) != 2:
                    continue

                event_type, path = parts

                # Map inotify events
                event_map = {
                    "MODIFY": "modify",
                    "CREATE": "create",
                    "DELETE": "delete",
                }

                event = event_map.get(event_type.upper())
                if event:
                    on_change({
                        "event": event,
                        "path": path,
                        "timestamp": utc_now().isoformat(),
                    })

        await self.workspace.sandbox.process.get_session_command_logs_async(
            session_id, response.cmd_id, process_events
        )

    def stop(self):
        """Stop file watching."""
        self._running = False
```

---

## Complete Integration: Full Dev Environment View

```tsx
// frontend/app/sandbox/[id]/dev/page.tsx

import { useState } from 'react';
import { FileExplorer } from '@/components/sandbox/FileExplorer';
import { CodeEditor } from '@/components/sandbox/CodeEditor';
import { LiveTerminal } from '@/components/sandbox/LiveTerminal';
import { ResizablePanel, ResizablePanelGroup, ResizableHandle } from '@/components/ui/resizable';

export default function SandboxDevEnvironmentPage({
  params
}: {
  params: { id: string }
}) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="h-12 border-b flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <h1 className="font-semibold">Full Dev Environment Access</h1>
          <span className="text-sm text-muted-foreground">
            Sandbox: {params.id}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-green-500" />
          <span className="text-sm">Live</span>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          {/* File Explorer */}
          <ResizablePanel defaultSize={20} minSize={15}>
            <FileExplorer
              sandboxId={params.id}
              onFileSelect={setSelectedFile}
            />
          </ResizablePanel>

          <ResizableHandle />

          {/* Editor + Terminal */}
          <ResizablePanel defaultSize={80}>
            <ResizablePanelGroup direction="vertical">
              {/* Code Editor */}
              <ResizablePanel defaultSize={60}>
                <CodeEditor
                  sandboxId={params.id}
                  selectedPath={selectedFile}
                />
              </ResizablePanel>

              <ResizableHandle />

              {/* Terminal */}
              <ResizablePanel defaultSize={40}>
                <LiveTerminal sandboxId={params.id} />
              </ResizablePanel>
            </ResizablePanelGroup>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
}
```

---

## Implementation Timeline

| Phase | Effort | Dependencies | Priority |
|-------|--------|--------------|----------|
| **Phase 1: File Explorer** | 4-6 hours | None | High |
| **Phase 2: Code Editor** | 2-3 hours | Phase 1 | High |
| **Phase 3: Terminal Streaming** | 6-8 hours | Phase 1 | Medium |
| **Phase 4: File Watching** | 3-4 hours | Phase 3 | Low |
| **Integration & Polish** | 4-6 hours | All | Final |

**Total Estimated Effort**: 19-27 hours

---

## Technical Considerations

### Performance

1. **File Tree Pagination** - Large workspaces should paginate/lazy-load subdirectories
2. **File Size Limits** - Cap file viewing at ~1MB; offer download for larger files
3. **WebSocket Reconnection** - Implement exponential backoff for terminal reconnects
4. **Debounce File Watcher** - Batch rapid file changes (100ms debounce)

### Security

1. **Path Traversal** - Validate all file paths are within sandbox workspace
2. **Binary Files** - Detect and handle binary files appropriately
3. **Sensitive Files** - Consider filtering `.env`, credentials from tree
4. **Rate Limiting** - Limit file read requests per minute

### UX Considerations

1. **Loading States** - Show skeletons while tree/files load
2. **Error Handling** - Graceful degradation if sandbox disconnects
3. **Mobile Support** - Consider collapsed sidebar on mobile
4. **Keyboard Navigation** - Arrow keys for tree, Cmd+P for file search

---

## Future Enhancements

1. **LSP Integration** - Use Daytona's `create_lsp_server()` for:
   - Autocomplete in editor
   - Go to definition
   - Hover documentation
   - Error highlighting

2. **Git Integration** - Show git status in file explorer:
   - Modified files highlighted
   - Diff viewer in editor
   - Commit history sidebar

3. **Collaborative Editing** - Real-time cursors when multiple users view same sandbox

4. **Terminal History** - Persist terminal output across sessions

5. **File Editing** - Allow users to edit files (with agent conflict resolution)

---

## References

- [Daytona Python SDK - FileSystem Operations](https://www.daytona.io/docs/python-sdk/file-system/)
- [Daytona Python SDK - Process Execution](https://www.daytona.io/docs/en/python-sdk/sync/process/)
- [Daytona Log Streaming Guide](https://github.com/daytonaio/daytona/blob/main/apps/docs/src/content/docs/log-streaming.mdx)
- [Monaco Editor React](https://github.com/suren-atoyan/monaco-react)
- [xterm.js](https://xtermjs.org/)
