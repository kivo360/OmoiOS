"use client"

import { motion } from "framer-motion"
import {
  Mail,
  Search,
  Calendar,
  FileText,
  TrendingUp,
  Users,
  ShoppingCart,
  Headphones,
  Brain,
  Globe,
  BarChart3,
  Briefcase,
  Clock
} from "lucide-react"

const useCases = [
  {
    icon: Mail,
    name: "Inbox Zero Bot",
    description: "Triages email, drafts replies, unsubscribes from spam. Save 5+ hrs/week.",
    category: "Productivity",
    timeSaved: "5 hrs/week",
  },
  {
    icon: Search,
    name: "Lead Hunter",
    description: "Finds prospects, grabs contact info, scores leads. Wake up to warm leads.",
    category: "Sales",
    timeSaved: "8 hrs/week",
  },
  {
    icon: Calendar,
    name: "Calendar Wrangler",
    description: "Schedules meetings, sends reminders, preps agendas. No more back-and-forth.",
    category: "Productivity",
    timeSaved: "3 hrs/week",
  },
  {
    icon: FileText,
    name: "Content Machine",
    description: "Spots trends, outlines blogs, suggests viral topics. Writer's block? Gone.",
    category: "Marketing",
    timeSaved: "6 hrs/week",
  },
  {
    icon: TrendingUp,
    name: "SEO Watchdog",
    description: "Audits your site, flags issues, writes meta descriptions. Rank while you sleep.",
    category: "Marketing",
    timeSaved: "4 hrs/week",
  },
  {
    icon: Users,
    name: "Resume Screener",
    description: "Reviews applicants, ranks candidates, drafts interview questions. Hire faster.",
    category: "Operations",
    timeSaved: "10 hrs/week",
  },
  {
    icon: ShoppingCart,
    name: "Store Manager",
    description: "Updates products, alerts low stock, optimizes listings. E-commerce on autopilot.",
    category: "E-commerce",
    timeSaved: "7 hrs/week",
  },
  {
    icon: Headphones,
    name: "Support Hero",
    description: "Handles tier-1 tickets, drafts responses, escalates the hard stuff. 24/7 coverage.",
    category: "Support",
    timeSaved: "15 hrs/week",
  },
  {
    icon: Brain,
    name: "Morning Briefer",
    description: "Daily summary of calendar, emails, and tasks. Start every day focused.",
    category: "Productivity",
    timeSaved: "2 hrs/week",
  },
  {
    icon: Globe,
    name: "Competitor Spy",
    description: "Tracks rival pricing, launches, and news. Know what they're doing — first.",
    category: "Research",
    timeSaved: "4 hrs/week",
  },
  {
    icon: BarChart3,
    name: "Report Builder",
    description: "Pulls data, generates weekly reports, spots anomalies. Insights without the grunt work.",
    category: "Analytics",
    timeSaved: "6 hrs/week",
  },
  {
    icon: Briefcase,
    name: "Project Sync",
    description: "Connects Slack, Notion, Trello. Auto-updates everyone. No more status meetings.",
    category: "Operations",
    timeSaved: "5 hrs/week",
  },
]

export function OpenClawUseCasesSection() {
  return (
    <section id="use-cases" className="bg-landing-bg py-20 md:py-32">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-12 max-w-2xl text-center"
        >
          <div className="mb-4 inline-flex items-center justify-center rounded-full border border-landing-border bg-landing-bg-muted px-4 py-2">
            <Clock className="mr-2 h-5 w-5 text-landing-accent" />
            <span className="text-sm font-medium text-landing-text-muted">
              Save 10+ Hours Every Week
            </span>
          </div>

          <h2 className="mb-4 text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            12 AI Employees. Ready to Hire.
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-landing-text-muted">
            Not just one assistant — a full team of specialists.
            Each bot trained for a specific job. Pick the ones that fit your workflow.
          </p>
        </motion.div>

        <div className="mx-auto grid max-w-6xl gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {useCases.map((useCase, index) => (
            <motion.div
              key={useCase.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.05, duration: 0.4 }}
            >
              <div className="group flex h-full flex-col rounded-xl border border-landing-border bg-white p-5 shadow-sm transition-all duration-300 hover:shadow-md hover:border-landing-accent/30">
                <div className="mb-3 flex items-center justify-between">
                  <div className="inline-flex items-center justify-center rounded-lg bg-landing-bg-muted p-2.5 group-hover:bg-landing-accent/10 transition-colors">
                    <useCase.icon className="h-5 w-5 text-landing-accent" />
                  </div>
                  <span className="rounded-full bg-emerald-100 text-emerald-700 px-2.5 py-1 text-xs font-medium">
                    {useCase.timeSaved}
                  </span>
                </div>

                <h3 className="mb-2 text-lg font-bold text-landing-text">{useCase.name}</h3>
                <p className="text-sm text-landing-text-muted leading-relaxed flex-1">{useCase.description}</p>

                <div className="mt-3 pt-3 border-t border-landing-border">
                  <span className="text-xs text-landing-text-muted">
                    {useCase.category}
                  </span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.6, duration: 0.5 }}
          className="mt-12 text-center"
        >
          <p className="mb-4 text-landing-text-muted">
            Need something custom? We'll build a bot for your exact workflow.
          </p>
          <a
            href="#consulting"
            className="inline-flex items-center text-landing-accent font-semibold hover:underline"
          >
            See Custom Build Options →
          </a>
        </motion.div>
      </div>
    </section>
  )
}
