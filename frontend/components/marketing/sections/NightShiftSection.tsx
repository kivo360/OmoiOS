"use client"

import { motion } from "framer-motion"
import { Moon } from "lucide-react"
import { NightShiftLog } from "@/components/landing/NightShiftLog"
import { cn } from "@/lib/utils"

interface NightShiftSectionProps {
  className?: string
}

export function NightShiftSection({ className }: NightShiftSectionProps) {
  return (
    <section className={cn("bg-landing-bg-muted py-16 md:py-24", className)}>
      <div className="container mx-auto px-4">
        <div className="mx-auto max-w-4xl">
          {/* Section Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mb-12 text-center"
          >
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-landing-accent/10 px-4 py-2">
              <Moon className="h-4 w-4 text-landing-accent" />
              <span className="text-sm font-medium text-landing-accent">
                Work Happens While You Rest
              </span>
            </div>
            <h2 className="text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
              Go to Bed. Wake Up to Done.
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-lg text-landing-text-muted">
              Describe what you need before you leave for the day.
              Check your inbox in the morning for a PR ready to review.
            </p>
          </motion.div>

          {/* Night Shift Log Animation */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
          >
            <NightShiftLog autoPlay={true} className="border-landing-border" />
          </motion.div>

          {/* Stats Below */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.4 }}
            className="mt-8 grid grid-cols-3 gap-4 text-center"
          >
            {[
              { value: "2h 28m", label: "of work done for you" },
              { value: "5", label: "steps you didn't manage" },
              { value: "1", label: "PR ready to merge" },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-2xl font-bold text-landing-text">{stat.value}</div>
                <div className="text-sm text-landing-text-muted">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  )
}
