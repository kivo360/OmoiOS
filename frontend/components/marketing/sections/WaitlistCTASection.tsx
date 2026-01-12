"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { ArrowRight, CheckCircle2, Sparkles, Zap, Shield, Rocket } from "lucide-react"
import { SparklesCore } from "@/components/ui/sparkles"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

const benefits = [
  {
    icon: Zap,
    text: "Start building in minutes",
  },
  {
    icon: Shield,
    text: "No credit card required",
  },
  {
    icon: Rocket,
    text: "Free tier included",
  },
]

interface WaitlistCTASectionProps {
  className?: string
}

export function WaitlistCTASection({ className }: WaitlistCTASectionProps) {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return

    setIsSubmitting(true)
    // Small delay for visual feedback before redirect
    setTimeout(() => {
      router.push(`/register?email=${encodeURIComponent(email)}`)
    }, 300)
  }

  return (
    <section
      className={cn(
        "relative overflow-hidden bg-landing-bg-dark py-24 md:py-32",
        className
      )}
    >
      {/* Sparkles Background */}
      <div className="absolute inset-0">
        <SparklesCore
          id="waitlist-sparkles"
          background="transparent"
          minSize={0.4}
          maxSize={1}
          particleDensity={50}
          className="h-full w-full"
          particleColor="#FF6B35"
        />
      </div>

      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-landing-bg-dark/50 to-landing-bg-dark" />

      <div className="container relative mx-auto px-4">
        <div className="mx-auto max-w-2xl text-center">
          {/* Eyebrow */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mb-6"
          >
            <span className="inline-flex items-center gap-2 rounded-full bg-landing-accent/20 px-4 py-1.5 text-sm font-medium uppercase tracking-wider text-landing-accent">
              <Sparkles className="h-4 w-4" />
              Now Open
            </span>
          </motion.div>

          {/* Headline */}
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-3xl font-bold tracking-tight text-white md:text-4xl lg:text-5xl"
          >
            Ready to Ship Faster?
          </motion.h2>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="mt-4 text-lg text-gray-400"
          >
            Create your free account and start building with AI agents today. No credit card required.
          </motion.p>

          {/* Benefits */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.25 }}
            className="mx-auto mt-8 flex max-w-lg flex-col gap-3 sm:flex-row sm:justify-center"
          >
            {benefits.map((benefit, index) => (
              <div
                key={index}
                className="flex items-center gap-2 rounded-lg bg-white/5 px-4 py-2 text-sm text-gray-300"
              >
                <benefit.icon className="h-4 w-4 text-landing-accent" />
                <span>{benefit.text}</span>
              </div>
            ))}
          </motion.div>

          {/* Form */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
            className="mt-10"
          >
            <form onSubmit={handleSubmit} className="mx-auto flex max-w-md gap-3">
              <Input
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-12 flex-1 border-gray-700 bg-gray-900 text-white placeholder:text-gray-500"
                required
                disabled={isSubmitting}
              />
              <Button
                type="submit"
                size="lg"
                disabled={isSubmitting}
                className="h-12 bg-landing-accent px-6 text-white hover:bg-landing-accent-dark"
              >
                {isSubmitting ? (
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <>
                    Get Started Free
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            {/* Trust note */}
            <p className="mt-4 text-sm text-gray-400">
              Join <span className="font-semibold text-landing-accent">500+</span> engineers already building with OmoiOS
            </p>
          </motion.div>

          {/* Trust Elements */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.4 }}
            className="mt-8 flex flex-wrap items-center justify-center gap-4 text-xs text-gray-500"
          >
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-green-500" />
              Free tier forever
            </span>
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-green-500" />
              No credit card required
            </span>
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-green-500" />
              Cancel anytime
            </span>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
