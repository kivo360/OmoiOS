"use client"

import { motion } from "framer-motion"
import { Bot, Clock, Shield, Zap, MessageSquare, Sparkles } from "lucide-react"
import Link from "next/link"
import { NumberTicker } from "@/components/ui/number-ticker"

const stats = [
  {
    value: 8,
    suffix: "+",
    label: "Message Anywhere",
    description: "One bot, every platform you use",
    icon: MessageSquare,
  },
  {
    value: 24,
    suffix: "/7",
    label: "Never Miss a Beat",
    description: "Works while you sleep",
    icon: Clock,
  },
  {
    value: 100,
    suffix: "%",
    label: "Your Data Stays Yours",
    description: "Runs on your devices, not ours",
    icon: Shield,
  },
  {
    value: 0,
    suffix: "",
    label: "Set It & Forget It",
    description: "We handle all deployment",
    icon: Zap,
  },
]

export function OpenClawHeroSection() {
  return (
    <section className="relative overflow-hidden bg-landing-bg py-20 md:py-32">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-4xl text-center"
        >
          <div className="mb-6 inline-flex items-center justify-center rounded-full border border-landing-border bg-landing-bg-muted px-4 py-2">
            <Sparkles className="mr-2 h-4 w-4 text-landing-accent" />
            <span className="text-sm font-medium text-landing-text-muted">
              For solopreneurs, agencies & small teams
            </span>
          </div>

          <h1 className="mb-6 text-4xl font-bold tracking-tight text-landing-text sm:text-5xl md:text-6xl">
            Stop Babysitting ChatGPT.
            <br />
            <span className="landing-gradient-text">
              Start Delegating.
            </span>
          </h1>

          <p className="mx-auto mb-8 max-w-2xl text-lg text-landing-text-muted md:text-xl">
            Tired of copy-pasting prompts every day? OpenClaw runs autonomously on <strong>your</strong> devices —
            checking emails, scheduling tasks, and sending updates while you sleep.
            No subscriptions. No data harvesting. Just results.
          </p>

          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="#consulting"
              className="landing-gradient-cta landing-card-hover inline-flex items-center rounded-lg px-8 py-4 font-semibold text-white"
            >
              Deploy My AI
            </Link>
            <Link
              href="#use-cases"
              className="inline-flex items-center rounded-lg border border-landing-border bg-white px-8 py-4 font-semibold text-landing-text hover:bg-landing-bg-muted transition-colors"
            >
              See What It Can Do
            </Link>
          </div>

          {/* Social proof hint */}
          <p className="mt-6 text-sm text-landing-text-muted">
            Join 50+ early adopters already automating their busywork
          </p>
        </motion.div>

        {/* Stats Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-20 mx-auto max-w-5xl"
        >
          <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
            {stats.map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.1 * index }}
                className="group relative overflow-hidden rounded-2xl border border-landing-border bg-white p-6 shadow-sm transition-all duration-300 hover:shadow-lg hover:border-landing-accent/30"
              >
                {/* Gradient overlay on hover */}
                <div className="absolute inset-0 bg-gradient-to-br from-landing-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                <div className="relative">
                  <div className="mb-4 inline-flex items-center justify-center rounded-xl bg-landing-bg-muted p-3 group-hover:bg-landing-accent/10 transition-colors">
                    <stat.icon className="h-6 w-6 text-landing-accent" />
                  </div>

                  <div className="flex items-baseline gap-0.5">
                    <NumberTicker
                      value={stat.value}
                      delay={0.2 + index * 0.1}
                      className="text-4xl font-bold text-landing-text"
                    />
                    <span className="text-3xl font-bold text-landing-accent">
                      {stat.suffix}
                    </span>
                  </div>

                  <h3 className="mt-2 text-sm font-semibold text-landing-text">
                    {stat.label}
                  </h3>
                  <p className="mt-1 text-xs text-landing-text-muted">
                    {stat.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}
