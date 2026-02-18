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
  purple: "#A78BFA",
  text: "rgba(255, 248, 235, 0.92)",
  textMuted: "rgba(255, 236, 205, 0.70)",
  textDim: "rgba(255, 236, 205, 0.50)",
  cardBg: "rgba(255, 208, 74, 0.06)",
  cardBorder: "rgba(255, 208, 74, 0.18)",
};

function PhaseNode({
  label,
  status,
  isActive,
}: {
  label: string;
  status: "completed" | "active" | "pending";
  isActive?: boolean;
}) {
  const statusColors = {
    completed: colors.green,
    active: colors.gold,
    pending: colors.textDim,
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "12px",
      }}
    >
      <div
        style={{
          width: "80px",
          height: "80px",
          borderRadius: "40px",
          background:
            status === "completed"
              ? `linear-gradient(135deg, ${colors.green} 0%, #3CB371 100%)`
              : status === "active"
                ? `linear-gradient(135deg, ${colors.gold} 0%, ${colors.orange} 100%)`
                : "rgba(255, 208, 74, 0.08)",
          border:
            status === "pending" ? `2px solid ${colors.cardBorder}` : "none",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow:
            status === "active"
              ? `0 0 30px rgba(255, 208, 74, 0.35)`
              : status === "completed"
                ? `0 0 20px rgba(80, 200, 120, 0.25)`
                : "none",
        }}
      >
        {status === "completed" ? (
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
            <path
              d="M20 6L9 17l-5-5"
              stroke="#fff"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ) : status === "active" ? (
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="3" fill="#1a150d" />
            <circle
              cx="12"
              cy="12"
              r="8"
              stroke="#1a150d"
              strokeWidth="2"
              strokeDasharray="4 4"
              fill="none"
            />
          </svg>
        ) : (
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <circle
              cx="12"
              cy="12"
              r="8"
              stroke={colors.textDim}
              strokeWidth="2"
              fill="none"
            />
          </svg>
        )}
      </div>
      <span
        style={{
          fontSize: "14px",
          fontFamily: "Montserrat",
          fontWeight: status === "active" ? 400 : 300,
          color: statusColors[status],
        }}
      >
        {label}
      </span>
    </div>
  );
}

function GateIcon({ approved }: { approved: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "8px",
      }}
    >
      <div
        style={{
          width: "44px",
          height: "44px",
          transform: "rotate(45deg)",
          background: approved
            ? "rgba(80, 200, 120, 0.15)"
            : "rgba(255, 208, 74, 0.12)",
          border: `2px solid ${approved ? colors.green : colors.gold}60`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ transform: "rotate(-45deg)", display: "flex" }}>
          {approved ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path
                d="M20 6L9 17l-5-5"
                stroke={colors.green}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2L2 7l10 5 10-5-10-5z"
                stroke={colors.gold}
                strokeWidth="2"
                fill="none"
              />
              <path
                d="M2 17l10 5 10-5"
                stroke={colors.gold}
                strokeWidth="2"
                fill="none"
              />
              <path
                d="M2 12l10 5 10-5"
                stroke={colors.gold}
                strokeWidth="2"
                fill="none"
              />
            </svg>
          )}
        </div>
      </div>
      <span
        style={{
          fontSize: "10px",
          fontFamily: "Montserrat",
          fontWeight: 300,
          color: approved ? colors.greenSoft : colors.goldSoft,
          textTransform: "uppercase",
          letterSpacing: "1px",
        }}
      >
        {approved ? "Approved" : "Gate"}
      </span>
    </div>
  );
}

