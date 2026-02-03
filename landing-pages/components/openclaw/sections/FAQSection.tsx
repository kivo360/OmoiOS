"use client"

import { motion } from "framer-motion"
import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

const faqs = [
  {
    question: "Do I need to be technical?",
    answer: "Nope. We handle everything. You just tell us how you want it to work.",
  },
  {
    question: "Will it sound robotic?",
    answer: "No — it's powered by Claude, the most natural-sounding AI. Clients won't know it's not you (unless you want them to).",
  },
  {
    question: "What if a client asks something complex?",
    answer: "It escalates to you. You handle the hard stuff, it handles the repetitive stuff.",
  },
  {
    question: "Can I see what it's saying?",
    answer: "Yes — full visibility. You can review every conversation and adjust responses anytime.",
  },
  {
    question: "What happens if something breaks?",
    answer: "With the $29/month maintenance plan, we monitor 24/7 and fix issues automatically. Without it, you can email us and we'll help you troubleshoot.",
  },
  {
    question: "Can I cancel anytime?",
    answer: "The setup fee is one-time. If you add the monthly maintenance, you can cancel anytime — no contracts, no penalties.",
  },
]

function FAQItem({ question, answer, index }: { question: string; answer: string; index: number }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.1, duration: 0.4 }}
      className="border-b border-landing-border last:border-b-0"
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between py-5 text-left"
      >
        <span className="text-lg font-medium text-landing-text pr-4">{question}</span>
        <ChevronDown
          className={cn(
            "h-5 w-5 flex-shrink-0 text-landing-text-muted transition-transform duration-200",
            isOpen && "rotate-180"
          )}
        />
      </button>
      <div
        className={cn(
          "overflow-hidden transition-all duration-300",
          isOpen ? "max-h-48 pb-5" : "max-h-0"
        )}
      >
        <p className="text-base text-landing-text-muted leading-relaxed">{answer}</p>
      </div>
    </motion.div>
  )
}

export function FAQSection() {
  return (
    <section className="bg-landing-bg py-20 md:py-32">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-12 max-w-2xl text-center"
        >
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            Frequently Asked Questions
          </h2>
        </motion.div>

        <div className="mx-auto max-w-2xl rounded-2xl border border-landing-border bg-white p-6 md:p-8 shadow-sm">
          {faqs.map((faq, index) => (
            <FAQItem key={faq.question} {...faq} index={index} />
          ))}
        </div>
      </div>
    </section>
  )
}
