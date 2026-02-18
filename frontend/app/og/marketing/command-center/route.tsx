import { ImageResponse } from "next/og";

export const runtime = "edge";

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
  text: "rgba(255, 248, 235, 0.92)",
  textMuted: "rgba(255, 236, 205, 0.70)",
  textDim: "rgba(255, 236, 205, 0.50)",
  cardBg: "rgba(255, 208, 74, 0.06)",
  cardBorder: "rgba(255, 208, 74, 0.18)",
  inputBg: "rgba(0, 0, 0, 0.35)",
};

export async function GET() {
  const montserratRegular = fetch(
    new URL("../../../../public/fonts/Montserrat-Regular.ttf", import.meta.url),
  ).then((res) => res.arrayBuffer());

  const montserratLight = fetch(
    new URL("../../../../public/fonts/Montserrat-Light.ttf", import.meta.url),
  ).then((res) => res.arrayBuffer());

  return new ImageResponse(
    <div
      style={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        background: colors.bgGradient,
        position: "relative",
        padding: "36px 60px",
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

      {/* Ambient glow - centered on input */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background:
            "radial-gradient(ellipse 70% 50% at 50% 55%, rgba(255, 208, 74, 0.10) 0%, transparent 60%)",
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
          marginBottom: "24px",
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
            Describe What You Want Built
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
            Type a feature request → OmoiOS plans and executes
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
            <g
              stroke="url(#goldStroke)"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
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

      {/* Main Command Center UI */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          flex: 1,
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1,
        }}
      >
        {/* Command Card */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            width: "820px",
            background: "rgba(0, 0, 0, 0.40)",
            borderRadius: "20px",
            padding: "28px",
            border: `1px solid ${colors.cardBorder}`,
            boxShadow: "0 20px 60px rgba(0, 0, 0, 0.5)",
          }}
        >
          {/* Top row: Repo selector + Model selector */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "16px",
            }}
          >
            {/* Repo selector */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "10px 16px",
                background: colors.inputBg,
                borderRadius: "12px",
                border: `1px solid ${colors.cardBorder}`,
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path
                  d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"
                  stroke={colors.goldSoft}
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
              </svg>
              <span
                style={{
                  fontSize: "14px",
                  fontFamily: "Montserrat",
                  fontWeight: 400,
                  color: colors.text,
                }}
              >
                acme/webapp
              </span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path
                  d="M6 9l6 6 6-6"
                  stroke={colors.textMuted}
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>

            {/* Model selector */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "10px 16px",
                background: colors.inputBg,
                borderRadius: "12px",
                border: `1px solid ${colors.cardBorder}`,
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 2a4 4 0 0 1 4 4v1a3 3 0 0 1 3 3v1a3 3 0 0 1-1 2.24V16a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4v-2.76A3 3 0 0 1 5 11v-1a3 3 0 0 1 3-3V6a4 4 0 0 1 4-4z"
                  stroke={colors.goldSoft}
                  strokeWidth="2"
                  fill="none"
                />
              </svg>
              <span
                style={{
                  fontSize: "14px",
                  fontFamily: "Montserrat",
                  fontWeight: 400,
                  color: colors.text,
                }}
              >
                Claude Opus 4.5
              </span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path
                  d="M6 9l6 6 6-6"
                  stroke={colors.textMuted}
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
          </div>

          {/* Main input area */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              background: colors.inputBg,
              borderRadius: "14px",
              border: `2px solid ${colors.gold}40`,
              padding: "16px 20px",
              marginBottom: "16px",
              boxShadow: `0 0 30px rgba(255, 208, 74, 0.08)`,
            }}
          >
            <div
              style={{
                display: "flex",
                fontSize: "16px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: colors.text,
                marginBottom: "6px",
              }}
            >
              Add payment processing with Stripe
            </div>
            <div
              style={{
                display: "flex",
                fontSize: "12px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: colors.textDim,
              }}
            >
              Include checkout flow, subscription management, and webhook
              handling...
            </div>
          </div>

          {/* Bottom row: Mode selector + Launch button */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            {/* Mode selector */}
            <div
              style={{
                display: "flex",
                gap: "8px",
              }}
            >
              {/* Quick mode */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "10px 18px",
                  background: "rgba(255, 208, 74, 0.08)",
                  borderRadius: "10px",
                  border: `1px solid ${colors.cardBorder}`,
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"
                    stroke={colors.textMuted}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                  />
                </svg>
                <span
                  style={{
                    fontSize: "13px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.textMuted,
                  }}
                >
                  Quick
                </span>
              </div>

              {/* Spec-driven mode (selected) */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "10px 18px",
                  background: "rgba(255, 208, 74, 0.18)",
                  borderRadius: "10px",
                  border: `2px solid ${colors.gold}`,
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
                    stroke={colors.gold}
                    strokeWidth="2"
                    fill="none"
                  />
                  <polyline
                    points="14,2 14,8 20,8"
                    stroke={colors.gold}
                    strokeWidth="2"
                    fill="none"
                  />
                </svg>
                <span
                  style={{
                    fontSize: "13px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.gold,
                  }}
                >
                  Spec-Driven
                </span>
              </div>
            </div>

            {/* Launch button */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "14px 32px",
                background: `linear-gradient(135deg, ${colors.gold} 0%, ${colors.orange} 100%)`,
                borderRadius: "12px",
                boxShadow: `0 8px 24px rgba(255, 208, 74, 0.30)`,
              }}
            >
              <span
                style={{
                  fontSize: "15px",
                  fontFamily: "Montserrat",
                  fontWeight: 400,
                  color: "#1a150d",
                }}
              >
                Launch Workflow
              </span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
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

        {/* Below card: What happens next */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "28px",
            marginTop: "20px",
          }}
        >
          {[
            { icon: "📋", label: "Generate Spec" },
            { icon: "→", label: "" },
            { icon: "✅", label: "Review & Approve" },
            { icon: "→", label: "" },
            { icon: "🤖", label: "Agents Execute" },
            { icon: "→", label: "" },
            { icon: "🚀", label: "Ship PR" },
          ].map((step, i) =>
            step.label ? (
              <div
                key={i}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <span style={{ fontSize: "20px" }}>{step.icon}</span>
                <span
                  style={{
                    fontSize: "10px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textMuted,
                  }}
                >
                  {step.label}
                </span>
              </div>
            ) : (
              <span
                key={i}
                style={{
                  fontSize: "14px",
                  color: colors.goldMuted,
                }}
              >
                →
              </span>
            ),
          )}
        </div>
      </div>

      {/* Bottom tagline */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          marginTop: "auto",
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
            From idea to PR in minutes, not days
          </span>
        </div>
      </div>
    </div>,
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
    },
  );
}
