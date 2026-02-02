"use client"

import { useEffect, useState, useRef } from "react"
import { motion, useInView } from "framer-motion"
import { cn } from "@/lib/utils"

const stats = [
  {
    value: 10,
    suffix: "x",
    label: "faster shipping",
    description: "idea to PR in hours, not weeks",
  },
  {
    value: 85,
    suffix: "%",
    label: "less busywork",
    description: "more building, less managing",
  },
  {
    value: 24,
    suffix: "/7",
    label: "work gets done",
    description: "even while you sleep",
  },
  {
    value: 0,
    suffix: "",
    label: "babysitting required",
    description: "problems fix themselves",
  },
]

interface StatsSectionProps {
  className?: string
}

export function StatsSection({ className }: StatsSectionProps) {
  return (
    <section className={cn("bg-landing-bg-warm py-20 md:py-28", className)}>
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-12 max-w-2xl text-center"
        >
          <h2 className="text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            What You Actually Get
          </h2>
          <p className="mt-4 text-lg text-landing-text-muted">
            More time for what matters. Less time on what doesn&apos;t.
          </p>
        </motion.div>

        {/* Stats Grid */}
        <div className="mx-auto grid max-w-4xl grid-cols-2 gap-6 md:grid-cols-4">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="text-center"
            >
              <AnimatedCounter
                value={stat.value}
                suffix={stat.suffix}
                className="text-4xl font-bold text-landing-accent md:text-5xl"
              />
              <div className="mt-2 font-medium text-landing-text">{stat.label}</div>
              <div className="text-sm text-landing-text-muted">{stat.description}</div>
            </motion.div>
          ))}
        </div>

        {/* Testimonial Quote */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
          className="mx-auto mt-16 max-w-2xl text-center"
        >
          <blockquote className="text-lg italic text-landing-text-muted">
            &ldquo;I wrote what I wanted Monday morning. Had a working PR to review by lunch.
            I didn&apos;t touch a board, chase updates, or attend a single standup.&rdquo;
          </blockquote>
          <cite className="mt-4 block text-sm text-landing-text-subtle">
            — Engineering Lead, Series A Startup
          </cite>
        </motion.div>
      </div>
    </section>
  )
}

// Animated Counter Component
function AnimatedCounter({
  value,
  suffix,
  className,
}: {
  value: number
  suffix: string
  className?: string
}) {
  const [count, setCount] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true })

  useEffect(() => {
    if (!isInView) return

    const duration = 2000 // ms
    const steps = 60
    const stepDuration = duration / steps
    const increment = value / steps

    let current = 0
    const timer = setInterval(() => {
      current += increment
      if (current >= value) {
        setCount(value)
        clearInterval(timer)
      } else {
        setCount(Math.floor(current))
      }
    }, stepDuration)

    return () => clearInterval(timer)
  }, [isInView, value])

  return (
    <span ref={ref} className={className}>
      {count}
      {suffix}
    </span>
  )
}
