"use client"

import { motion, AnimatePresence } from "framer-motion"
import { FileText } from "lucide-react"
import { AnimatedCheckbox } from "./AnimatedCheckbox"
import { cn } from "@/lib/utils"

export interface DoneCriterion {
  label: string
  completed: boolean
  animationDelay: number
}

interface PhaseInstructionsPanelProps {
  phaseName: string
  phaseEmoji: string
  instructions: string[]
  doneCriteria: DoneCriterion[]
  isActive: boolean
  className?: string
}

export function PhaseInstructionsPanel({
  phaseName,
  phaseEmoji,
  instructions,
  doneCriteria,
  isActive,
  className,
}: PhaseInstructionsPanelProps) {
  return (
    <AnimatePresence mode="wait">
      {isActive && (
        <motion.div
          className={cn(
            "rounded-lg border border-border bg-card p-4",
            className
          )}
          initial={{ opacity: 0, y: -20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          transition={{ duration: 0.3 }}
        >
          {/* Header */}
          <div className="mb-3 flex items-center gap-2 border-b border-border pb-2">
            <FileText className="h-4 w-4 text-primary" />
            <span className="font-mono text-xs uppercase tracking-wider text-primary">
              Phase Instructions
            </span>
          </div>

          {/* Phase Name */}
          <div className="mb-4">
            <span className="text-lg font-semibold text-foreground">
              {phaseEmoji} {phaseName}
            </span>
          </div>

          {/* Instructions */}
          <div className="mb-4">
            <div className="mb-2 font-mono text-xs text-muted-foreground">
              Agent receives:
            </div>
            <div className="rounded border border-border bg-muted p-3">
              <ul className="space-y-2">
                {instructions.map((instruction, i) => (
                  <motion.li
                    key={i}
                    className="flex items-start gap-2 text-sm text-foreground"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 + 0.2, duration: 0.3 }}
                  >
                    <span className="mt-1 text-primary">•</span>
                    <TypewriterInstruction text={instruction} delay={i * 150} />
                  </motion.li>
                ))}
              </ul>
            </div>
          </div>

          {/* Done Criteria */}
          <div>
            <div className="mb-2 font-mono text-xs text-muted-foreground">
              Done when:
            </div>
            <div className="space-y-2">
              {doneCriteria.map((criterion, i) => (
                <AnimatedCheckbox
                  key={i}
                  checked={criterion.completed}
                  label={criterion.label}
                  delay={criterion.animationDelay / 1000}
                />
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

// Typewriter effect for instructions
function TypewriterInstruction({
  text,
  delay = 0,
}: {
  text: string
  delay?: number
}) {
  return (
    <motion.span
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: delay / 1000, duration: 0.2 }}
    >
      {text}
    </motion.span>
  )
}
