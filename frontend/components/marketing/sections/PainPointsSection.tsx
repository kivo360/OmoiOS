"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  Clock,
  Users,
  GitMerge,
  CheckCircle2,
  ListChecks,
  Eye,
  TrendingUp,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Point = {
  icon: LucideIcon;
  title: string;
  description: string;
};

const painPoints: Point[] = [
  {
    icon: Users,
    title: "Hiring can't keep up with the roadmap",
    description:
      "Recruiting is slow. Roadmaps aren't. Your best engineers end up doing coordination work instead of shipping.",
  },
  {
    icon: AlertTriangle,
    title: "AI output looks right… until you run it",
    description:
      "Plausible code that fails at build time is a tax on senior time—and a demo killer.",
  },
  {
    icon: Clock,
    title: "Plans drift and context disappears",
    description:
      "Docs rot, decisions get scattered, and reviews slow down because nobody knows the full story.",
  },
  {
    icon: GitMerge,
    title: "Parallel work increases breakage",
    description:
      "More contributors should mean more throughput—not more merge conflicts and regressions.",
  },
];

const outcomes: Point[] = [
  {
    icon: ListChecks,
    title: "A clear plan and schedule before execution",
    description:
      "See what will be built, in what order, and why—before any work starts.",
  },
  {
    icon: Eye,
    title: "An execution log you can audit",
    description:
      "Watch progress and review what happened without chasing updates or babysitting.",
  },
  {
    icon: CheckCircle2,
    title: "Traceable outputs you can review",
    description:
      "Requirements, design, implementation steps, and results—connected and easy to reference.",
  },
  {
    icon: TrendingUp,
    title: "Scale output without scaling headcount",
    description:
      "Add capacity by adding agents and guardrails—not meetings and coordination overhead.",
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
          className="mx-auto mb-12 max-w-2xl text-center"
        >
          <Badge className="mb-4 bg-landing-accent/10 text-landing-accent hover:bg-landing-accent/10">
            For CTOs & Founders
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            Your bottleneck isn&apos;t ideas. It&apos;s execution.
          </h2>
          <p className="mt-4 text-lg text-landing-text-muted">
            OmoiOS helps you scale output without scaling chaos—by making
            planning and execution visible, structured, and reviewable.
          </p>
        </motion.div>

        <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-2">
          {/* Pain */}
          <div>
            <div className="mb-4 flex items-center gap-2">
              <span className="text-sm font-semibold uppercase tracking-wider text-landing-text-subtle">
                The pain
              </span>
            </div>

            <div className="space-y-4">
              {painPoints.map((point, i) => (
                <motion.div
                  key={point.title}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05 }}
                >
                  <Card className="border-landing-border bg-white p-6">
                    <div className="flex gap-4">
                      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-red-500/10">
                        <point.icon className="h-5 w-5 text-red-600" />
                      </div>
                      <div>
                        <h3 className="text-base font-semibold text-landing-text">
                          {point.title}
                        </h3>
                        <p className="mt-1 text-sm text-landing-text-muted">
                          {point.description}
                        </p>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Outcome */}
          <div>
            <div className="mb-4 flex items-center gap-2">
              <span className="text-sm font-semibold uppercase tracking-wider text-landing-text-subtle">
                On the other side
              </span>
            </div>

            <div className="space-y-4">
              {outcomes.map((point, i) => (
                <motion.div
                  key={point.title}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05 }}
                >
                  <Card className="border-landing-border bg-white p-6">
                    <div className="flex gap-4">
                      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-green-500/10">
                        <point.icon className="h-5 w-5 text-green-600" />
                      </div>
                      <div>
                        <h3 className="text-base font-semibold text-landing-text">
                          {point.title}
                        </h3>
                        <p className="mt-1 text-sm text-landing-text-muted">
                          {point.description}
                        </p>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
