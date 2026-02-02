"use client"

import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Terminal, Copy, Check } from "lucide-react"
import { cn } from "@/lib/utils"

interface CLIDemoProps {
  className?: string
}

const cliSequence = [
  { type: "command", text: '$ omi task "Add Stripe checkout to the billing page"' },
  { type: "output", text: "" },
  { type: "output", text: "✓ Analyzing requirements...", delay: 500 },
  { type: "output", text: "✓ Created Ticket FEAT-201", delay: 800 },
  { type: "output", text: "✓ Decomposed into 4 tasks", delay: 400 },
  { type: "output", text: "✓ Spawning 4 agents...", delay: 600 },
  { type: "output", text: "" },
  {
    type: "agent",
    text: "Agent-1: Implementing StripeCheckoutButton component",
    delay: 300,
  },
  {
    type: "agent",
    text: "Agent-2: Adding /api/checkout/session endpoint",
    delay: 200,
  },
  { type: "agent", text: "Agent-3: Writing integration tests", delay: 200 },
  { type: "agent", text: "Agent-4: Updating billing page layout", delay: 200 },
  { type: "output", text: "" },
  { type: "progress", text: "[████████████████████░░░░] 78% complete", delay: 1000 },
  { type: "output", text: "" },
  { type: "success", text: "✓ All tasks completed successfully!", delay: 1500 },
  { type: "success", text: "✓ PR #203 opened: 'Add Stripe checkout flow'", delay: 500 },
  { type: "link", text: "  → https://github.com/your-org/repo/pull/203", delay: 300 },
]

export function CLIDemo({ className }: CLIDemoProps) {
  const [visibleLines, setVisibleLines] = useState<number>(0)
  const [copied, setCopied] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [typedCommand, setTypedCommand] = useState("")

  useEffect(() => {
    // Type out the command first
    const command = cliSequence[0].text
    let charIndex = 0

    setIsTyping(true)
    const typeInterval = setInterval(() => {
      if (charIndex <= command.length) {
        setTypedCommand(command.slice(0, charIndex))
        charIndex++
      } else {
        clearInterval(typeInterval)
        setIsTyping(false)
        setVisibleLines(1)

        // Then show subsequent lines with delays
        let lineIndex = 1
        const showNextLine = () => {
          if (lineIndex < cliSequence.length) {
            const delay = cliSequence[lineIndex].delay || 100
            setTimeout(() => {
              setVisibleLines(lineIndex + 1)
              lineIndex++
              showNextLine()
            }, delay)
          }
        }
        setTimeout(showNextLine, 500)
      }
    }, 40)

    return () => clearInterval(typeInterval)
  }, [])

  const copyCommand = () => {
    navigator.clipboard.writeText('omi task "Add Stripe checkout to the billing page"')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const getLineColor = (type: string) => {
    switch (type) {
      case "command":
        return "text-white"
      case "output":
        return "text-[#00FF41]"
      case "agent":
        return "text-[#0366D6]"
      case "progress":
        return "text-[#FFD93D]"
      case "success":
        return "text-[#00FF41]"
      case "link":
        return "text-[#A855F7]"
      default:
        return "text-[#999]"
    }
  }

  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border border-[#333] bg-[#0D0D0D]",
        className
      )}
    >
      {/* Terminal Header */}
      <div className="flex items-center justify-between border-b border-[#333] px-4 py-2">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-[#00FF41]" />
          <span className="font-mono text-xs text-[#999]">terminal</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={copyCommand}
            className="flex items-center gap-1 rounded px-2 py-1 text-xs text-[#999] transition-colors hover:bg-[#333] hover:text-white"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3 text-[#00FF41]" />
                <span className="text-[#00FF41]">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                <span>Copy</span>
              </>
            )}
          </button>
          <div className="flex items-center gap-1.5">
            <div className="h-3 w-3 rounded-full bg-[#FF5F57]" />
            <div className="h-3 w-3 rounded-full bg-[#FFBD2E]" />
            <div className="h-3 w-3 rounded-full bg-[#28CA41]" />
          </div>
        </div>
      </div>

      {/* Terminal Content */}
      <div className="min-h-[320px] p-4 font-mono text-sm">
        {/* Command line (typing effect) */}
        <div className="mb-2 text-white">
          {typedCommand}
          {isTyping && (
            <motion.span
              className="inline-block w-2 bg-[#00FF41]"
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.5, repeat: Infinity }}
            >
              _
            </motion.span>
          )}
        </div>

        {/* Output lines */}
        <AnimatePresence mode="popLayout">
          {cliSequence.slice(1, visibleLines).map((line, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className={cn("leading-relaxed", getLineColor(line.type))}
            >
              {line.text || "\u00A0"}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Cursor at end */}
        {visibleLines >= cliSequence.length && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 text-white"
          >
            ${" "}
            <motion.span
              className="inline-block w-2 bg-[#00FF41]"
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.5, repeat: Infinity }}
            >
              _
            </motion.span>
          </motion.div>
        )}
      </div>
    </div>
  )
}
