"use client"

import { motion } from "framer-motion"
import { Star, Quote } from "lucide-react"

export function TestimonialSection() {
  return (
    <section className="bg-landing-bg py-16 md:py-20">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto max-w-3xl"
        >
          <div className="relative rounded-3xl bg-gradient-to-br from-slate-900 to-slate-800 p-8 md:p-12 shadow-xl">
            {/* Quote icon */}
            <Quote className="absolute top-6 right-6 h-12 w-12 text-landing-accent/20 md:h-16 md:w-16" />

            {/* Stars */}
            <div className="mb-6 flex gap-1">
              {[...Array(5)].map((_, i) => (
                <Star key={i} className="h-5 w-5 fill-amber-400 text-amber-400" />
              ))}
            </div>

            {/* Quote */}
            <blockquote className="mb-8 text-xl md:text-2xl font-medium text-white leading-relaxed">
              "I used to spend 2-3 hours every morning just responding to WhatsApp messages.
              Same questions, over and over. Now my bot handles all of that while I focus on
              actual client work. Best $49 I've spent this year."
            </blockquote>

            {/* Author */}
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-landing-accent to-orange-500 text-xl font-bold text-white">
                M
              </div>
              <div>
                <p className="font-semibold text-white">Marco R.</p>
                <p className="text-sm text-gray-400">Immigration Consultant, Miami</p>
              </div>
            </div>

            {/* Subtle badge */}
            <div className="mt-6 pt-6 border-t border-slate-700">
              <p className="text-sm text-gray-500">
                Beta user since January 2026
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
