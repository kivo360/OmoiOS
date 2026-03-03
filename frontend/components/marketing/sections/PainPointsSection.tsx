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
    title: "Your backlog grows faster than your team",
    description:
      "Add agent capacity tonight. Wake up to shipped work tomorrow. No headcount, no onboarding, no ramp-up time.",
  },
  {
    icon: AlertTriangle,
    title: "AI code that looks right until you run it",
    description:
      "Agents run tests, catch failures, and self-correct before you ever see the PR. You review working code, not plausible code.",
  },
  {
    icon: Clock,
    title: "Context scattered across Slack, docs, and tickets",
    description:
      "Every line of code traces back to the original spec. Requirements, design, and implementation stay connected end-to-end.",
  },
  {
    icon: GitMerge,
    title: "More agents, not more merge conflicts",
    description:
      "Isolated sandboxes. Dependency-aware sequencing. Scale throughput by adding agents, not meetings.",
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
            AI coding tools still need you at the keyboard.
          </h2>
          <p className="mt-4 text-lg text-landing-text-muted">
            Kiro, Cursor, and Copilot help you code faster — but you&apos;re
            still the one coding. OmoiOS runs the full pipeline overnight so
            your team reviews pull requests, not prompts.
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
