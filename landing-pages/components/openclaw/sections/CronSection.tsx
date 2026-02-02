"use client"

import { motion } from "framer-motion"
import { Clock, Play, Calendar, Bell, RefreshCw, Sun, Repeat, CalendarClock } from "lucide-react"
import { WobbleCard } from "@/components/ui/wobble-card"
import { Button as MovingBorderButton } from "@/components/ui/moving-border"

// Helper function to convert cron to human-readable format
function cronToHuman(schedule: string, type: string): { text: string; icon: React.ReactNode } {
  if (type === "One-shot") {
    // Parse ISO date
    const date = new Date(schedule)
    const options: Intl.DateTimeFormatOptions = {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    }
    return {
      text: date.toLocaleDateString('en-US', options),
      icon: <CalendarClock className="h-4 w-4" />
    }
  }

  // Parse cron expression
  if (schedule === "0 7 * * *") {
    return { text: "Every day at 7:00 AM", icon: <Sun className="h-4 w-4" /> }
  }
  if (schedule === "0 */4 * * *") {
    return { text: "Every 4 hours", icon: <Repeat className="h-4 w-4" /> }
  }
  if (schedule === "0 6 * * 1") {
    return { text: "Every Monday at 6:00 AM", icon: <Calendar className="h-4 w-4" /> }
  }

  return { text: schedule, icon: <Clock className="h-4 w-4" /> }
}

const cronJobs = [
  {
    icon: Calendar,
    title: "Morning Brief",
    description: "Summarize overnight updates and deliver to Slack channel",
    schedule: "0 7 * * *",
    timezone: "Pacific Time",
    type: "Recurring",
    color: "bg-amber-500",
  },
  {
    icon: Bell,
    title: "Daily Check-in",
    description: "Proactive status check every 4 hours",
    schedule: "0 */4 * * *",
    timezone: "UTC",
    type: "Recurring",
    color: "bg-blue-500",
  },
  {
    icon: RefreshCw,
    title: "Weekly Deep Analysis",
    description: "Comprehensive project progress analysis with high thinking",
    schedule: "0 6 * * 1",
    timezone: "Eastern Time",
    type: "Recurring",
    color: "bg-purple-500",
  },
  {
    icon: Play,
    title: "One-time Reminder",
    description: "Important meeting or deadline reminder",
    schedule: "2026-02-15T14:00:00Z",
    timezone: "UTC",
    type: "One-shot",
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
          <div className="mb-6 inline-flex items-center justify-center rounded-full border border-landing-border bg-landing-bg-muted px-4 py-2">
            <Clock className="mr-2 h-5 w-5 text-landing-accent" />
            <span className="text-sm font-medium text-landing-text-muted">
              Proactive Automation with Interval Timers
            </span>
          </div>

          <h2 className="mb-4 text-3xl font-bold tracking-tight text-landing-text md:text-4xl">
            It Works While You Sleep
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-landing-text-muted">
            Most AI tools wait for you to ask. OpenClaw acts on its own —
            sending morning briefs, checking in on projects, and reminding you before you forget.
          </p>
        </motion.div>

        <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-2">
          {cronJobs.map((job, index) => {
            const humanSchedule = cronToHuman(job.schedule, job.type)

            return (
              <motion.div
                key={job.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1, duration: 0.5 }}
              >
                <WobbleCard
                  containerClassName="h-full bg-white border border-landing-border"
                  className="p-6 py-8"
                >
                  <div className="relative z-10">
                    <div className="mb-4 flex items-start justify-between">
                      <div className={`inline-flex items-center justify-center rounded-xl ${job.color} p-3 text-white shadow-lg`}>
                        <job.icon className="h-6 w-6" />
                      </div>
                      <span className={`rounded-full ${job.type === "Recurring" ? "bg-landing-accent" : "bg-slate-700"} px-3 py-1 text-xs font-semibold text-white`}>
                        {job.type}
                      </span>
                    </div>

                    <h3 className="mb-2 text-xl font-bold text-landing-text">{job.title}</h3>
                    <p className="mb-6 text-base text-landing-text-muted">{job.description}</p>

                    {/* Human-readable time pill with moving border */}
                    <MovingBorderButton
                      as="div"
                      borderRadius="1rem"
                      containerClassName="w-full h-auto p-[2px]"
                      borderClassName="bg-[radial-gradient(var(--landing-accent)_40%,transparent_60%)]"
                      duration={3000}
                      className="flex items-center justify-between gap-3 bg-slate-50 px-4 py-3 text-landing-text"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-landing-accent">
                          {humanSchedule.icon}
                        </span>
                        <span className="font-medium">{humanSchedule.text}</span>
                      </div>
                      <span className="text-xs text-landing-text-muted">{job.timezone}</span>
                    </MovingBorderButton>
                  </div>
                </WobbleCard>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
