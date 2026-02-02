"use client"

import { motion } from "framer-motion"
import { Check, X } from "lucide-react"

const checklist = [
  "You spend 5+ hours/week on repetitive tasks",
  "You're tired of copy-pasting into ChatGPT",
  "You want AI that works without constant prompting",
  "You care about keeping your data private",
  "You're a solopreneur, freelancer, or small team",
]

const notForYou = [
  "You want a ChatGPT wrapper (this runs 24/7, not on-demand)",
  "You need enterprise compliance like SOC2 or HIPAA — not yet",
  "You want us to host your data (it runs on YOUR devices)",
]

export function IsThisForYouSection() {
  return (
    <section id="why" className="bg-landing-bg py-16 md:py-24">
      <div className="container mx-auto px-4">
        <div className="mx-auto max-w-4xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="grid gap-8 md:grid-cols-2"
          >
            {/* For You */}
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-8">
              <h3 className="mb-6 text-xl font-bold text-landing-text">
                OpenClaw is for you if...
              </h3>
              <ul className="space-y-4">
                {checklist.map((item, index) => (
                  <motion.li
                    key={item}
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.1 }}
                    className="flex items-start gap-3"
                  >
                    <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500">
                      <Check className="h-3 w-3 text-white" />
                    </div>
                    <span className="text-landing-text-muted">{item}</span>
                  </motion.li>
                ))}
              </ul>
              <p className="mt-6 text-sm font-medium text-emerald-700">
                Check 3+? OpenClaw will pay for itself in week one.
              </p>
            </div>

            {/* Not For You */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-8">
              <h3 className="mb-6 text-xl font-bold text-landing-text">
                OpenClaw is NOT for you if...
              </h3>
              <ul className="space-y-4">
                {notForYou.map((item, index) => (
                  <motion.li
                    key={item}
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.1 + 0.3 }}
                    className="flex items-start gap-3"
                  >
                    <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-400">
                      <X className="h-3 w-3 text-white" />
                    </div>
                    <span className="text-landing-text-muted">{item}</span>
                  </motion.li>
                ))}
              </ul>
              <p className="mt-6 text-sm text-slate-500">
                No hard feelings. We'd rather you know upfront.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
