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

// Graph layout configuration
const graph = {
  nodes: [
    // Main branch
    { id: "spec", x: 80, y: 380, label: "Spec", status: "completed" as const },
    { id: "api", x: 240, y: 380, label: "API Design", status: "completed" as const },
    { id: "db", x: 400, y: 300, label: "DB Schema", status: "completed" as const },
    { id: "auth", x: 400, y: 460, label: "Auth Flow", status: "active" as const },
    { id: "endpoints", x: 560, y: 300, label: "Endpoints", status: "active" as const },
    { id: "webhook", x: 560, y: 460, label: "Webhooks", status: "pending" as const },
    { id: "tests", x: 720, y: 380, label: "Integration", status: "pending" as const },
    { id: "pr", x: 880, y: 380, label: "PR Ready", status: "pending" as const },
    // Discovery branch
    { id: "cache", x: 560, y: 180, label: "Caching", status: "discovered" as const, discovered: true },
    { id: "perf", x: 720, y: 180, label: "Perf Tests", status: "discovered" as const, discovered: true },
  ],
  edges: [
    { from: "spec", to: "api" },
    { from: "api", to: "db" },
    { from: "api", to: "auth" },
    { from: "db", to: "endpoints" },
    { from: "auth", to: "webhook" },
    { from: "endpoints", to: "tests" },
    { from: "webhook", to: "tests" },
    { from: "tests", to: "pr" },
    // Discovery edges
    { from: "db", to: "cache", discovered: true },
    { from: "cache", to: "perf", discovered: true },
    { from: "perf", to: "tests", discovered: true },
  ],
}

