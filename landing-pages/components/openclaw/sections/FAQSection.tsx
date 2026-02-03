"use client"

import { motion } from "framer-motion"
import { useState } from "react"
import { ChevronDown, HelpCircle } from "lucide-react"
import { cn } from "@/lib/utils"

const faqs = [
  {
    question: "Do I need to be technical?",
    answer: "Nope. We handle everything. You just tell us how you want it to work — your services, your pricing, your FAQs. We configure the rest.",
  },
  {
    question: "Will it sound robotic?",
    answer: "No — it's powered by Claude, the most natural-sounding AI available. Clients won't know it's not you (unless you want them to). You can customize the tone to match your style.",
  },
  {
    question: "What if a client asks something complex?",
    answer: "It escalates to you immediately. You handle the nuanced stuff, it handles the repetitive questions you're tired of answering.",
  },
  {
    question: "Can I see what it's saying?",
    answer: "Yes — full visibility into every conversation. You can review responses, adjust how it answers, and make changes anytime.",
  },
  {
    question: "What if something breaks?",
    answer: "With the $29/month maintenance plan, we monitor 24/7 and fix issues automatically before you notice. Without it, just email us and we'll help you troubleshoot.",
  },
  {
    question: "What's your refund policy?",
    answer: "30-day money-back guarantee, no questions asked. If you're not happy with the results, we'll refund you in full.",
  },
]

function FAQItem({ question, answer, index }: { question: string; answer: string; index: number }) {
  const [isOpen, setIsOpen] = useState(index === 0) // First one open by default

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex w-full items-center justify-between rounded-xl px-6 py-5 text-left transition-all duration-200",
          isOpen
            ? "bg-landing-accent/5 border border-landing-accent/20"
            : "hover:bg-slate-50 border border-transparent"
        )}
      >
        <span className={cn(
          "text-lg font-medium pr-4 transition-colors",
          isOpen ? "text-landing-accent" : "text-landing-text"
        )}>
          {question}
        </span>
        <div className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-all duration-200",
          isOpen ? "bg-landing-accent text-white rotate-180" : "bg-slate-100 text-slate-500"
        )}>
          <ChevronDown className="h-4 w-4" />
        </div>
      </button>
      <div
        className={cn(
          "overflow-hidden transition-all duration-300 ease-out",
          isOpen ? "max-h-48 opacity-100" : "max-h-0 opacity-0"
        )}
      >
        <p className="px-6 pb-4 pt-2 text-base text-landing-text-muted leading-relaxed">
          {answer}
        </p>
      </div>
    </motion.div>
  )
}

export function FAQSection() {
  return (
    <section className="bg-slate-50 py-20 md:py-28">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-12 max-w-2xl text-center"
        >
          <div className="mb-4 inline-flex items-center justify-center rounded-full border border-landing-border bg-white px-4 py-2">
            <HelpCircle className="mr-2 h-4 w-4 text-landing-accent" />
            <span className="text-sm font-medium text-landing-text-muted">
              Got questions?
            </span>
          </div>
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            Frequently Asked Questions
          </h2>
          <p className="text-lg text-landing-text-muted">
            Everything you need to know before getting started.
          </p>
        </motion.div>

        <div className="mx-auto max-w-2xl space-y-3">
          {faqs.map((faq, index) => (
            <FAQItem key={faq.question} {...faq} index={index} />
          ))}
        </div>

        {/* Still have questions? */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mt-10 max-w-md text-center"
        >
          <p className="text-landing-text-muted">
            Still have questions?{" "}
            <a
              href="mailto:kevin@omoios.dev?subject=Question%20about%20OpenClaw"
              className="font-medium text-landing-accent hover:underline"
            >
              Email us directly
            </a>
            {" "}— we respond within 24 hours.
          </p>
        </motion.div>
      </div>
    </section>
  )
}
