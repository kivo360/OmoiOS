"use client"

import { motion } from "framer-motion"
import { User, Bot, Code2, Rocket, GitPullRequest, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface WorkflowDiagramProps {
  className?: string
}

const agents = [
  {
    id: "architect",
    name: "Architect Agent",
    icon: <Bot className="h-5 w-5" />,
    colorClass: "text-primary",
    borderClass: "border-primary",
    bgClass: "bg-primary/10",
    description: "Analyzes requirements, creates tickets",
    output: "Requirements + Tickets",
  },
  {
    id: "developer",
    name: "Developer Agents",
    icon: <Code2 className="h-5 w-5" />,
    colorClass: "text-info",
    borderClass: "border-info",
    bgClass: "bg-info/10",
    description: "Parallel execution in sandboxes",
    output: "Tested Code",
    isParallel: true,
  },
  {
    id: "release",
    name: "Release Agent",
    icon: <Rocket className="h-5 w-5" />,
    colorClass: "text-primary",
    borderClass: "border-primary",
    bgClass: "bg-primary/10",
    description: "Git workflows, PR creation",
    output: "Pull Request",
  },
]

export function WorkflowDiagram({ className }: WorkflowDiagramProps) {
  return (
    <div className={cn("relative", className)}>
      {/* Connection lines */}
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full"
        preserveAspectRatio="none"
        viewBox="0 0 800 200"
      >
        {/* Static lines */}
        <path
          d="M 100,100 L 300,100"
          className="stroke-border"
          strokeWidth="2"
          fill="none"
        />
        <path
          d="M 380,100 L 500,100"
          className="stroke-border"
          strokeWidth="2"
          fill="none"
        />
        <path
          d="M 580,100 L 700,100"
          className="stroke-border"
          strokeWidth="2"
          fill="none"
        />

        {/* Animated flow particles */}
        <motion.circle
          cx="0"
          cy="0"
          r="4"
          className="fill-primary"
          animate={{
            cx: [100, 300, 300],
            opacity: [0, 1, 0],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "linear",
          }}
        >
          <animateMotion
            path="M 100,100 L 300,100"
            dur="1.5s"
            repeatCount="indefinite"
          />
        </motion.circle>

        <motion.circle
          cx="0"
          cy="0"
          r="4"
          className="fill-info"
          animate={{
            opacity: [0, 1, 0],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            delay: 0.5,
            ease: "linear",
          }}
        >
          <animateMotion
            path="M 380,100 L 500,100"
            dur="1.5s"
            repeatCount="indefinite"
            begin="0.5s"
          />
        </motion.circle>

        <motion.circle
          cx="0"
          cy="0"
          r="4"
          className="fill-primary"
          animate={{
            opacity: [0, 1, 0],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            delay: 1,
            ease: "linear",
          }}
        >
          <animateMotion
            path="M 580,100 L 700,100"
            dur="1.5s"
            repeatCount="indefinite"
            begin="1s"
          />
        </motion.circle>
      </svg>

      <div className="relative flex items-center justify-between px-4">
        {/* Input */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="flex flex-col items-center"
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-xl border-2 border-border bg-muted">
            <User className="h-6 w-6 text-muted-foreground" />
          </div>
          <div className="mt-2 text-center">
            <div className="text-sm font-medium text-foreground">Input</div>
            <div className="text-xs text-muted-foreground">"Add auth"</div>
          </div>
        </motion.div>

        {/* Agents */}
        {agents.map((agent, index) => (
          <motion.div
            key={agent.id}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: index * 0.2 }}
            className="flex flex-col items-center"
          >
            <div
              className={cn(
                "relative flex h-16 w-16 items-center justify-center rounded-xl border-2",
                agent.borderClass,
                agent.bgClass
              )}
            >
              <div className={agent.colorClass}>{agent.icon}</div>

              {/* Parallel indicator */}
              {agent.isParallel && (
                <div className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-info text-[10px] font-bold text-primary-foreground">
                  3x
                </div>
              )}
            </div>
            <div className="mt-2 text-center">
              <div className="text-sm font-medium text-foreground">{agent.name}</div>
              <div className="text-xs text-muted-foreground">{agent.output}</div>
            </div>
          </motion.div>
        ))}

        {/* Output */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.8 }}
          className="flex flex-col items-center"
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-xl border-2 border-success bg-success/10">
            <GitPullRequest className="h-6 w-6 text-success" />
          </div>
          <div className="mt-2 text-center">
            <div className="text-sm font-medium text-foreground">Output</div>
            <div className="text-xs text-success">PR Ready</div>
          </div>
        </motion.div>
      </div>

      {/* Human in the loop callout */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 1 }}
        className="mx-auto mt-8 max-w-md"
      >
        <div className="flex items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-muted/50 px-4 py-3">
          <CheckCircle2 className="h-4 w-4 text-success" />
          <span className="text-sm text-muted-foreground">
            <span className="text-foreground">Human-in-the-Loop:</span> You review the
            final PR
          </span>
        </div>
      </motion.div>
    </div>
  )
}