function GraphNode({
  x,
  y,
  label,
  status,
  discovered,
}: {
  x: number
  y: number
  label: string
  status: "completed" | "active" | "pending" | "discovered"
  discovered?: boolean
}) {
  const statusConfig = {
    completed: {
      bg: `linear-gradient(135deg, ${colors.green} 0%, #3CB371 100%)`,
      border: "none",
      textColor: "#fff",
      glow: `0 0 20px rgba(80, 200, 120, 0.30)`,
    },
    active: {
      bg: `linear-gradient(135deg, ${colors.gold} 0%, ${colors.orange} 100%)`,
      border: "none",
      textColor: "#1a150d",
      glow: `0 0 25px rgba(255, 208, 74, 0.40)`,
    },
    pending: {
      bg: "rgba(255, 208, 74, 0.08)",
      border: `2px solid ${colors.cardBorder}`,
      textColor: colors.textMuted,
      glow: "none",
    },
    discovered: {
      bg: "rgba(167, 139, 250, 0.15)",
      border: `2px dashed ${colors.purple}60`,
      textColor: colors.purple,
      glow: `0 0 15px rgba(167, 139, 250, 0.20)`,
    },
  }

  const config = statusConfig[status]

  return (
    <div
      style={{
        position: "absolute",
        left: `${x - 50}px`,
        top: `${y - 28}px`,
        width: "100px",
        height: "56px",
        borderRadius: "12px",
        background: config.bg,
        border: config.border,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: config.glow,
      }}
    >
      {discovered && (
        <div
          style={{
            position: "absolute",
            top: "-8px",
            right: "-8px",
            width: "20px",
            height: "20px",
            borderRadius: "10px",
            background: colors.purple,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
              fill="#fff"
            />
          </svg>
        </div>
      )}
      <span
        style={{
          fontSize: "11px",
          fontFamily: "Montserrat",
          fontWeight: 400,
          color: config.textColor,
          textAlign: "center",
        }}
      >
        {label}
      </span>
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
              "radial-gradient(ellipse 60% 40% at 50% 55%, rgba(255, 208, 74, 0.06) 0%, transparent 60%), radial-gradient(ellipse 40% 30% at 60% 25%, rgba(167, 139, 250, 0.05) 0%, transparent 50%)",
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
              Workflows That Build Themselves
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
              Tasks discover dependencies and adapt in real-time
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

        {/* Graph Visualization */}
        <div
          style={{
            display: "flex",
            flex: 1,
            position: "relative",
            zIndex: 1,
          }}
        >
          {/* Graph container */}
          <div
            style={{
              position: "relative",
              width: "960px",
              height: "520px",
              display: "flex",
            }}
          >
            {/* SVG for edges */}
            <svg
              width="960"
              height="520"
              viewBox="0 0 960 520"
              fill="none"
              style={{ position: "absolute", top: 0, left: 0 }}
            >
              {/* Main flow edges */}
              {graph.edges.map((edge, i) => {
                const from = graph.nodes.find((n) => n.id === edge.from)!
                const to = graph.nodes.find((n) => n.id === edge.to)!
                const isDiscovered = edge.discovered

                // Calculate control points for curved lines
                const midX = (from.x + to.x) / 2
                const midY = (from.y + to.y) / 2

                // Determine if line should curve up or down
                const curveOffset = to.y !== from.y ? 0 : 20

                return (
                  <path
                    key={i}
                    d={`M ${from.x + 50} ${from.y} Q ${midX} ${midY - curveOffset} ${to.x - 50} ${to.y}`}
                    stroke={isDiscovered ? colors.purple : colors.goldSoft}
                    strokeWidth={isDiscovered ? "2" : "2.5"}
                    strokeDasharray={isDiscovered ? "6 4" : "none"}
                    opacity={isDiscovered ? 0.6 : 0.7}
                    fill="none"
                  />
                )
              })}

              {/* Arrow markers */}
              <defs>
                <marker
                  id="arrowGold"
                  markerWidth="10"
                  markerHeight="7"
                  refX="9"
                  refY="3.5"
                  orient="auto"
                >
                  <polygon points="0 0, 10 3.5, 0 7" fill={colors.goldSoft} />
                </marker>
                <marker
                  id="arrowPurple"
                  markerWidth="10"
                  markerHeight="7"
                  refX="9"
                  refY="3.5"
                  orient="auto"
                >
                  <polygon points="0 0, 10 3.5, 0 7" fill={colors.purple} />
                </marker>
              </defs>
            </svg>

            {/* Nodes */}
            {graph.nodes.map((node) => (
              <GraphNode
                key={node.id}
                x={node.x}
                y={node.y}
                label={node.label}
                status={node.status}
                discovered={node.discovered}
              />
            ))}

            {/* Discovery callout */}
            <div
              style={{
                position: "absolute",
                left: "580px",
                top: "80px",
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                padding: "12px 16px",
                background: "rgba(167, 139, 250, 0.10)",
                borderRadius: "10px",
                border: `1px dashed ${colors.purple}50`,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
                    fill={colors.purple}
                  />
                </svg>
                <span
                  style={{
                    fontSize: "11px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.purple,
                  }}
                >
                  Discovered Branch
                </span>
              </div>
              <span
                style={{
                  fontSize: "10px",
                  fontFamily: "Montserrat",
                  fontWeight: 300,
                  color: colors.textMuted,
                }}
              >
                Agent found optimization opportunity
              </span>
            </div>
          </div>

          {/* Legend */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              width: "180px",
              background: "rgba(0, 0, 0, 0.30)",
              borderRadius: "14px",
              padding: "16px",
              border: `1px solid ${colors.cardBorder}`,
              marginLeft: "auto",
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
              Legend
            </div>

            {[
              { color: colors.green, label: "Completed" },
              { color: colors.gold, label: "In Progress" },
              { color: colors.textDim, label: "Blocked" },
              { color: colors.purple, label: "Discovered" },
            ].map((item, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  marginBottom: "10px",
                }}
              >
                <div
                  style={{
                    width: "12px",
                    height: "12px",
                    borderRadius: "6px",
                    background: item.color,
                  }}
                />
                <span
                  style={{
                    fontSize: "12px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textMuted,
                  }}
                >
                  {item.label}
                </span>
              </div>
            ))}

            {/* Stats */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                marginTop: "auto",
                paddingTop: "14px",
                borderTop: `1px solid ${colors.cardBorder}`,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span
                  style={{ fontSize: "11px", fontFamily: "Montserrat", fontWeight: 300, color: colors.textDim }}
                >
                  Tasks
                </span>
                <span
                  style={{ fontSize: "11px", fontFamily: "Montserrat", fontWeight: 400, color: colors.gold }}
                >
                  10
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span
                  style={{ fontSize: "11px", fontFamily: "Montserrat", fontWeight: 300, color: colors.textDim }}
                >
                  Discovered
                </span>
                <span
                  style={{ fontSize: "11px", fontFamily: "Montserrat", fontWeight: 400, color: colors.purple }}
                >
                  +2
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span
                  style={{ fontSize: "11px", fontFamily: "Montserrat", fontWeight: 300, color: colors.textDim }}
                >
                  Progress
                </span>
                <span
                  style={{ fontSize: "11px", fontFamily: "Montserrat", fontWeight: 400, color: colors.green }}
                >
                  40%
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
            marginTop: "20px",
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
              Structure emerges from the problem, not predefined plans
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
