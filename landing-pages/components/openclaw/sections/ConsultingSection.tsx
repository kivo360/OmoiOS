"use client"

import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { Check, Rocket, Crown, Clock, Headphones, Shield, AlertCircle } from "lucide-react"
import Link from "next/link"

const pricingTiers = [
  {
    name: "Starter",
    price: "$49",
    period: "one-time",
    description: "Full setup on your device. Start automating today.",
    icon: Rocket,
    iconColor: "bg-blue-500",
    features: [
      "Full setup on your device",
      "1 channel (WhatsApp OR Telegram)",
      "FAQ automation",
      "Lead qualification",
      "Basic follow-ups",
      "Email support",
      "Ready in 48 hours",
    ],
    cta: "Get Started — $49",
    ctaLink: "https://buy.stripe.com/eVq5kCfMf8HS7sg67f1Jm05",
    popular: false,
  },
  {
    name: "Pro",
    price: "$99",
    period: "one-time",
    description: "Everything in Starter, plus multi-channel & training.",
    icon: Crown,
    iconColor: "bg-amber-500",
    features: [
      "Everything in Starter, plus:",
      "3 channels connected",
      "Calendar booking integration",
      "Custom workflow automation",
      "1-on-1 training call",
      "Priority support",
      "Ready in 48 hours",
    ],
    cta: "Go Pro — $99",
    ctaLink: "https://buy.stripe.com/fZu4gy57Be2ceUI3Z71Jm06",
    popular: true,
  },
]

const monthlySupport = {
  name: "Maintenance",
  price: "$29",
  period: "/month",
  description: "Keep your AI assistant running perfectly. Cancel anytime.",
  icon: Headphones,
  ctaLink: "https://buy.stripe.com/4gM14marV5vG3c0brz1Jm07",
  features: [
    "24/7 monitoring",
    "Auto-recovery if something breaks",
    "Monthly optimization",
    "Priority support queue",
    "Cancel anytime",
  ],
}

