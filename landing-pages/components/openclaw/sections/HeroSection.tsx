"use client"

import { motion } from "framer-motion"
import { Clock, Shield, MessageSquare, Calendar, Users, AlertCircle } from "lucide-react"
import Link from "next/link"

const benefits = [
  {
    icon: MessageSquare,
    text: "Answers FAQs instantly",
  },
  {
    icon: Users,
    text: "Qualifies leads for you",
  },
  {
    icon: Calendar,
    text: "Books consultations automatically",
  },
  {
    icon: Clock,
    text: "Works 24/7 — even when you sleep",
  },
]

export function OpenClawHeroSection() {
  return (
    <section className="relative overflow-hidden bg-landing-bg py-20 md:py-32">
      {/* Urgency Banner */}
      <div className="absolute top-0 left-0 right-0 bg-gradient-to-r from-amber-500 to-orange-500 py-2 px-4 text-center">
        <p className="text-sm font-semibold text-white flex items-center justify-center gap-2">
          <AlertCircle className="h-4 w-4" />
          Early adopter pricing — Only 5 setup slots left this month
        </p>
      </div>

      <div className="container mx-auto px-4 pt-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-4xl text-center"
        >
          <div className="mb-6 inline-flex items-center justify-center rounded-full border border-landing-border bg-landing-bg-muted px-4 py-2">
            <MessageSquare className="mr-2 h-4 w-4 text-landing-accent" />
            <span className="text-sm font-medium text-landing-text-muted">
              For consultants, coaches & service businesses
            </span>
          </div>

          <h1 className="mb-6 text-4xl font-bold tracking-tight text-landing-text sm:text-5xl md:text-6xl">
            Your AI Assistant That Handles
            <br />
            <span className="landing-gradient-text">
              Clients While You Sleep
            </span>
          </h1>

          <p className="mx-auto mb-8 max-w-2xl text-lg text-landing-text-muted md:text-xl">
            Stop answering the same WhatsApp questions 50 times a day. OpenClaw responds to leads,
            schedules consultations, and follows up automatically — so you can focus on closing deals.
          </p>

          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="#consulting"
              className="landing-gradient-cta landing-card-hover inline-flex items-center rounded-lg px-8 py-4 font-semibold text-white"
            >
              Get Started — $49
            </Link>
            <Link
              href="#how-it-works"
              className="inline-flex items-center rounded-lg border border-landing-border bg-white px-8 py-4 font-semibold text-landing-text hover:bg-landing-bg-muted transition-colors"
            >
              See How It Works
            </Link>
          </div>

          {/* Social proof - real results */}
          <p className="mt-6 text-sm text-landing-text-muted">
            Setup takes 48 hours. You'll be automating client intake by this weekend.
          </p>

          {/* Guarantee Badge */}
          <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-emerald-50 border border-emerald-200 px-4 py-2">
            <Shield className="h-4 w-4 text-emerald-600" />
            <span className="text-sm font-medium text-emerald-700">
              30-day money-back guarantee — no questions asked
            </span>
          </div>
        </motion.div>

        {/* Benefits Grid */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-16 mx-auto max-w-3xl"
        >
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {benefits.map((benefit, index) => (
              <motion.div
                key={benefit.text}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.1 * index }}
                className="flex flex-col items-center gap-3 rounded-2xl border border-landing-border bg-white p-5 text-center shadow-sm"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-landing-accent/10">
                  <benefit.icon className="h-6 w-6 text-landing-accent" />
                </div>
                <span className="text-sm font-medium text-landing-text">{benefit.text}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}
