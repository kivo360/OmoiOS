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
  red: "#FF6B6B",
  text: "rgba(255, 248, 235, 0.92)",
  textMuted: "rgba(255, 236, 205, 0.70)",
  textDim: "rgba(255, 236, 205, 0.50)",
  cardBg: "rgba(255, 208, 74, 0.06)",
  cardBorder: "rgba(255, 208, 74, 0.18)",
  columnBg: "rgba(0, 0, 0, 0.25)",
}

// Task card component
function TaskCard({
  title,
  agent,
  phase,
  priority,
  isActive,
}: {
  title: string
  agent: string
  phase: "Planning" | "Building" | "Testing" | "Review"
  priority: "high" | "medium" | "low"
  isActive?: boolean
}) {
  const phaseColors = {
    Planning: colors.gold,
    Building: colors.orange,
    Testing: colors.green,
    Review: "#A78BFA",
  }

  const priorityColors = {
    high: colors.red,
    medium: colors.orange,
    low: colors.green,
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        background: colors.cardBg,
        border: `1px solid ${isActive ? colors.gold : colors.cardBorder}`,
        borderRadius: "10px",
        padding: "10px 12px",
        marginBottom: "8px",
        boxShadow: isActive
          ? `0 0 20px rgba(255, 208, 74, 0.15)`
          : "0 4px 12px rgba(0, 0, 0, 0.3)",
      }}
    >
      {/* Title */}
      <div
        style={{
          display: "flex",
          fontSize: "11px",
          fontFamily: "Montserrat",
          fontWeight: 400,
          color: colors.text,
          marginBottom: "8px",
          lineHeight: 1.3,
        }}
      >
        {title}
      </div>

      {/* Bottom row: agent + badges */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {/* Agent */}
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <div
            style={{
              width: "16px",
              height: "16px",
              borderRadius: "8px",
              background: `linear-gradient(135deg, ${colors.gold} 0%, ${colors.orange} 100%)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2a4 4 0 0 1 4 4v1a3 3 0 0 1 3 3v1a3 3 0 0 1-1 2.24V16a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4v-2.76A3 3 0 0 1 5 11v-1a3 3 0 0 1 3-3V6a4 4 0 0 1 4-4z"
                stroke="#1a150d"
                strokeWidth="2"
                fill="none"
              />
            </svg>
          </div>
          {isActive && (
            <div
              style={{
                width: "5px",
                height: "5px",
                borderRadius: "2.5px",
                background: colors.green,
                boxShadow: `0 0 4px ${colors.green}`,
              }}
            />
          )}
          <span
            style={{
              fontSize: "9px",
              fontFamily: "Montserrat",
              fontWeight: 300,
              color: colors.textMuted,
            }}
          >
            {agent}
          </span>
        </div>

        {/* Badges */}
        <div style={{ display: "flex", gap: "4px" }}>
          {/* Phase badge */}
          <div
            style={{
              display: "flex",
              padding: "2px 6px",
              borderRadius: "4px",
              background: `${phaseColors[phase]}20`,
              border: `1px solid ${phaseColors[phase]}40`,
            }}
          >
            <span
              style={{
                fontSize: "8px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: phaseColors[phase],
              }}
            >
              {phase}
            </span>
          </div>

          {/* Priority dot */}
          <div
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "3px",
              background: priorityColors[priority],
              alignSelf: "center",
            }}
          />
        </div>
      </div>
    </div>
  )
}

// Column component
function Column({
  title,
  count,
  children,
}: {
  title: string
  count: number
  children: React.ReactNode
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        width: "180px",
        background: colors.columnBg,
        borderRadius: "12px",
        padding: "12px",
        height: "100%",
      }}
    >
      {/* Column header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "10px",
        }}
      >
        <span
          style={{
            fontSize: "13px",
            fontFamily: "Montserrat",
            fontWeight: 400,
            color: colors.textMuted,
          }}
        >
          {title}
        </span>
        <div
          style={{
            display: "flex",
            padding: "2px 8px",
            borderRadius: "10px",
            background: "rgba(255, 208, 74, 0.12)",
          }}
        >
          <span
            style={{
              fontSize: "11px",
              fontFamily: "Montserrat",
              fontWeight: 400,
              color: colors.goldSoft,
            }}
          >
            {count}
          </span>
        </div>
      </div>

      {/* Cards */}
      <div style={{ display: "flex", flexDirection: "column" }}>{children}</div>
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
          padding: "30px 40px",
        }}
      >
        {/* Subtle texture */}
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
              "radial-gradient(ellipse 80% 60% at 50% 40%, rgba(255, 208, 74, 0.08) 0%, transparent 60%)",
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
            marginBottom: "20px",
            zIndex: 1,
          }}
        >
          {/* Left: Title + subtitle */}
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div
              style={{
                display: "flex",
                fontSize: "28px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: colors.text,
                marginBottom: "6px",
              }}
            >
              Watch Agents Work in Real-Time
            </div>
            <div
              style={{
                display: "flex",
                fontSize: "14px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: colors.textMuted,
              }}
            >
              Full visibility into every task, ticket, and agent
            </div>
          </div>

          {/* Right: Logo */}
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

        {/* Kanban Board */}
        <div
          style={{
            display: "flex",
            flex: 1,
            gap: "16px",
            zIndex: 1,
          }}
        >
          {/* Backlog */}
          <Column title="Backlog" count={2}>
            <TaskCard
              title="Add user authentication flow"
              agent="Agent-07"
              phase="Planning"
              priority="high"
            />
            <TaskCard
              title="Design database schema"
              agent="Agent-12"
              phase="Planning"
              priority="medium"
            />
          </Column>

          {/* In Progress */}
          <Column title="In Progress" count={2}>
            <TaskCard
              title="Implement Stripe webhook handler"
              agent="Agent-01"
              phase="Building"
              priority="high"
              isActive
            />
            <TaskCard
              title="Build payment form component"
              agent="Agent-04"
              phase="Building"
              priority="high"
              isActive
            />
          </Column>

          {/* Review */}
          <Column title="Review" count={2}>
            <TaskCard
              title="Validate checkout flow tests"
              agent="Agent-02"
              phase="Testing"
              priority="high"
            />
            <TaskCard
              title="Review subscription logic"
              agent="Agent-05"
              phase="Review"
              priority="medium"
            />
          </Column>

          {/* Done */}
          <Column title="Done" count={3}>
            <TaskCard
              title="Setup Stripe SDK integration"
              agent="Agent-01"
              phase="Building"
              priority="high"
            />
            <TaskCard
              title="Create payment types"
              agent="Agent-06"
              phase="Building"
              priority="medium"
            />
            <TaskCard
              title="Add environment config"
              agent="Agent-08"
              phase="Building"
              priority="low"
            />
          </Column>

          {/* Side Panel Preview */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              width: "200px",
              background: "rgba(0, 0, 0, 0.35)",
              borderRadius: "12px",
              padding: "12px",
              border: `1px solid ${colors.cardBorder}`,
            }}
          >
            {/* Panel header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "12px",
              }}
            >
              <div
                style={{
                  width: "26px",
                  height: "26px",
                  borderRadius: "13px",
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
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: "12px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.text,
                  }}
                >
                  Agent-01
                </span>
                <div style={{ display: "flex", alignItems: "center", gap: "3px" }}>
                  <div
                    style={{
                      width: "5px",
                      height: "5px",
                      borderRadius: "2.5px",
                      background: colors.green,
                      boxShadow: `0 0 4px ${colors.green}`,
                    }}
                  />
                  <span
                    style={{
                      fontSize: "9px",
                      fontFamily: "Montserrat",
                      fontWeight: 300,
                      color: colors.greenSoft,
                    }}
                  >
                    Active
                  </span>
                </div>
              </div>
            </div>

            {/* Activity feed */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  fontSize: "9px",
                  fontFamily: "Montserrat",
                  fontWeight: 300,
                  color: colors.textDim,
                  textTransform: "uppercase",
                  letterSpacing: "1px",
                  marginBottom: "2px",
                }}
              >
                Live Activity
              </div>

              {/* Activity items */}
              {[
                { time: "now", action: "Writing webhook handler..." },
                { time: "2m", action: "Analyzed Stripe SDK docs" },
                { time: "5m", action: "Created event types" },
              ].map((item, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "6px",
                  }}
                >
                  <span
                    style={{
                      fontSize: "8px",
                      fontFamily: "Montserrat",
                      fontWeight: 300,
                      color: colors.textDim,
                      width: "22px",
                      flexShrink: 0,
                    }}
                  >
                    {item.time}
                  </span>
                  <span
                    style={{
                      fontSize: "9px",
                      fontFamily: "Montserrat",
                      fontWeight: 300,
                      color: i === 0 ? colors.gold : colors.textMuted,
                    }}
                  >
                    {item.action}
                  </span>
                </div>
              ))}
            </div>

            {/* Bottom stats */}
            <div
              style={{
                display: "flex",
                marginTop: "auto",
                paddingTop: "10px",
                borderTop: `1px solid ${colors.cardBorder}`,
                gap: "12px",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: "14px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.gold,
                  }}
                >
                  47
                </span>
                <span
                  style={{
                    fontSize: "8px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textDim,
                  }}
                >
                  Files Changed
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: "14px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.green,
                  }}
                >
                  12
                </span>
                <span
                  style={{
                    fontSize: "8px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textDim,
                  }}
                >
                  Tests Passing
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom tagline */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginTop: "16px",
            zIndex: 1,
          }}
        >
          <div
            style={{
              display: "flex",
              background: "rgba(255, 208, 74, 0.08)",
              borderRadius: "999px",
              padding: "8px 16px",
              border: `1px solid ${colors.cardBorder}`,
            }}
          >
            <span
              style={{
                fontSize: "12px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: colors.textMuted,
              }}
            >
              Never wonder what your agents are doing
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
