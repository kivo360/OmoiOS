"use client"

import { motion } from "framer-motion"
import { Pencil, ListChecks, Moon, CheckCircle2 } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TicketJourney } from "@/components/landing/TicketJourney"
import { cn } from "@/lib/utils"

const phases = [
  {
    id: "spec",
    number: "01",
    title: "You Write a Spec",
    description:
      "Describe the feature in plain English. Add constraints like tech stack, architecture rules, or coding standards. The spec becomes the agent's guardrails.",
    icon: Pencil,
    color: "bg-purple-500",
    highlight: "Spec-driven constraints",
  },
  {
    id: "plan",
    number: "02",
    title: "We Plan the Work",
    description:
      "Your spec becomes tickets and tasks with clear dependencies. You see exactly what will be built and in what order. Approve or adjust before any code is written.",
    icon: ListChecks,
    color: "bg-blue-500",
    highlight: "Tickets & dependencies",
  },
  {
    id: "execution",
    number: "03",
    title: "Agents Work Overnight",
    description:
      "Go to sleep. Agents work through tickets in isolated sandboxes—writing code, running tests, fixing issues. They don't stop until every task is complete.",
    icon: Moon,
    color: "bg-amber-500",
    highlight: "Runs until completion",
  },
  {
    id: "review",
    number: "04",
    title: "Wake Up to a PR",
    description:
      "Morning: a pull request with working, tested code. Every change traced back to your spec. Review it, merge it, ship it.",
    icon: CheckCircle2,
    color: "bg-green-500",
    highlight: "Ready when you are",
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
            You Sleep. Agents Ship.
          </h2>
          <p className="mt-4 text-lg text-landing-text-muted">
            Write a spec, approve the plan, go to bed. Wake up to a pull request.
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
                  <p className="mb-3 text-sm text-landing-text-muted">{phase.description}</p>

                  {/* Highlight Badge */}
                  <Badge
                    variant="secondary"
                    className="bg-landing-bg-muted text-xs text-landing-text-muted"
                  >
                    {phase.highlight}
                  </Badge>

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
              Watch It In Action
            </h3>
            <p className="mt-2 text-landing-text-muted">
              See a real feature go from description to done
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
