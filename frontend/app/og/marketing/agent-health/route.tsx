import { ImageResponse } from "next/og"

export const runtime = "edge"

// Color palette - warmer tones matching main OG image
const colors = {
  bg: "#1a150d",
  bgGradient: "linear-gradient(145deg, #2d2618 0%, #1a150d 50%, #0f0c08 100%)",
  gold: "#FFD04A",
  goldSoft: "rgba(255, 208, 74, 0.70)",
  goldMuted: "rgba(255, 208, 74, 0.40)",
  green: "#50C878",
  greenSoft: "rgba(80, 200, 120, 0.85)",
  orange: "#FF8A2A",
  yellow: "#FBBF24",
  red: "#FF6B6B",
  text: "rgba(255, 248, 235, 0.92)",
  textMuted: "rgba(255, 236, 205, 0.70)",
  textDim: "rgba(255, 236, 205, 0.50)",
  cardBg: "rgba(255, 208, 74, 0.06)",
  cardBorder: "rgba(255, 208, 74, 0.18)",
}

function AgentHealthCard({
  name,
  status,
  task,
}: {
  name: string
  status: "healthy" | "warning" | "intervened"
  task: string
}) {
  const statusConfig = {
    healthy: { color: colors.green, label: "Healthy", glow: "rgba(80, 200, 120, 0.20)" },
    warning: { color: colors.yellow, label: "Warning", glow: "rgba(251, 191, 36, 0.20)" },
    intervened: { color: colors.gold, label: "Steered", glow: "rgba(255, 208, 74, 0.20)" },
  }

  const config = statusConfig[status]

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        width: "180px",
        background: colors.cardBg,
        borderRadius: "14px",
        padding: "16px",
        border: `1px solid ${colors.cardBorder}`,
        boxShadow: status !== "healthy" ? `0 0 20px ${config.glow}` : "none",
      }}
    >
      {/* Agent header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div
            style={{
              width: "28px",
              height: "28px",
              borderRadius: "14px",
              background: `linear-gradient(135deg, ${colors.gold} 0%, ${colors.orange} 100%)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2a4 4 0 0 1 4 4v1a3 3 0 0 1 3 3v1a3 3 0 0 1-1 2.24V16a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4v-2.76A3 3 0 0 1 5 11v-1a3 3 0 0 1 3-3V6a4 4 0 0 1 4-4z"
                stroke="#1a150d"
                strokeWidth="2"
                fill="none"
              />
            </svg>
          </div>
          <span
            style={{
              fontSize: "13px",
              fontFamily: "Montserrat",
              fontWeight: 400,
              color: colors.text,
            }}
          >
            {name}
          </span>
        </div>
        <div
          style={{
            width: "10px",
            height: "10px",
            borderRadius: "5px",
            background: config.color,
            boxShadow: `0 0 8px ${config.color}`,
          }}
        />
      </div>

      {/* Task */}
      <div
        style={{
          display: "flex",
          fontSize: "11px",
          fontFamily: "Montserrat",
          fontWeight: 300,
          color: colors.textMuted,
          marginBottom: "10px",
          lineHeight: 1.4,
        }}
      >
        {task}
      </div>

      {/* Status badge */}
      <div
        style={{
          display: "flex",
          padding: "4px 10px",
          background: `${config.color}15`,
          borderRadius: "6px",
          border: `1px solid ${config.color}30`,
          alignSelf: "flex-start",
        }}
      >
        <span
          style={{
            fontSize: "10px",
            fontFamily: "Montserrat",
            fontWeight: 400,
            color: config.color,
          }}
        >
          {config.label}
        </span>
      </div>
    </div>
  )
}

function InterventionItem({
  time,
  issue,
  action,
}: {
  time: string
  issue: string
  action: string
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "12px",
        padding: "12px 0",
        borderBottom: `1px solid ${colors.cardBorder}`,
      }}
    >
      <span
        style={{
          fontSize: "11px",
          fontFamily: "Montserrat",
          fontWeight: 300,
          color: colors.textDim,
          width: "40px",
          flexShrink: 0,
        }}
      >
        {time}
      </span>
      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <span
          style={{
            fontSize: "12px",
            fontFamily: "Montserrat",
            fontWeight: 400,
            color: colors.text,
          }}
        >
          {issue}
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <path
              d="M5 12h14M12 5l7 7-7 7"
              stroke={colors.green}
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span
            style={{
              fontSize: "11px",
              fontFamily: "Montserrat",
              fontWeight: 300,
              color: colors.greenSoft,
            }}
          >
            {action}
          </span>
        </div>
      </div>
    </div>
  )
}

