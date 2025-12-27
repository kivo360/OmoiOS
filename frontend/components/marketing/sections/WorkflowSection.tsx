"use client"

import { motion } from "framer-motion"
import { Search, Pencil, ListChecks, Code2, CheckCircle2 } from "lucide-react"
import { Card } from "@/components/ui/card"
import { TicketJourney } from "@/components/landing/TicketJourney"
import { cn } from "@/lib/utils"

const phases = [
  {
    id: "requirements",
    number: "01",
    title: "Requirements",
    description:
      "Describe your feature in plain English. AI generates structured requirements (EARS-style).",
    icon: Search,
    color: "bg-blue-500",
  },
  {
    id: "design",
    number: "02",
    title: "Design",
    description:
      "Architecture diagrams, data models, and implementation plan. Review and approve before any code.",
    icon: Pencil,
    color: "bg-purple-500",
  },
  {
    id: "tasks",
    number: "03",
    title: "Planning",
    description:
      "Discrete tasks with dependencies auto-generated. Kanban board populates automatically.",
    icon: ListChecks,
    color: "bg-amber-500",
  },
  {
    id: "execution",
    number: "04",
    title: "Execution",
    description:
      "Agents write code, run tests, self-correct. PR created when done—you just review.",
    icon: Code2,
    color: "bg-green-500",
  },
]

interface WorkflowSectionProps {
  className?: string
}

export function WorkflowSection({ className }: WorkflowSectionProps) {
  return (
    <section className={cn("bg-landing-bg py-20 md:py-32", className)} id="how-it-works">
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-16 max-w-2xl text-center"
        >
          <h2 className="text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            From idea to merged PR in 4 phases
          </h2>
          <p className="mt-4 text-lg text-landing-text-muted">
            OmoiOS uses spec-driven development to ensure quality at every step
          </p>
        </motion.div>

        {/* Phase Steps */}
        <div className="mx-auto mb-16 max-w-4xl">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {phases.map((phase, i) => (
              <motion.div
                key={phase.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <Card className="relative h-full border-landing-border bg-white p-6 transition-all hover:shadow-lg">
                  {/* Phase Number */}
                  <div className="mb-4 text-4xl font-bold text-landing-bg-muted">
                    {phase.number}
                  </div>

                  {/* Icon */}
                  <div
                    className={cn(
                      "mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg",
                      phase.color
                    )}
                  >
                    <phase.icon className="h-5 w-5 text-white" />
                  </div>

                  {/* Content */}
                  <h3 className="mb-2 text-lg font-semibold text-landing-text">
                    {phase.title}
                  </h3>
                  <p className="text-sm text-landing-text-muted">{phase.description}</p>

                  {/* Connector Arrow (hidden on last item) */}
                  {i < phases.length - 1 && (
                    <div className="absolute -right-3 top-1/2 hidden -translate-y-1/2 lg:block">
                      <svg
                        className="h-6 w-6 text-landing-border"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </div>
                  )}
                </Card>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Live Demo: Ticket Journey */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto max-w-5xl"
          id="demo"
        >
          <div className="mb-8 text-center">
            <h3 className="text-xl font-semibold text-landing-text">
              Watch a Ticket Come to Life
            </h3>
            <p className="mt-2 text-landing-text-muted">
              See how a single feature request flows through autonomous phases
            </p>
          </div>

          <Card className="overflow-hidden border-landing-border bg-white p-6 md:p-8">
            <TicketJourney
              autoPlay={true}
              speed="normal"
              showPhaseInstructions={true}
              showFeedbackLoops={true}
            />
          </Card>
        </motion.div>
      </div>
    </section>
  )
}
