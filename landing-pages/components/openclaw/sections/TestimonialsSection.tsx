"use client"

import { motion } from "framer-motion"
import { Star, Quote } from "lucide-react"

// TODO: Replace with real testimonials when available
const testimonials = [
  {
    quote: "OpenClaw saved me 15+ hours a week. I used to spend my mornings manually checking emails and Slack — now my bot handles it before I wake up.",
    author: "Sarah K.",
    role: "Agency Owner",
    avatar: null, // Add image URL when available
    rating: 5,
  },
  {
    quote: "Finally, AI that actually runs without me babysitting it. The cron job setup alone was worth the price.",
    author: "Marcus T.",
    role: "Solopreneur",
    avatar: null,
    rating: 5,
  },
  {
    quote: "I was skeptical about the 'runs on your devices' claim, but it actually works. My data never leaves my server.",
    author: "James L.",
    role: "CTO, Startup",
    avatar: null,
    rating: 5,
  },
]

export function TestimonialsSection() {
  // Uncomment this section when you have real testimonials
  // For now, return null to hide the section
  return null

  /*
  return (
    <section className="bg-landing-bg py-20 md:py-28">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-12 max-w-2xl text-center"
        >
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            What Early Adopters Say
          </h2>
          <p className="text-lg text-landing-text-muted">
            Real results from real users who stopped babysitting ChatGPT.
          </p>
        </motion.div>

        <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-3">
          {testimonials.map((testimonial, index) => (
            <motion.div
              key={testimonial.author}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className="relative rounded-2xl border border-landing-border bg-white p-8 shadow-sm"
            >
              <Quote className="absolute top-6 right-6 h-8 w-8 text-landing-accent/20" />

              <div className="mb-4 flex gap-1">
                {[...Array(testimonial.rating)].map((_, i) => (
                  <Star key={i} className="h-5 w-5 fill-amber-400 text-amber-400" />
                ))}
              </div>

              <p className="mb-6 text-landing-text-muted leading-relaxed">
                "{testimonial.quote}"
              </p>

              <div className="flex items-center gap-3">
                {testimonial.avatar ? (
                  <img
                    src={testimonial.avatar}
                    alt={testimonial.author}
                    className="h-12 w-12 rounded-full object-cover"
                  />
                ) : (
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-landing-accent text-white font-bold">
                    {testimonial.author[0]}
                  </div>
                )}
                <div>
                  <p className="font-semibold text-landing-text">{testimonial.author}</p>
                  <p className="text-sm text-landing-text-muted">{testimonial.role}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
  */
}