function ConnectorLine({
  status,
}: {
  status: "completed" | "active" | "pending";
}) {
  const lineColor =
    status === "completed"
      ? colors.green
      : status === "active"
        ? colors.gold
        : colors.cardBorder;
  return (
    <div
      style={{
        width: "60px",
        height: "3px",
        background: lineColor,
        opacity: status === "pending" ? 0.4 : 0.7,
        borderRadius: "2px",
      }}
    />
  );
}

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
        padding: "50px 80px",
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
            "radial-gradient(ellipse 60% 40% at 50% 45%, rgba(255, 208, 74, 0.08) 0%, transparent 60%)",
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
          marginBottom: "40px",
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
            Autonomy With Oversight
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
            Approve at phase transitions, not every keystroke
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

      {/* Main Phase Flow */}
      <div
        style={{
          display: "flex",
          flex: 1,
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1,
        }}
      >
        {/* Phase pipeline */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginBottom: "50px",
          }}
        >
          <PhaseNode label="Requirements" status="completed" />
          <ConnectorLine status="completed" />
          <GateIcon approved={true} />
          <ConnectorLine status="completed" />
          <PhaseNode label="Design" status="completed" />
          <ConnectorLine status="completed" />
          <GateIcon approved={true} />
          <ConnectorLine status="active" />
          <PhaseNode label="Tasks" status="active" isActive />
          <ConnectorLine status="pending" />
          <GateIcon approved={false} />
          <ConnectorLine status="pending" />
          <PhaseNode label="Execution" status="pending" />
        </div>

        {/* Approval Dialog Card */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            width: "520px",
            background: "rgba(0, 0, 0, 0.45)",
            borderRadius: "20px",
            padding: "28px",
            border: `1px solid ${colors.gold}40`,
            boxShadow: `0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(255, 208, 74, 0.08)`,
          }}
        >
          {/* Dialog header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "20px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "18px",
                  background: `linear-gradient(135deg, ${colors.gold} 0%, ${colors.orange} 100%)`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M12 2L2 7l10 5 10-5-10-5z"
                    stroke="#1a150d"
                    strokeWidth="2"
                    fill="none"
                  />
                  <path
                    d="M2 17l10 5 10-5"
                    stroke="#1a150d"
                    strokeWidth="2"
                    fill="none"
                  />
                  <path
                    d="M2 12l10 5 10-5"
                    stroke="#1a150d"
                    strokeWidth="2"
                    fill="none"
                  />
                </svg>
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: "16px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.text,
                  }}
                >
                  Phase Gate Approval
                </span>
                <span
                  style={{
                    fontSize: "12px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textMuted,
                  }}
                >
                  Tasks → Execution
                </span>
              </div>
            </div>
            <div
              style={{
                display: "flex",
                padding: "6px 12px",
                background: "rgba(255, 208, 74, 0.12)",
                borderRadius: "8px",
                border: `1px solid ${colors.cardBorder}`,
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
                Awaiting Review
              </span>
            </div>
          </div>

          {/* Summary */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              background: "rgba(255, 208, 74, 0.04)",
              borderRadius: "12px",
              padding: "16px",
              marginBottom: "20px",
              border: `1px solid ${colors.cardBorder}`,
            }}
          >
            <span
              style={{
                fontSize: "11px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: colors.textDim,
                textTransform: "uppercase",
                letterSpacing: "1px",
                marginBottom: "10px",
              }}
            >
              Phase Summary
            </span>
            <div style={{ display: "flex", gap: "24px" }}>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: "24px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.gold,
                  }}
                >
                  12
                </span>
                <span
                  style={{
                    fontSize: "11px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textMuted,
                  }}
                >
                  Tasks Created
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: "24px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.green,
                  }}
                >
                  3
                </span>
                <span
                  style={{
                    fontSize: "11px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textMuted,
                  }}
                >
                  Dependencies
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: "24px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.purple,
                  }}
                >
                  2
                </span>
                <span
                  style={{
                    fontSize: "11px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textMuted,
                  }}
                >
                  Agents Ready
                </span>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div
            style={{
              display: "flex",
              gap: "12px",
            }}
          >
            <div
              style={{
                display: "flex",
                flex: 1,
                alignItems: "center",
                justifyContent: "center",
                padding: "14px",
                background: "rgba(255, 208, 74, 0.08)",
                borderRadius: "10px",
                border: `1px solid ${colors.cardBorder}`,
              }}
            >
              <span
                style={{
                  fontSize: "14px",
                  fontFamily: "Montserrat",
                  fontWeight: 400,
                  color: colors.textMuted,
                }}
              >
                Request Changes
              </span>
            </div>
            <div
              style={{
                display: "flex",
                flex: 1,
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                padding: "14px",
                background: `linear-gradient(135deg, ${colors.green} 0%, #3CB371 100%)`,
                borderRadius: "10px",
                boxShadow: `0 6px 20px rgba(80, 200, 120, 0.30)`,
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path
                  d="M20 6L9 17l-5-5"
                  stroke="#fff"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span
                style={{
                  fontSize: "14px",
                  fontFamily: "Montserrat",
                  fontWeight: 400,
                  color: "#fff",
                }}
              >
                Approve & Continue
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
          marginTop: "auto",
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
            Control where it matters, automation everywhere else
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
