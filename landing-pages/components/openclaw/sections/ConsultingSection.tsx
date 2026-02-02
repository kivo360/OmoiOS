"use client"

import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { Check, Book, Rocket, Crown, Zap, Clock, Headphones } from "lucide-react"
import Link from "next/link"

const pricingTiers = [
  {
    name: "DIY Guide",
    price: "$39",
    period: "one-time",
    description: "Set it up yourself with our expert guidance",
    icon: Book,
    iconColor: "bg-slate-600",
    features: [
      "Step-by-step installation guide",
      "Video walkthrough included",
      "Troubleshooting documentation",
      "Community Discord access",
      "Email support for questions",
    ],
    cta: "Get the Guide",
    ctaLink: "https://buy.stripe.com/fZucN47fJf6gfYM1QZ1Jm00",
    popular: false,
  },
  {
    name: "Starter",
    price: "$449",
    period: "one-time",
    description: "We handle the setup. You start automating.",
    icon: Rocket,
    iconColor: "bg-blue-500",
    features: [
      "Full VPS or Mac deployment",
      "1 messaging channel configured",
      "10 skills pre-configured",
      "Security hardening included",
      "Basic cron job setup",
      "48-hour email support",
      "Ready in 48 hours",
    ],
    cta: "Get Started",
    ctaLink: "https://buy.stripe.com/4gMfZgfMfaQ05k81QZ1Jm01",
    popular: false,
  },
  {
    name: "Pro",
    price: "$899",
    period: "one-time",
    description: "Complete setup with custom automation.",
    icon: Crown,
    iconColor: "bg-amber-500",
    features: [
      "Everything in Starter, plus:",
      "3 messaging channels configured",
      "25 custom skills setup",
      "Custom workflow automation",
      "1-on-1 training session",
      "Migration from existing tools",
      "7-day priority support",
      "Ready in 48 hours",
    ],
    cta: "Go Pro",
    ctaLink: "https://buy.stripe.com/aFa14mbvZ3nybIw8fn1Jm02",
    popular: true,
  },
  {
    name: "Enterprise",
    price: "$1,299",
    period: "one-time",
    description: "White-glove service for businesses.",
    icon: Zap,
    iconColor: "bg-purple-500",
    features: [
      "Everything in Pro, plus:",
      "Unlimited channels configured",
      "50+ custom skills setup",
      "CRM & database integration",
      "Team training (up to 5 people)",
      "Custom skill development",
      "30-day priority support",
      "Dedicated phone line setup",
      "Ready in 72 hours",
    ],
    cta: "Contact Us",
    ctaLink: "https://buy.stripe.com/dRmfZg8jN2ju8wk3Z71Jm03",
    popular: false,
  },
]

const monthlySupport = {
  name: "Ongoing Support",
  price: "$99",
  period: "/month",
  description: "Keep your AI assistant running perfectly",
  icon: Headphones,
  ctaLink: "https://buy.stripe.com/bJe28qgQje2c13ScvD1Jm04",
  features: [
    "24/7 monitoring & alerts",
    "Proactive issue resolution",
    "Monthly performance review",
    "Skill updates & maintenance",
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
            Pick Your Setup. Start Automating Today.
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-gray-400">
            DIY or done-for-you — your call. Every package includes security hardening,
            production deployment, and a bot that actually works.
          </p>
        </motion.div>

        {/* Pricing Tiers */}
        <div className="mx-auto grid max-w-6xl gap-6 md:grid-cols-2 lg:grid-cols-4">
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

        {/* Free Consultation CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.6, duration: 0.5 }}
          className="mt-16 text-center"
        >
          <h3 className="mb-4 text-2xl font-semibold text-white">
            Not sure which one fits?
          </h3>
          <p className="mb-6 text-base text-gray-400">
            Book a free 30-min call. We'll map out your workflows and recommend the right setup. No pressure.
          </p>
          <a
            href="mailto:kevin@omoios.dev?subject=OpenClaw%20Strategy%20Call&body=Hi%20Kevin%2C%0A%0AI%27m%20interested%20in%20learning%20more%20about%20OpenClaw.%0A%0A"
            className="inline-flex items-center rounded-xl bg-white px-8 py-4 font-semibold text-slate-900 transition-all duration-300 hover:bg-gray-100 shadow-lg"
          >
            Book Free Strategy Call
          </a>
        </motion.div>
      </div>
    </section>
  )
}
