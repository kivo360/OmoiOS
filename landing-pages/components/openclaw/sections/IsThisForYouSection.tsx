"use client"

import { motion } from "framer-motion"
import { AlertTriangle } from "lucide-react"

const painPoints = [
  'You answer "What documents do I need?" 20 times a day',
  "Leads go cold because you took too long to reply",
  "You're glued to WhatsApp from 6am to midnight",
  "Following up manually is eating your life",
  "You know you're leaving money on the table",
]

export function IsThisForYouSection() {
  return (
    <section id="why" className="bg-slate-900 py-16 md:py-24">
      <div className="container mx-auto px-4">
        <div className="mx-auto max-w-3xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-10"
          >
            <h2 className="text-3xl font-bold text-white md:text-4xl">
              Sound familiar?
            </h2>
          </motion.div>

          <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-8 md:p-10">
            <ul className="space-y-5">
              {painPoints.map((item, index) => (
                <motion.li
                  key={item}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-start gap-4"
                >
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-500/20">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                  </div>
                  <span className="text-lg text-gray-200">{item}</span>
                </motion.li>
              ))}
            </ul>
          </div>

          <motion.p
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
            className="mt-8 text-center text-lg text-gray-400"
          >
            If you checked 3+, OpenClaw will pay for itself in the first week.
          </motion.p>
        </div>
      </div>
    </section>
  )
}
