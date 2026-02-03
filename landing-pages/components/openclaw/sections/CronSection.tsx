"use client"

import { motion } from "framer-motion"
import { Settings, Link2, Zap } from "lucide-react"

const steps = [
  {
    number: "1",
    icon: Settings,
    title: "We Set It Up",
    description: "Tell us about your services, pricing, and process. We configure everything for you.",
    color: "bg-blue-500",
  },
  {
    number: "2",
    icon: Link2,
    title: "Connect Your Channels",
    description: "WhatsApp, Telegram, email, or all three. Your bot goes where your clients are.",
    color: "bg-amber-500",
  },
  {
    number: "3",
    icon: Zap,
    title: "Start Automating",
    description: "Your AI handles inquiries while you focus on clients. Ready in 48 hours.",
    color: "bg-emerald-500",
  },
]

export function OpenClawCronSection() {
  return (
    <section id="how-it-works" className="bg-landing-bg py-20 md:py-32">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-16 max-w-2xl text-center"
        >
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            How It Works
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-landing-text-muted">
            Ready in 48 hours. No tech skills needed.
          </p>
        </motion.div>

        <div className="mx-auto max-w-4xl">
          <div className="grid gap-8 md:grid-cols-3">
            {steps.map((step, index) => (
              <motion.div
                key={step.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.15, duration: 0.5 }}
                className="relative"
              >
                {/* Connector line (hidden on mobile, shown on desktop) */}
                {index < steps.length - 1 && (
                  <div className="hidden md:block absolute top-12 left-[60%] w-[80%] h-0.5 bg-gradient-to-r from-landing-accent/50 to-landing-accent/10" />
                )}

                <div className="flex flex-col items-center text-center">
                  {/* Step number with icon */}
                  <div className={`mb-6 relative flex h-24 w-24 items-center justify-center rounded-2xl ${step.color} shadow-lg`}>
                    <step.icon className="h-10 w-10 text-white" />
                    <div className="absolute -top-2 -right-2 flex h-8 w-8 items-center justify-center rounded-full bg-white text-sm font-bold text-slate-900 shadow-md">
                      {step.number}
                    </div>
                  </div>

                  <h3 className="mb-3 text-xl font-bold text-landing-text">{step.title}</h3>
                  <p className="text-base text-landing-text-muted leading-relaxed">{step.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
