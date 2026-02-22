"use client";

import { motion } from "framer-motion";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { cn } from "@/lib/utils";

const faqs = [
  {
    question: "How is OmoiOS different from Kiro?",
    answer:
      "Kiro is a spec-driven IDE from AWS — it helps you plan and code interactively at your desk. OmoiOS is a spec-driven orchestration platform that runs autonomously in the cloud. You write the spec, approve the plan, and agents execute the full pipeline — delivering a PR while you focus on other work (or sleep). OmoiOS is also open-source and self-hostable, while Kiro is closed-source.",
  },
  {
    question: "How is OmoiOS different from OpenAI Codex?",
    answer:
      "Codex is a cloud-based coding agent from OpenAI — you assign individual tasks via prompts, and it works in a sandbox to deliver code changes or PRs. OmoiOS is a spec-driven orchestration platform — you write a feature specification, agents generate requirements, design, and implementation plans, then execute the full pipeline autonomously. OmoiOS is also open-source, self-hostable, and supports multiple model providers (Anthropic + OpenAI), while Codex is closed-source, runs only on OpenAI's infrastructure, and uses GPT models exclusively.",
  },
  {
    question: "How is OmoiOS different from Cursor or Copilot?",
    answer:
      "Cursor and Copilot are code assistants that help you write code faster inside your editor. OmoiOS is an autonomous execution platform — it doesn't help you code, it codes for you based on your spec. Different tool for a different workflow.",
  },
  {
    question: "How is OmoiOS different from Claude Code?",
    answer:
      "Claude Code is a powerful local coding agent that runs in your terminal alongside your IDE. It's excellent for interactive development — exploring codebases, debugging, and making changes with you in the loop. OmoiOS is designed for a different workflow: you define a spec, approve a plan, and agents execute the full pipeline in the cloud while you're away. Think of Claude Code as your pair programmer, and OmoiOS as your overnight engineering team.",
  },
  {
    question: "How is OmoiOS different from OpenCode?",
    answer:
      "OpenCode (sst/opencode) is a great open-source CLI tool for interactive AI-assisted coding with support for 75+ model providers. Like Claude Code, it's a local tool that requires your presence. OmoiOS takes a different approach: cloud-based autonomous execution driven by specs, not prompts. Both are open source, but OmoiOS is infrastructure you deploy, not software you install.",
  },
  {
    question: "Can I self-host OmoiOS?",
    answer:
      "Yes. OmoiOS is open-source and can be deployed on your own infrastructure. The Enterprise plan includes dedicated support for self-hosted deployments.",
  },
  {
    question: "What models does OmoiOS support?",
    answer:
      "OmoiOS works with Anthropic (Claude) and OpenAI models. On Pro and above, you can bring your own API keys to use your preferred provider.",
  },
  {
    question: "Is my code safe?",
    answer:
      "Your code runs in isolated sandboxes. On the self-hosted plan, everything stays on your infrastructure. OmoiOS never trains on your code.",
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
    question: "Do I need to babysit the agents?",
    answer:
      "No. That's the point. You approve the plan, then agents work autonomously—often overnight—until the work is complete. You wake up to a pull request ready for review.",
  },
];

interface FAQSectionProps {
  className?: string;
  id?: string;
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
  );
}
