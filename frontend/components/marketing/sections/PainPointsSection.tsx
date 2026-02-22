"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, Clock, Users, GitMerge } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type PainCard = {
  icon: LucideIcon;
  title: string;
  description: string;
};

const painCards: PainCard[] = [
  {
    icon: Users,
    title: "Your roadmap moves faster than your hiring",
    description:
      "Recruiting takes months. Your backlog grows daily. OmoiOS lets you add agent capacity tonight and wake up to shipped work tomorrow — no headcount required.",
  },
  {
    icon: AlertTriangle,
    title: "AI-generated code looks right until you run it",
    description:
      "Plausible code that breaks at build time wastes senior time. OmoiOS agents run tests, catch failures, and self-correct before you ever see the PR.",
  },
  {
    icon: Clock,
    title: "Plans drift. Context disappears. Reviews slow down.",
    description:
      "Decisions get scattered across Slack, docs, and tickets. OmoiOS traces every line of code back to the original spec — requirements, design, and implementation stay connected.",
  },
  {
    icon: GitMerge,
    title: "More contributors should mean more throughput, not more conflicts",
    description:
      "OmoiOS agents work in isolated sandboxes with dependency-aware sequencing. Parallel execution without merge chaos.",
  },
];

interface PainPointsSectionProps {
  className?: string;
  id?: string;
}

export function PainPointsSection({ className, id }: PainPointsSectionProps) {
  return (
    <section
      id={id}
      className={cn("bg-landing-bg-warm py-20 md:py-32", className)}
    >
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-12 max-w-3xl text-center"
        >
          <h2 className="text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            AI coding tools still need you at the keyboard. OmoiOS
            doesn&apos;t.
          </h2>
          <p className="mt-4 text-lg text-landing-text-muted">
            Kiro, Cursor, and Copilot help you code faster — but you&apos;re
            still the one coding. OmoiOS runs the full pipeline in the
            background so your team reviews pull requests, not prompts.
          </p>
        </motion.div>

        <div className="mx-auto max-w-3xl space-y-4">
          {painCards.map((card, i) => (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
            >
              <Card className="border-landing-border bg-white p-6">
                <div className="flex gap-4">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-red-500/10">
                    <card.icon className="h-5 w-5 text-red-600" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-landing-text">
                      {card.title}
                    </h3>
                    <p className="mt-1 text-sm text-landing-text-muted">
                      {card.description}
                    </p>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
