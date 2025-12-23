"use client"

import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

interface AnimatedCheckboxProps {
  checked: boolean
  label: string
  delay?: number
  className?: string
}

export function AnimatedCheckbox({
  checked,
  label,
  delay = 0,
  className,
}: AnimatedCheckboxProps) {
  return (
    <motion.div
      className={cn("flex items-center gap-2", className)}
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.3 }}
    >
      <div className="relative h-4 w-4 flex-shrink-0">
        {/* Checkbox background */}
        <motion.div
          className={cn(
            "h-4 w-4 rounded border-2 transition-colors duration-200",
            checked
              ? "border-success bg-success/10"
              : "border-muted-foreground/50 bg-transparent"
          )}
          animate={checked ? { scale: [1, 1.1, 1] } : {}}
          transition={{ duration: 0.2 }}
        />

        {/* Checkmark SVG */}
        {checked && (
          <svg
            className="absolute inset-0 h-4 w-4 text-success"
            viewBox="0 0 16 16"
            fill="none"
          >
            <motion.path
              d="M3 8.5L6.5 12L13 4"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.3, delay: delay + 0.1, ease: "easeOut" }}
            />
          </svg>
        )}
      </div>

      {/* Label */}
      <motion.span
        className={cn(
          "text-sm transition-colors duration-200",
          checked ? "text-success" : "text-muted-foreground"
        )}
        animate={checked ? { opacity: 1 } : { opacity: 0.7 }}
      >
        {label}
      </motion.span>

      {/* Glow effect on completion */}
      {checked && (
        <motion.div
          className="absolute -inset-1 rounded bg-success/20 blur-sm"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: [0, 0.5, 0], scale: [0.8, 1.2, 1] }}
          transition={{ duration: 0.5, delay }}
        />
      )}
    </motion.div>
  )
}
