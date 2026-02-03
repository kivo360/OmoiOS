"use client"

import { motion } from "framer-motion"
import { MessageSquare, Users, Calendar, Clock, CheckCircle, Eye } from "lucide-react"

const features = [
  {
    icon: MessageSquare,
    title: "Answers FAQs Instantly",
    subtitle: "Automatic Responses",
    description: "Documents, timelines, costs — your bot handles the questions you're tired of answering.",
  },
  {
    icon: Users,
    title: "Qualifies Leads for You",
    subtitle: "Lead Qualification",
    description: "Filters out tire-kickers before they reach you. Only serious inquiries get through.",
  },
  {
    icon: Calendar,
    title: "Books Consultations",
    subtitle: "Calendar Integration",
    description: "Syncs with your calendar and books appointments automatically. No back-and-forth.",
  },
  {
    icon: Clock,
    title: "Follows Up Automatically",
    subtitle: "Automated Follow-ups",
    description: "Cold leads get nurtured. Hot leads get reminded. You never forget to follow up again.",
  },
  {
    icon: CheckCircle,
    title: "Works 24/7",
    subtitle: "Always On",
    description: "Responds to inquiries at 3am. Handles weekend questions. Never takes a day off.",
  },
  {
    icon: Eye,
    title: "Full Visibility",
    subtitle: "Review Everything",
    description: "See every conversation. Adjust responses anytime. You're always in control.",
  },
]

export function OpenClawFeaturesSection() {
  return (
    <section id="features" className="bg-landing-bg-muted py-20 md:py-32">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-16 max-w-2xl text-center"
        >
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            What if your WhatsApp replied for you?
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-landing-text-muted">
            OpenClaw is an AI assistant that lives in your WhatsApp, Telegram, or email.
            It knows your services, your pricing, and your process — and handles the repetitive stuff automatically.
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
