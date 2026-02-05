"use client"

import { motion } from "framer-motion"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { cn } from "@/lib/utils"

const faqs = [
  {
    question: "How do you avoid low-quality output?",
    answer:
      "OmoiOS doesn’t just generate text. It executes the plan in real environments: running commands, running tests, and iterating when something fails. You get working, reviewable output—not a pile of guesswork.",
  },
  {
    question: "How is everything traceable?",
    answer:
      "Each run produces structured artifacts (requirements, design, implementation steps, and results) that link back to the original request. You can review what happened, why it happened, and what changed.",
  },
  {
    question: "How does billing work?",
    answer:
      "Start free with 1 concurrent agent. Pro is $50/month with 5 concurrent agents. Team is $200/month with 10 agents. Pro and above can bring your own API keys to bypass usage limits.",
  },
  {
    question: "What are concurrent agents?",
    answer:
      "Concurrent agents is how many work items can run in parallel. Free users get 1 agent (work runs one at a time). Pro gets 5 agents running simultaneously. Team gets 10. If you hit your limit, new work queues up and runs when a slot opens—nothing is lost.",
  },
  {
    question: "What if it doesn't work for my use case?",
    answer:
      "We offer a 30-day money-back guarantee for paid plans. If OmoiOS doesn't work for your workflow, we'll refund you—no questions asked.",
  },
  {
    question: "What is 'Bring Your Own API Keys'?",
    answer:
      "Pro and Team users can connect their own LLM API keys (OpenAI, Anthropic, etc.). You pay the LLM provider directly for tokens, which lets you run unlimited workflows without worrying about our usage caps.",
  },
  {
    question: "Is my code safe?",
    answer:
      "Yes. Your code runs in isolated sandboxes that are destroyed after each run. We never store your source code or share it with anyone. You can also self-host for complete control.",
  },
  {
    question: "Do I need to babysit the agents?",
    answer:
      "No. That's the point. You approve the plan, then agents work autonomously—often overnight—until the work is complete. You wake up to a pull request ready for review.",
  },
]

interface FAQSectionProps {
  className?: string
  id?: string
}

export function FAQSection({ className, id }: FAQSectionProps) {
  return (
    <section id={id} className={cn("bg-landing-bg py-16 md:py-24", className)}>
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-12 max-w-2xl text-center"
        >
          <h2 className="text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            Frequently Asked Questions
          </h2>
          <p className="mt-4 text-lg text-landing-text-muted">
            Everything you need to know before getting started.
          </p>
        </motion.div>

        {/* FAQ Accordion */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="mx-auto max-w-2xl"
        >
          <Accordion type="single" collapsible className="w-full">
            {faqs.map((faq, index) => (
              <AccordionItem
                key={index}
                value={`item-${index}`}
                className="border-landing-border"
              >
                <AccordionTrigger className="text-left text-landing-text hover:text-landing-accent hover:no-underline">
                  {faq.question}
                </AccordionTrigger>
                <AccordionContent className="text-landing-text-muted">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </motion.div>

        {/* Contact CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="mx-auto mt-12 max-w-2xl text-center"
        >
          <p className="text-landing-text-muted">
            Have another question?{" "}
            <a
              href="mailto:hello@omoios.dev"
              className="font-medium text-landing-accent underline-offset-4 hover:underline"
            >
              Reach out directly
            </a>
          </p>
        </motion.div>
      </div>
    </section>
  )
}
