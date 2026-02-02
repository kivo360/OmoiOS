"use client"

import { motion } from "framer-motion"
import { ArrowRight, Frown, Smile } from "lucide-react"

const comparisons = [
  {
    before: "Check email manually every morning",
    after: "Wake up to a prioritized inbox summary",
  },
  {
    before: "Copy-paste prompts into ChatGPT all day",
    after: "Bot handles tasks on autopilot, 24/7",
  },
  {
    before: "Forget to follow up — deals go cold",
    after: "Auto-reminders before opportunities slip",
  },
  {
    before: "Spend hours compiling weekly reports",
    after: "Reports generated and sent automatically",
  },
  {
    before: "Context-switch between 10 different apps",
    after: "One bot syncs Slack, Notion, email & more",
  },
]

export function BeforeAfterSection() {
  return (
    <section className="bg-landing-bg-muted py-20 md:py-28">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-12 max-w-2xl text-center"
        >
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            Your Week, Transformed
          </h2>
          <p className="text-lg text-landing-text-muted">
            See what changes when your AI actually works for you.
          </p>
        </motion.div>

        <div className="mx-auto max-w-4xl">
          {/* Header */}
          <div className="mb-6 grid grid-cols-[1fr,auto,1fr] items-center gap-4 px-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-wide">
              <Frown className="h-4 w-4" />
              Before
            </div>
            <div className="w-8" />
            <div className="flex items-center gap-2 text-sm font-semibold text-emerald-600 uppercase tracking-wide">
              <Smile className="h-4 w-4" />
              After
            </div>
          </div>

          {/* Comparison rows */}
          <div className="space-y-4">
            {comparisons.map((item, index) => (
              <motion.div
                key={item.before}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="grid grid-cols-[1fr,auto,1fr] items-center gap-4"
              >
                {/* Before */}
                <div className="rounded-xl bg-white border border-slate-200 p-4 text-landing-text-muted">
                  {item.before}
                </div>

                {/* Arrow */}
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-landing-accent text-white shadow-lg">
                  <ArrowRight className="h-5 w-5" />
                </div>

                {/* After */}
                <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-emerald-800 font-medium">
                  {item.after}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
