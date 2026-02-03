"use client"

import { motion } from "framer-motion"
import { Quote, Clock, MessageSquare, TrendingUp } from "lucide-react"

const stats = [
  { icon: Clock, value: "4 hrs/day", label: "Time saved" },
  { icon: MessageSquare, value: "80%", label: "Auto-handled" },
  { icon: TrendingUp, value: "+3 clients", label: "First month" },
]

export function TestimonialSection() {
  return (
    <section className="bg-landing-bg py-16 md:py-20">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto max-w-4xl"
        >
          <div className="relative rounded-3xl bg-gradient-to-br from-slate-900 to-slate-800 p-8 md:p-12 shadow-xl overflow-hidden">
            {/* Background accent */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-landing-accent/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

            {/* Quote icon */}
            <Quote className="absolute top-6 right-6 h-12 w-12 text-landing-accent/20 md:h-16 md:w-16" />

            <div className="relative">
              {/* Mini case study label */}
              <div className="mb-6 inline-flex items-center rounded-full bg-landing-accent/20 px-3 py-1">
                <span className="text-xs font-semibold text-landing-accent uppercase tracking-wide">
                  Case Study
                </span>
              </div>

              {/* Story */}
              <p className="mb-8 text-lg md:text-xl text-gray-300 leading-relaxed">
                <span className="font-semibold text-white">Maria runs a relocation consultancy in Paraguay.</span>{" "}
                Before OpenClaw, she spent 4 hours every day answering the same WhatsApp questions —
                documents needed, timelines, costs. Now her AI handles 80% of inquiries automatically.
                She closed 3 extra clients in the first month just from faster response times.
              </p>

              {/* Stats */}
              <div className="mb-8 grid grid-cols-3 gap-4">
                {stats.map((stat) => (
                  <div key={stat.label} className="text-center">
                    <div className="mb-2 inline-flex items-center justify-center rounded-xl bg-white/5 p-3">
                      <stat.icon className="h-5 w-5 text-landing-accent" />
                    </div>
                    <p className="text-2xl font-bold text-white">{stat.value}</p>
                    <p className="text-xs text-gray-500">{stat.label}</p>
                  </div>
                ))}
              </div>

              {/* Quote */}
              <blockquote className="mb-6 text-lg md:text-xl font-medium text-white italic border-l-4 border-landing-accent pl-4">
                "I finally have my mornings back. The bot sounds exactly like me —
                clients don't even know the difference."
              </blockquote>

              {/* Author */}
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-landing-accent to-orange-500 text-lg font-bold text-white">
                  M
                </div>
                <div>
                  <p className="font-semibold text-white">Maria S.</p>
                  <p className="text-sm text-gray-400">Relocation Consultant, Asunción</p>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
