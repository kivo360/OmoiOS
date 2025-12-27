"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { ArrowRight, CheckCircle2, Sparkles } from "lucide-react"
import { SparklesCore } from "@/components/ui/sparkles"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

interface WaitlistCTASectionProps {
  className?: string
}

export function WaitlistCTASection({ className }: WaitlistCTASectionProps) {
  const [email, setEmail] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return

    setIsSubmitting(true)
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setIsSubmitting(false)
    setIsSubmitted(true)
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
              Limited Early Access
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
            Be First to Ship with AI
          </motion.h2>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="mt-4 text-lg text-gray-400"
          >
            Join the waitlist for early access. We&apos;re onboarding teams weekly.
          </motion.p>

          {/* Form */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
            className="mt-10"
          >
            {!isSubmitted ? (
              <>
                <form onSubmit={handleSubmit} className="mx-auto flex max-w-md gap-3">
                  <Input
                    type="email"
                    placeholder="Enter your work email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="h-12 flex-1 border-gray-700 bg-gray-900 text-white placeholder:text-gray-500"
                    required
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
                        Join Waitlist
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </form>

                {/* Counter */}
                <p className="mt-4 text-sm text-gray-400">
                  <span className="font-semibold text-landing-accent">847</span> engineers
                  already on the waitlist
                </p>
              </>
            ) : (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="inline-flex items-center gap-2 rounded-lg bg-green-900/50 px-6 py-3 text-green-400"
              >
                <CheckCircle2 className="h-5 w-5" />
                <span className="font-medium">You&apos;re on the list! Check your email.</span>
              </motion.div>
            )}
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
              No credit card required
            </span>
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-green-500" />
              Cancel anytime
            </span>
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-green-500" />
              SOC 2 compliant
            </span>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
