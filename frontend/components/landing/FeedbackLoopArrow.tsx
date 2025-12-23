"use client"

import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"

interface FeedbackLoopArrowProps {
  show: boolean
  fromPhase: "testing" | "implementation"
  toPhase: "implementation" | "requirements"
  message?: string
  className?: string
}

export function FeedbackLoopArrow({
  show,
  fromPhase,
  toPhase,
  message = "Spawning fix task...",
  className,
}: FeedbackLoopArrowProps) {
  // Calculate path based on phases
  const getPath = () => {
    if (fromPhase === "testing" && toPhase === "implementation") {
      // Curved path from testing back to implementation
      return "M 380,60 C 340,120 260,120 220,60"
    }
    if (fromPhase === "implementation" && toPhase === "requirements") {
      // Curved path from implementation back to requirements
      return "M 220,60 C 180,120 100,120 60,60"
    }
    return "M 300,50 C 250,100 150,100 100,50"
  }

  const path = getPath()

  return (
    <AnimatePresence>
      {show && (
        <div className={cn("absolute inset-0 pointer-events-none", className)}>
          <svg
            className="h-full w-full"
            viewBox="0 0 500 150"
            preserveAspectRatio="xMidYMid meet"
          >
            {/* Glow filter */}
            <defs>
              <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Background dashed path (static) */}
            <motion.path
              d={path}
              fill="none"
              className="stroke-destructive"
              strokeWidth={2}
              strokeDasharray="8 4"
              strokeOpacity={0.3}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            />

            {/* Animated drawing path */}
            <motion.path
              d={path}
              fill="none"
              className="stroke-destructive"
              strokeWidth={2}
              strokeDasharray="8 4"
              filter="url(#glow)"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              exit={{ pathLength: 0 }}
              transition={{ duration: 1, ease: "easeInOut" }}
            />

            {/* Arrowhead */}
            <motion.polygon
              points="55,55 65,60 60,70"
              className="fill-destructive"
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0 }}
              transition={{ delay: 0.8, duration: 0.2 }}
            />
          </svg>

          {/* Traveling error icon */}
          <motion.div
            className="absolute"
            style={{
              offsetPath: `path("${path}")`,
            }}
            initial={{ offsetDistance: "0%" }}
            animate={{ offsetDistance: "100%" }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.2, ease: "easeInOut" }}
          >
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-destructive text-xs text-destructive-foreground">
              !
            </div>
          </motion.div>

          {/* Message label */}
          <motion.div
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ delay: 0.5, duration: 0.3 }}
          >
            <div className="rounded bg-destructive/20 px-3 py-1 font-mono text-xs text-destructive">
              {message}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}

// Simplified version for inline use
export function SimpleFeedbackArrow({
  show,
  className,
}: {
  show: boolean
  className?: string
}) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className={cn("flex items-center gap-1 text-destructive", className)}
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -10 }}
        >
          <motion.div
            className="h-0.5 bg-destructive"
            initial={{ width: 0 }}
            animate={{ width: 40 }}
            transition={{ duration: 0.5 }}
          />
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            ←
          </motion.span>
          <motion.span
            className="font-mono text-xs"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            fix
          </motion.span>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
