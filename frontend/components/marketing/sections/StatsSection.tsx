"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const stats = [
  {
    display: "Hours",
    label: "not weeks",
    description: "from spec to pull request",
  },
  {
    display: "24/7",
    label: "execution",
    description: "agents work while you sleep",
  },
  {
    display: "Full",
    label: "lineage",
    description: "every line traced to a requirement",
  },
  {
    display: "Zero",
    label: "babysitting",
    description: "approve the plan, review the PR",
  },
];

interface StatsSectionProps {
  className?: string;
}

export function StatsSection({ className }: StatsSectionProps) {
  return (
    <section className={cn("bg-landing-bg-warm py-16 md:py-24", className)}>
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-12 max-w-2xl text-center"
        >
          <h2 className="text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            Ship More. Manage Less.
          </h2>
          <p className="mt-4 text-lg text-landing-text-muted">
            The work you delegate to agents is work your team doesn&apos;t
            manage.
          </p>
        </motion.div>

        {/* Stats Grid */}
        <div className="mx-auto grid max-w-4xl grid-cols-2 gap-6 md:grid-cols-4">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="text-center"
            >
              <span className="text-4xl font-bold text-landing-accent md:text-5xl">
                {stat.display}
              </span>
              <div className="mt-2 font-medium text-landing-text">
                {stat.label}
              </div>
              <div className="text-sm text-landing-text-muted">
                {stat.description}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