export async function GET() {
  const montserratRegular = fetch(
    new URL("../../../../public/fonts/Montserrat-Regular.ttf", import.meta.url)
  ).then((res) => res.arrayBuffer())

  const montserratLight = fetch(
    new URL("../../../../public/fonts/Montserrat-Light.ttf", import.meta.url)
  ).then((res) => res.arrayBuffer())

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          background: colors.bgGradient,
          position: "relative",
          padding: "50px 60px",
        }}
      >
        {/* Texture */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundImage:
              "radial-gradient(rgba(255, 208, 74, 0.03) 1px, transparent 1px)",
            backgroundSize: "32px 32px",
            display: "flex",
          }}
        />

        {/* Warm golden overlay - matching main OG image */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              "radial-gradient(ellipse 100% 80% at 30% 30%, rgba(255,200,50,0.12) 0%, transparent 50%)",
            display: "flex",
          }}
        />

        {/* Ambient glow */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              "radial-gradient(ellipse 50% 40% at 30% 50%, rgba(80, 200, 120, 0.06) 0%, transparent 60%), radial-gradient(ellipse 50% 40% at 70% 50%, rgba(255, 208, 74, 0.06) 0%, transparent 60%)",
            display: "flex",
          }}
        />

        {/* Vignette */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              "radial-gradient(ellipse 120% 90% at 50% 50%, transparent 52%, rgba(0,0,0,0.5) 100%)",
            display: "flex",
          }}
        />

        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            marginBottom: "30px",
            zIndex: 1,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div
              style={{
                display: "flex",
                fontSize: "36px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: colors.text,
                marginBottom: "10px",
              }}
            >
              Agents That Fix Themselves
            </div>
            <div
              style={{
                display: "flex",
                fontSize: "18px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: colors.textMuted,
              }}
            >
              Guardian monitors, detects drift, and intervenes automatically
            </div>
          </div>

          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center" }}>
            <svg
              width="36"
              height="36"
              viewBox="0 0 512 512"
              fill="none"
              style={{ marginRight: "10px" }}
            >
              <defs>
                <linearGradient
                  id="goldStroke"
                  x1="120"
                  y1="96"
                  x2="392"
                  y2="416"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop offset="0" stopColor="#FFE78A" />
                  <stop offset="0.35" stopColor="#FFD04A" />
                  <stop offset="1" stopColor="#FF8A2A" />
                </linearGradient>
              </defs>
              <g stroke="url(#goldStroke)" strokeLinecap="round" strokeLinejoin="round">
                <g strokeWidth="20">
                  <circle cx="256" cy="256" r="112" fill="none" />
                  <circle cx="368" cy="256" r="112" fill="none" />
                  <circle cx="312" cy="352.99" r="112" fill="none" />
                  <circle cx="200" cy="352.99" r="112" fill="none" />
                  <circle cx="144" cy="256" r="112" fill="none" />
                  <circle cx="200" cy="159.01" r="112" fill="none" />
                  <circle cx="312" cy="159.01" r="112" fill="none" />
                </g>
              </g>
            </svg>
            <span
              style={{
                fontSize: "22px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: colors.text,
              }}
            >
              OmoiOS
            </span>
          </div>
        </div>

        {/* Main Content */}
        <div
          style={{
            display: "flex",
            flex: 1,
            gap: "30px",
            zIndex: 1,
          }}
        >
          {/* Left: Agent Grid */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              flex: 1,
            }}
          >
            {/* Section label */}
            <div
              style={{
                display: "flex",
                fontSize: "11px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: colors.textDim,
                textTransform: "uppercase",
                letterSpacing: "1.5px",
                marginBottom: "16px",
              }}
            >
              Active Agents
            </div>

            {/* Agent grid */}
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "14px",
              }}
            >
              <AgentHealthCard name="Agent-01" status="healthy" task="Building checkout API" />
              <AgentHealthCard name="Agent-02" status="healthy" task="Writing unit tests" />
              <AgentHealthCard
                name="Agent-03"
                status="intervened"
                task="Was stuck on auth → Redirected"
              />
              <AgentHealthCard name="Agent-04" status="healthy" task="Database migrations" />
              <AgentHealthCard
                name="Agent-05"
                status="warning"
                task="High token usage detected"
              />
              <AgentHealthCard name="Agent-06" status="healthy" task="Frontend components" />
            </div>

            {/* Stats row */}
            <div
              style={{
                display: "flex",
                gap: "30px",
                marginTop: "auto",
                paddingTop: "20px",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: "32px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.green,
                  }}
                >
                  6
                </span>
                <span
                  style={{
                    fontSize: "12px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textMuted,
                  }}
                >
                  Active Agents
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: "32px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.gold,
                  }}
                >
                  14
                </span>
                <span
                  style={{
                    fontSize: "12px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textMuted,
                  }}
                >
                  Interventions Today
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: "32px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.text,
                  }}
                >
                  47s
                </span>
                <span
                  style={{
                    fontSize: "12px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textMuted,
                  }}
                >
                  Avg. Resolution
                </span>
              </div>
            </div>
          </div>

          {/* Right: Intervention Timeline */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              width: "380px",
              background: "rgba(0, 0, 0, 0.35)",
              borderRadius: "18px",
              padding: "20px",
              border: `1px solid ${colors.cardBorder}`,
            }}
          >
            {/* Header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                marginBottom: "16px",
              }}
            >
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "16px",
                  background: "rgba(80, 200, 120, 0.15)",
                  border: `1px solid ${colors.green}40`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"
                    stroke={colors.green}
                    strokeWidth="2"
                    fill="none"
                  />
                </svg>
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: "14px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.text,
                  }}
                >
                  Guardian Interventions
                </span>
                <span
                  style={{
                    fontSize: "11px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.greenSoft,
                  }}
                >
                  Auto-resolved issues
                </span>
              </div>
            </div>

            {/* Timeline */}
            <div style={{ display: "flex", flexDirection: "column" }}>
              <InterventionItem
                time="2m ago"
                issue="Agent-03 stuck on auth error loop"
                action="Sent steering: Use cached token"
              />
              <InterventionItem
                time="8m ago"
                issue="Agent-05 token usage spike"
                action="Reduced context window"
              />
              <InterventionItem
                time="15m ago"
                issue="Agent-02 constraint violation"
                action="Rolled back & retried"
              />
              <InterventionItem
                time="23m ago"
                issue="Agent-01 idle timeout"
                action="Resumed with checkpoint"
              />
            </div>

            {/* Guardian status */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                marginTop: "auto",
                paddingTop: "16px",
              }}
            >
              <div
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "4px",
                  background: colors.green,
                  boxShadow: `0 0 8px ${colors.green}`,
                }}
              />
              <span
                style={{
                  fontSize: "12px",
                  fontFamily: "Montserrat",
                  fontWeight: 300,
                  color: colors.greenSoft,
                }}
              >
                Guardian monitoring every 30s
              </span>
            </div>
          </div>
        </div>

        {/* Bottom tagline */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginTop: "24px",
            zIndex: 1,
          }}
        >
          <div
            style={{
              display: "flex",
              background: "rgba(255, 208, 74, 0.08)",
              borderRadius: "999px",
              padding: "10px 20px",
              border: `1px solid ${colors.cardBorder}`,
            }}
          >
            <span
              style={{
                fontSize: "14px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: colors.textMuted,
              }}
            >
              Self-healing workflows that don't need babysitting
            </span>
          </div>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
      fonts: [
        {
          name: "Montserrat",
          data: await montserratRegular,
          style: "normal",
          weight: 400,
        },
        {
          name: "Montserrat",
          data: await montserratLight,
          style: "normal",
          weight: 300,
        },
      ],
    }
  )
}
