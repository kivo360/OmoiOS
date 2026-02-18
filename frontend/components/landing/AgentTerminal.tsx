"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, Circle } from "lucide-react";
import { cn } from "@/lib/utils";

interface TerminalEntry {
  timestamp: string;
  agentId: string;
  action: string;
  status: "thinking" | "coding" | "testing" | "committing" | "complete";
}

const terminalSequence: TerminalEntry[] = [
  {
    timestamp: "02:47:12",
    agentId: "Agent-Architect",
    action: "Analyzing requirements → Breaking into 5 tasks...",
    status: "thinking",
  },
  {
    timestamp: "02:47:45",
    agentId: "Agent-Dev-1",
    action: "Implementing auth middleware...",
    status: "coding",
  },
  {
    timestamp: "02:48:22",
    agentId: "Agent-Dev-2",
    action: "Writing unit tests for /api/login...",
    status: "testing",
  },
  {
    timestamp: "02:49:01",
    agentId: "Agent-Dev-1",
    action: "✓ Tests passing (12/12)",
    status: "complete",
  },
  {
    timestamp: "02:49:33",
    agentId: "Agent-Orchestrator",
    action: "Opening PR #147: 'Add JWT authentication'",
    status: "committing",
  },
];

const statusColors: Record<TerminalEntry["status"], string> = {
  thinking: "#FFD93D", // Yellow
  coding: "#00FF41", // Green
  testing: "#0366D6", // Blue
  committing: "#A855F7", // Purple
  complete: "#00FF41", // Green
};

interface AgentTerminalProps {
  className?: string;
  autoPlay?: boolean;
  speed?: "slow" | "normal" | "fast";
}

export function AgentTerminal({
  className,
  autoPlay = true,
  speed = "normal",
}: AgentTerminalProps) {
  const [visibleEntries, setVisibleEntries] = useState<number>(0);
  const [currentText, setCurrentText] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const speedMultiplier = speed === "slow" ? 2 : speed === "fast" ? 0.5 : 1;

  useEffect(() => {
    if (!autoPlay) return;

    const showNextEntry = () => {
      if (visibleEntries >= terminalSequence.length) {
        // Reset after delay
        setTimeout(() => {
          setVisibleEntries(0);
          setCurrentText("");
        }, 3000 * speedMultiplier);
        return;
      }

      setIsTyping(true);
      const entry = terminalSequence[visibleEntries];
      let charIndex = 0;

      // Type out the action text
      const typeInterval = setInterval(() => {
        if (charIndex <= entry.action.length) {
          setCurrentText(entry.action.slice(0, charIndex));
          charIndex++;
        } else {
          clearInterval(typeInterval);
          setIsTyping(false);
          setVisibleEntries((prev) => prev + 1);
        }
      }, 30 * speedMultiplier);

      return () => clearInterval(typeInterval);
    };

    const entryDelay = setTimeout(showNextEntry, 2000 * speedMultiplier);

    return () => clearTimeout(entryDelay);
  }, [autoPlay, visibleEntries, speedMultiplier]);

  return (
    <div
      className={cn(
        "overflow-hidden rounded-lg border border-[#333] bg-[#0D0D0D]",
        className,
      )}
    >
      {/* Terminal Header */}
      <div className="flex items-center justify-between border-b border-[#333] px-4 py-2">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-[#00FF41]" />
          <span className="font-mono text-xs text-muted-foreground">
            OmoiOS Agent Activity
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-3 w-3 rounded-full bg-[#FF5F57]" />
          <div className="h-3 w-3 rounded-full bg-[#FFBD2E]" />
          <div className="h-3 w-3 rounded-full bg-[#28CA41]" />
        </div>
      </div>

      {/* Terminal Content */}
      <div className="h-64 overflow-hidden p-4 font-mono text-sm">
        <AnimatePresence mode="popLayout">
          {terminalSequence.slice(0, visibleEntries).map((entry, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0.5 }}
              transition={{ duration: 0.3 }}
              className="mb-2 flex items-start gap-3"
            >
              {/* Timestamp */}
              <span className="text-muted-foreground/50">
                [{entry.timestamp}]
              </span>

              {/* Status indicator */}
              <Circle
                className="mt-1 h-2 w-2 flex-shrink-0"
                fill={statusColors[entry.status]}
                color={statusColors[entry.status]}
              />

              {/* Agent ID */}
              <span className="text-[#0366D6]">{entry.agentId}:</span>

              {/* Action */}
              <span
                className={cn(
                  entry.status === "complete" && "text-[#00FF41]",
                  entry.status !== "complete" && "text-[#E5E5E5]",
                )}
              >
                {entry.action}
              </span>
            </motion.div>
          ))}

          {/* Current typing line */}
          {isTyping && visibleEntries < terminalSequence.length && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-start gap-3"
            >
              <span className="text-muted-foreground/50">
                [{terminalSequence[visibleEntries].timestamp}]
              </span>
              <Circle
                className="mt-1 h-2 w-2 flex-shrink-0 animate-pulse"
                fill={statusColors[terminalSequence[visibleEntries].status]}
                color={statusColors[terminalSequence[visibleEntries].status]}
              />
              <span className="text-[#0366D6]">
                {terminalSequence[visibleEntries].agentId}:
              </span>
              <span className="text-[#E5E5E5]">
                {currentText}
                <motion.span
                  className="inline-block w-2 bg-[#00FF41]"
                  animate={{ opacity: [1, 0] }}
                  transition={{ duration: 0.5, repeat: Infinity }}
                >
                  _
                </motion.span>
              </span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Waiting for next cycle */}
        {visibleEntries >= terminalSequence.length && !isTyping && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 text-center text-muted-foreground"
          >
            <span className="animate-pulse">Cycle complete. Restarting...</span>
          </motion.div>
        )}
      </div>

      {/* Status Bar */}
      <div className="flex items-center justify-between border-t border-[#333] px-4 py-2">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Circle className="h-2 w-2" fill="#00FF41" color="#00FF41" />
            <span>4 agents active</span>
          </div>
          <div className="flex items-center gap-1">
            <span>5 tasks in queue</span>
          </div>
        </div>
        <div className="text-xs text-muted-foreground">
          Last commit: 2 min ago
        </div>
      </div>
    </div>
  );
}