export function OpenClawConsultingSection() {
  return (
    <section id="consulting" className="bg-slate-900 py-20 md:py-32">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-12 max-w-2xl text-center"
        >
          <div className="mb-4 inline-flex items-center justify-center rounded-full bg-white/10 px-4 py-2">
            <Clock className="mr-2 h-5 w-5 text-landing-accent" />
            <span className="text-sm font-medium text-gray-300">
              Ready in 48 Hours or Less
            </span>
          </div>

          <h2 className="mb-4 text-3xl font-bold tracking-tight text-white md:text-4xl">
            Simple Pricing. No Surprises.
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-gray-400">
            One-time setup fee. No monthly subscriptions required.
            Add optional maintenance if you want hands-off peace of mind.
          </p>

          {/* Urgency + Guarantee */}
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-4">
            <div className="inline-flex items-center gap-2 rounded-full bg-amber-500/20 border border-amber-500/30 px-4 py-2">
              <AlertCircle className="h-4 w-4 text-amber-400" />
              <span className="text-sm font-medium text-amber-300">
                Only 5 setup slots left this month
              </span>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full bg-emerald-500/20 border border-emerald-500/30 px-4 py-2">
              <Shield className="h-4 w-4 text-emerald-400" />
              <span className="text-sm font-medium text-emerald-300">
                30-day money-back guarantee
              </span>
            </div>
          </div>
        </motion.div>

        {/* Pricing Tiers */}
        <div className="mx-auto grid max-w-3xl gap-6 md:grid-cols-2">
          {pricingTiers.map((tier, index) => (
            <motion.div
              key={tier.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1, duration: 0.5 }}
              className="relative"
            >
              {tier.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
                  <span className="rounded-full bg-landing-accent px-4 py-1 text-xs font-bold text-white shadow-lg">
                    Most Popular
                  </span>
                </div>
              )}
              <div className={cn(
                "flex h-full flex-col rounded-2xl p-6 transition-all duration-300 hover:translate-y-[-4px]",
                tier.popular
                  ? "border-2 border-landing-accent bg-white shadow-xl shadow-landing-accent/20"
                  : "border border-slate-700 bg-slate-800/50 hover:border-slate-600"
              )}>
                {/* Icon - Centered at top */}
                <div className="mb-6 flex justify-center">
                  <div className={cn(
                    "inline-flex items-center justify-center rounded-2xl p-4 shadow-lg",
                    tier.iconColor
                  )}>
                    <tier.icon className="h-7 w-7 text-white" />
                  </div>
                </div>

                {/* Title & Description - Centered */}
                <div className="text-center mb-4">
                  <h3 className={cn(
                    "mb-2 text-xl font-bold",
                    tier.popular ? "text-slate-900" : "text-white"
                  )}>
                    {tier.name}
                  </h3>
                  <p className={cn(
                    "text-sm",
                    tier.popular ? "text-slate-600" : "text-gray-400"
                  )}>
                    {tier.description}
                  </p>
                </div>

                {/* Price - Centered */}
                <div className="mb-6 text-center">
                  <span className={cn(
                    "text-4xl font-bold",
                    tier.popular ? "text-slate-900" : "text-white"
                  )}>
                    {tier.price}
                  </span>
                  <span className={cn(
                    "ml-1 text-sm",
                    tier.popular ? "text-slate-500" : "text-gray-500"
                  )}>
                    {tier.period}
                  </span>
                </div>

                {/* Features */}
                <ul className="mb-6 flex-1 space-y-3">
                  {tier.features.map((feature, i) => (
                    <li key={i} className={cn(
                      "flex items-start text-sm",
                      tier.popular ? "text-slate-700" : "text-gray-300"
                    )}>
                      <Check className={cn(
                        "mr-2 h-4 w-4 flex-shrink-0 mt-0.5",
                        tier.popular ? "text-landing-accent" : "text-emerald-400"
                      )} />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA Button */}
                <Link
                  href={tier.ctaLink}
                  target={tier.ctaLink.startsWith("http") ? "_blank" : undefined}
                  rel={tier.ctaLink.startsWith("http") ? "noopener noreferrer" : undefined}
                  className={cn(
                    "w-full rounded-xl py-3.5 font-semibold transition-all duration-300 text-center block",
                    tier.popular
                      ? "bg-landing-accent text-white hover:bg-landing-accent/90 shadow-lg shadow-landing-accent/30"
                      : "bg-white/10 text-white hover:bg-white/20 border border-slate-600"
                  )}
                >
                  {tier.cta}
                </Link>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Monthly Support Add-on */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.5, duration: 0.5 }}
          className="mx-auto mt-12 max-w-4xl"
        >
          <div className="rounded-2xl border border-landing-accent/30 bg-gradient-to-r from-landing-accent/10 to-landing-accent/5 p-8">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
              <div className="flex items-start gap-4">
                <div className="rounded-xl bg-landing-accent p-3 shadow-lg">
                  <Headphones className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white mb-1">
                    {monthlySupport.name}
                    <span className="ml-3 text-2xl font-bold text-landing-accent">
                      {monthlySupport.price}
                      <span className="text-base text-gray-400">{monthlySupport.period}</span>
                    </span>
                  </h3>
                  <p className="text-gray-300 mb-3">{monthlySupport.description}</p>
                  <div className="flex flex-wrap gap-x-6 gap-y-2">
                    {monthlySupport.features.map((feature, i) => (
                      <span key={i} className="flex items-center text-sm text-gray-300">
                        <Check className="mr-1.5 h-4 w-4 text-emerald-400" />
                        {feature}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <Link
                href={monthlySupport.ctaLink}
                target="_blank"
                rel="noopener noreferrer"
                className="whitespace-nowrap rounded-xl bg-landing-accent px-6 py-3.5 font-semibold text-white hover:bg-landing-accent/90 transition-colors shadow-lg text-center"
              >
                Add Support
              </Link>
            </div>
          </div>
        </motion.div>

        {/* What happens next */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.6, duration: 0.5 }}
          className="mt-16"
        >
          <div className="mx-auto max-w-2xl rounded-2xl border border-slate-700 bg-slate-800/50 p-8 text-center">
            <h3 className="mb-4 text-xl font-semibold text-white">
              What happens after you buy?
            </h3>
            <ol className="text-left text-gray-300 space-y-3 mb-6">
              <li className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-landing-accent text-sm font-bold text-white">1</span>
                <span>You'll get an email within 2 hours to schedule a quick onboarding call</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-landing-accent text-sm font-bold text-white">2</span>
                <span>We'll ask about your services, FAQs, and how you want the bot to respond</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-landing-accent text-sm font-bold text-white">3</span>
                <span>Within 48 hours, your AI assistant is live and handling inquiries</span>
              </li>
            </ol>
            <p className="text-sm text-gray-400 mb-6">
              Don't love it? Full refund within 30 days. No questions asked.
            </p>
            <Link
              href={pricingTiers[0].ctaLink}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center rounded-xl landing-gradient-cta px-8 py-4 font-semibold text-white transition-all duration-300 hover:opacity-90 shadow-lg"
            >
              Get Started — $49
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
