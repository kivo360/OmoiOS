"use client"

import { motion } from "framer-motion"
import { useState } from "react"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

const painPoints = [
  "You answer the same questions over and over again",
  "Leads go cold because you took too long to reply",
  "You're glued to your phone from 6am to midnight",
  "Following up manually is eating your life",
  "You know you're leaving money on the table",
]

function CheckboxItem({ item, index }: { item: string; index: number }) {
  const [checked, setChecked] = useState(false)

  return (
    <motion.li
      initial={{ opacity: 0, x: -10 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.1 }}
      className="flex items-start gap-4"
    >
      <button
        onClick={() => setChecked(!checked)}
        className={cn(
          "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border-2 transition-all duration-200",
          checked
            ? "bg-amber-500 border-amber-500"
            : "bg-transparent border-amber-500/50 hover:border-amber-500"
        )}
      >
        {checked && <Check className="h-4 w-4 text-white" />}
      </button>
      <span className={cn(
        "text-lg transition-colors duration-200",
        checked ? "text-white" : "text-gray-300"
      )}>
        {item}
      </span>
    </motion.li>
  )
}

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
            <p className="mt-3 text-gray-400">Click all that apply</p>
          </motion.div>

          <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-8 md:p-10">
            <ul className="space-y-5">
              {painPoints.map((item, index) => (
                <CheckboxItem key={item} item={item} index={index} />
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
            Check 3+? OpenClaw will pay for itself in the first week.
          </motion.p>
        </div>
      </div>
    </section>
  )
}
