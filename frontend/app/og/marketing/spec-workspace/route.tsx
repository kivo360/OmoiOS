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
  blue: "#60A5FA",
  purple: "#A78BFA",
  text: "rgba(255, 248, 235, 0.92)",
  textMuted: "rgba(255, 236, 205, 0.70)",
  textDim: "rgba(255, 236, 205, 0.50)",
  cardBg: "rgba(255, 208, 74, 0.06)",
  cardBorder: "rgba(255, 208, 74, 0.18)",
}

function Tab({ label, active }: { label: string; active?: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        padding: "10px 20px",
        background: active ? "rgba(255, 208, 74, 0.12)" : "transparent",
        borderBottom: active ? `2px solid ${colors.gold}` : "2px solid transparent",
      }}
    >
      <span
        style={{
          fontSize: "13px",
          fontFamily: "Montserrat",
          fontWeight: active ? 400 : 300,
          color: active ? colors.gold : colors.textMuted,
        }}
      >
        {label}
      </span>
    </div>
  )
}

function RequirementBlock({
  id,
  text,
  criteria,
}: {
  id: string
  text: string
  criteria: string[]
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        background: colors.cardBg,
        borderRadius: "12px",
        padding: "16px",
        border: `1px solid ${colors.cardBorder}`,
        marginBottom: "12px",
      }}
    >
      {/* Requirement ID + text */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: "10px", marginBottom: "12px" }}>
        <div
          style={{
            display: "flex",
            padding: "4px 8px",
            background: "rgba(255, 208, 74, 0.15)",
            borderRadius: "6px",
            flexShrink: 0,
          }}
        >
          <span
            style={{
              fontSize: "10px",
              fontFamily: "Montserrat",
              fontWeight: 400,
              color: colors.gold,
            }}
          >
            {id}
          </span>
        </div>
        <span
          style={{
            fontSize: "13px",
            fontFamily: "Montserrat",
            fontWeight: 400,
            color: colors.text,
            lineHeight: 1.4,
          }}
        >
          {text}
        </span>
      </div>

      {/* Acceptance criteria */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px", paddingLeft: "8px" }}>
        {criteria.map((c, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div
              style={{
                width: "14px",
                height: "14px",
                borderRadius: "4px",
                background: i < 2 ? colors.green : "transparent",
                border: i < 2 ? "none" : `1.5px solid ${colors.textDim}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              {i < 2 && (
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M20 6L9 17l-5-5"
                    stroke="#fff"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </div>
            <span
              style={{
                fontSize: "11px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: i < 2 ? colors.textMuted : colors.textDim,
              }}
            >
              {c}
            </span>
          </div>
        ))}
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
              "radial-gradient(ellipse 70% 50% at 60% 50%, rgba(255, 208, 74, 0.06) 0%, transparent 60%)",
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
              Specs, Not Vibes
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
              Structured requirements before a single line of code
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

        {/* Main Content - Spec Workspace UI */}
        <div
          style={{
            display: "flex",
            flex: 1,
            gap: "20px",
            zIndex: 1,
          }}
        >
          {/* Left Sidebar - Spec Navigator */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              width: "200px",
              background: "rgba(0, 0, 0, 0.30)",
              borderRadius: "14px",
              padding: "16px",
              border: `1px solid ${colors.cardBorder}`,
            }}
          >
            <div
              style={{
                display: "flex",
                fontSize: "11px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: colors.textDim,
                textTransform: "uppercase",
                letterSpacing: "1px",
                marginBottom: "14px",
              }}
            >
              Specs
            </div>

            {/* Spec list items */}
            {[
              { name: "Payment Processing", active: true },
              { name: "User Authentication", active: false },
              { name: "Dashboard Analytics", active: false },
            ].map((spec, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "10px 12px",
                  background: spec.active ? "rgba(255, 208, 74, 0.10)" : "transparent",
                  borderRadius: "8px",
                  marginBottom: "6px",
                  border: spec.active ? `1px solid ${colors.gold}40` : "1px solid transparent",
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
                    stroke={spec.active ? colors.gold : colors.textDim}
                    strokeWidth="2"
                    fill="none"
                  />
                  <polyline
                    points="14,2 14,8 20,8"
                    stroke={spec.active ? colors.gold : colors.textDim}
                    strokeWidth="2"
                    fill="none"
                  />
                </svg>
                <span
                  style={{
                    fontSize: "12px",
                    fontFamily: "Montserrat",
                    fontWeight: spec.active ? 400 : 300,
                    color: spec.active ? colors.gold : colors.textMuted,
                  }}
                >
                  {spec.name}
                </span>
              </div>
            ))}
          </div>

          {/* Main Workspace */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              flex: 1,
              background: "rgba(0, 0, 0, 0.35)",
              borderRadius: "14px",
              border: `1px solid ${colors.cardBorder}`,
              overflow: "hidden",
            }}
          >
            {/* Tab bar */}
            <div
              style={{
                display: "flex",
                borderBottom: `1px solid ${colors.cardBorder}`,
              }}
            >
              <Tab label="Requirements" active />
              <Tab label="Design" />
              <Tab label="Tasks" />
              <Tab label="Execution" />
            </div>

            {/* Content area */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                padding: "20px",
                flex: 1,
              }}
            >
              {/* Spec title */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "20px",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span
                    style={{
                      fontSize: "18px",
                      fontFamily: "Montserrat",
                      fontWeight: 400,
                      color: colors.text,
                    }}
                  >
                    Payment Processing
                  </span>
                  <span
                    style={{
                      fontSize: "12px",
                      fontFamily: "Montserrat",
                      fontWeight: 300,
                      color: colors.textMuted,
                    }}
                  >
                    Stripe integration with subscriptions
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    padding: "6px 14px",
                    background: "rgba(255, 208, 74, 0.12)",
                    borderRadius: "8px",
                    border: `1px solid ${colors.gold}40`,
                  }}
                >
                  <span
                    style={{
                      fontSize: "11px",
                      fontFamily: "Montserrat",
                      fontWeight: 400,
                      color: colors.gold,
                    }}
                  >
                    Requirements Phase
                  </span>
                </div>
              </div>

              {/* Requirements blocks */}
              <RequirementBlock
                id="REQ-001"
                text="WHEN a customer initiates checkout, THE SYSTEM SHALL create a Stripe payment intent with the cart total"
                criteria={[
                  "Payment intent created within 2s",
                  "Cart total matches Stripe amount",
                  "Customer email attached to intent",
                ]}
              />

              <RequirementBlock
                id="REQ-002"
                text="WHEN payment succeeds, THE SYSTEM SHALL update order status and send confirmation email"
                criteria={[
                  "Order status changes to 'paid'",
                  "Confirmation email sent within 30s",
                  "Webhook signature validated",
                ]}
              />

              {/* Phase approval button */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  marginTop: "auto",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "12px 24px",
                    background: `linear-gradient(135deg, ${colors.gold} 0%, ${colors.orange} 100%)`,
                    borderRadius: "10px",
                    boxShadow: `0 6px 20px rgba(255, 208, 74, 0.25)`,
                  }}
                >
                  <span
                    style={{
                      fontSize: "13px",
                      fontFamily: "Montserrat",
                      fontWeight: 400,
                      color: "#1a150d",
                    }}
                  >
                    Approve & Continue to Design
                  </span>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M5 12h14M12 5l7 7-7 7"
                      stroke="#1a150d"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          {/* Right Panel - Progress */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              width: "180px",
              background: "rgba(0, 0, 0, 0.30)",
              borderRadius: "14px",
              padding: "16px",
              border: `1px solid ${colors.cardBorder}`,
            }}
          >
            <div
              style={{
                display: "flex",
                fontSize: "11px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: colors.textDim,
                textTransform: "uppercase",
                letterSpacing: "1px",
                marginBottom: "16px",
              }}
            >
              Progress
            </div>

            {/* Progress items */}
            {[
              { label: "Requirements", status: "active", count: "8/10" },
              { label: "Design", status: "pending", count: "0/5" },
              { label: "Tasks", status: "pending", count: "0/12" },
              { label: "Execution", status: "pending", count: "—" },
            ].map((item, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 0",
                  borderBottom:
                    i < 3 ? `1px solid ${colors.cardBorder}` : "none",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <div
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "4px",
                      background:
                        item.status === "active"
                          ? colors.gold
                          : item.status === "completed"
                            ? colors.green
                            : colors.textDim,
                    }}
                  />
                  <span
                    style={{
                      fontSize: "12px",
                      fontFamily: "Montserrat",
                      fontWeight: item.status === "active" ? 400 : 300,
                      color:
                        item.status === "active"
                          ? colors.gold
                          : colors.textMuted,
                    }}
                  >
                    {item.label}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: "11px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textDim,
                  }}
                >
                  {item.count}
                </span>
              </div>
            ))}
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
              Spec-driven {">"} vibe-driven development
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
