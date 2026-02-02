"use client"

import { motion } from "framer-motion"
import { Bot, Clock, MessageSquare, Shield, Zap, Activity } from "lucide-react"

const features = [
  {
    icon: Bot,
    title: "Run a Whole Team",
    subtitle: "Multi-Agent System",
    description: "Deploy multiple bots at once — each with its own job, tools, and personality. Zero extra cost.",
  },
  {
    icon: MessageSquare,
    title: "One Bot, Every Chat",
    subtitle: "Omnichannel Support",
    description: "WhatsApp, Slack, Discord, Telegram, iMessage — all synced. Reply from anywhere.",
  },
  {
    icon: Clock,
    title: "Acts Before You Ask",
    subtitle: "Proactive Automation",
    description: "Morning briefs at 7am. Status updates at noon. Weekly reports on Monday. All automatic.",
  },
  {
    icon: Activity,
    title: "Never Goes Down",
    subtitle: "Always-On Reliability",
    description: "Built-in health checks with auto-recovery. Your bot fixes itself — no babysitting required.",
  },
  {
    icon: Shield,
    title: "Privacy by Default",
    subtitle: "Your Data, Your Control",
    description: "Runs on YOUR devices. No cloud middleman. No subscription fees. Open-source forever.",
  },
  {
    icon: Zap,
    title: "Does What You Need",
    subtitle: "500+ Skills Ready",
    description: "Gmail, Calendar, Notion, Shopify, Stripe — and hundreds more. Or build your own.",
  },
]

export function OpenClawFeaturesSection() {
  return (
    <section className="bg-landing-bg-muted py-20 md:py-32">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-16 max-w-2xl text-center"
        >
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            Built for People Who Hate Repetitive Work
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-landing-text-muted">
            Enterprise-grade automation that respects your privacy.
            Full control. No vendor lock-in. Actually useful.
          </p>
        </motion.div>

        <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1, duration: 0.5 }}
            >
              <div className="group flex h-full flex-col rounded-2xl border border-landing-border bg-white p-8 shadow-sm transition-all duration-300 hover:shadow-lg hover:border-landing-accent/30">
                <div className="mb-4 inline-flex items-center justify-center rounded-xl bg-landing-accent/10 p-4 w-fit group-hover:bg-landing-accent/20 transition-colors">
                  <feature.icon className="h-7 w-7 text-landing-accent" />
                </div>
                <p className="text-xs font-medium text-landing-accent uppercase tracking-wide mb-1">
                  {feature.subtitle}
                </p>
                <h3 className="mb-3 text-xl font-bold text-landing-text">{feature.title}</h3>
                <p className="text-base text-landing-text-muted leading-relaxed">{feature.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
