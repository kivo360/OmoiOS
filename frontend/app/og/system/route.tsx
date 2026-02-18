import { ImageResponse } from "next/og";

export const runtime = "edge";

const diagram = {
  width: 1080,
  height: 420,
  // Node centers + sizes (kept on integer pixels to avoid blurry transforms)
  nodes: {
    spec: { x: 96, y: 210, w: 84, h: 84 },
    orchestrator: { x: 240, y: 210, w: 120, h: 120 },
    code: { x: 452, y: 100, w: 74, h: 74 },
    test: { x: 452, y: 210, w: 74, h: 74 },
    review: { x: 452, y: 320, w: 74, h: 74 },
    gate: { x: 660, y: 210, w: 70, h: 70 },
    integrate: { x: 840, y: 210, w: 80, h: 80 },
    complete: { x: 998, y: 210, w: 92, h: 92 },
  },
};

function topLeft({
  x,
  y,
  w,
  h,
}: {
  x: number;
  y: number;
  w: number;
  h: number;
}) {
  return {
    left: `${x - w / 2}px`,
    top: `${y - h / 2}px`,
    width: `${w}px`,
    height: `${h}px`,
  };
}

export async function GET() {
  const montserratRegular = fetch(
    new URL("../../../public/fonts/Montserrat-Regular.ttf", import.meta.url),
  ).then((res) => res.arrayBuffer());

  const montserratLight = fetch(
    new URL("../../../public/fonts/Montserrat-Light.ttf", import.meta.url),
  ).then((res) => res.arrayBuffer());

  const n = diagram.nodes;

  const gold = "#FFD04A";
  const goldSoft = "rgba(255, 208, 74, 0.70)";
  const ink = "#1a150d";
  const text = "rgba(255, 248, 235, 0.92)";
  const muted = "rgba(255, 236, 205, 0.70)";

  return new ImageResponse(
    <div
      style={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        background:
          "linear-gradient(145deg, #2d2618 0%, #1a150d 52%, #0f0c08 100%)",
        position: "relative",
        padding: "46px 64px 42px 64px",
      }}
    >
      {/* Subtle texture + vignette */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage:
            "radial-gradient(rgba(255, 208, 74, 0.04) 1px, transparent 1px)",
          backgroundSize: "34px 34px",
          opacity: 1,
          display: "flex",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background:
            "radial-gradient(ellipse 85% 70% at 52% 60%, rgba(180, 125, 70, 0.12) 0%, transparent 60%), radial-gradient(ellipse 70% 60% at 30% 35%, rgba(255, 208, 74, 0.12) 0%, transparent 58%), radial-gradient(ellipse 60% 55% at 78% 70%, rgba(80, 200, 120, 0.10) 0%, transparent 55%)",
          display: "flex",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background:
            "radial-gradient(ellipse 120% 90% at 50% 50%, transparent 52%, rgba(0,0,0,0.48) 100%)",
          display: "flex",
        }}
      />

      {/* Top header bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "22px",
          zIndex: 1,
        }}
      >
        {/* Logo + brand */}
        <div style={{ display: "flex", alignItems: "center" }}>
          <svg
            width="40"
            height="40"
            viewBox="0 0 512 512"
            fill="none"
            style={{ marginRight: "12px" }}
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
              fontSize: "26px",
              fontFamily: "Montserrat",
              fontWeight: 400,
              color: text,
              letterSpacing: "0.2px",
            }}
          >
            OmoiOS
          </span>
        </div>

        {/* Tagline */}
        <div
          style={{
            display: "flex",
            background: "rgba(255, 208, 74, 0.10)",
            borderRadius: "999px",
            padding: "8px 16px",
            fontSize: "14px",
            fontFamily: "Montserrat",
            fontWeight: 300,
            color: "rgba(255, 236, 205, 0.85)",
            border: "1px solid rgba(255, 208, 74, 0.18)",
          }}
        >
          Autonomous Development
        </div>
      </div>

      {/* Main visualization area */}
      <div
        style={{
          display: "flex",
          flex: 1,
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1,
        }}
      >
        <div
          style={{
            position: "relative",
            width: `${diagram.width}px`,
            height: `${diagram.height}px`,
            display: "flex",
          }}
        >
          {/* Flow lines */}
          <svg
            width={diagram.width}
            height={diagram.height}
            viewBox={`0 0 ${diagram.width} ${diagram.height}`}
            fill="none"
            style={{ position: "absolute", top: 0, left: 0 }}
          >
            <defs>
              <linearGradient id="flowGrad" x1="0%" y1="50%" x2="100%" y2="50%">
                <stop offset="0%" stopColor="#FFD04A" stopOpacity="0.85" />
                <stop offset="72%" stopColor="#FFD04A" stopOpacity="0.85" />
                <stop offset="100%" stopColor="#50C878" stopOpacity="0.95" />
              </linearGradient>
            </defs>

            {/* Underlay (soft) */}
            <g strokeLinecap="round" strokeLinejoin="round">
              <path
                d={`M ${n.spec.x + n.spec.w / 2} ${n.spec.y} L ${n.orchestrator.x - n.orchestrator.w / 2} ${n.orchestrator.y}`}
                stroke={gold}
                strokeWidth="8"
                opacity="0.10"
              />
              <path
                d={`M ${n.orchestrator.x + n.orchestrator.w / 2 - 6} ${n.orchestrator.y} C ${n.orchestrator.x + 120} ${n.orchestrator.y}, ${n.code.x - 120} ${n.code.y}, ${n.code.x - n.code.w / 2} ${n.code.y}`}
                stroke={gold}
                strokeWidth="8"
                opacity="0.10"
              />
              <path
                d={`M ${n.orchestrator.x + n.orchestrator.w / 2 - 6} ${n.orchestrator.y} L ${n.test.x - n.test.w / 2} ${n.test.y}`}
                stroke={gold}
                strokeWidth="8"
                opacity="0.10"
              />
              <path
                d={`M ${n.orchestrator.x + n.orchestrator.w / 2 - 6} ${n.orchestrator.y} C ${n.orchestrator.x + 120} ${n.orchestrator.y}, ${n.review.x - 120} ${n.review.y}, ${n.review.x - n.review.w / 2} ${n.review.y}`}
                stroke={gold}
                strokeWidth="8"
                opacity="0.10"
              />

              <path
                d={`M ${n.code.x + n.code.w / 2} ${n.code.y} C ${n.code.x + 120} ${n.code.y}, ${n.gate.x - 160} ${n.gate.y - 40}, ${n.gate.x - n.gate.w / 2} ${n.gate.y}`}
                stroke={gold}
                strokeWidth="8"
                opacity="0.10"
              />
              <path
                d={`M ${n.test.x + n.test.w / 2} ${n.test.y} L ${n.gate.x - n.gate.w / 2} ${n.gate.y}`}
                stroke={gold}
                strokeWidth="8"
                opacity="0.10"
              />
              <path
                d={`M ${n.review.x + n.review.w / 2} ${n.review.y} C ${n.review.x + 120} ${n.review.y}, ${n.gate.x - 160} ${n.gate.y + 40}, ${n.gate.x - n.gate.w / 2} ${n.gate.y}`}
                stroke={gold}
                strokeWidth="8"
                opacity="0.10"
              />

              <path
                d={`M ${n.gate.x + n.gate.w / 2} ${n.gate.y} L ${n.integrate.x - n.integrate.w / 2} ${n.integrate.y}`}
                stroke={gold}
                strokeWidth="8"
                opacity="0.10"
              />
              <path
                d={`M ${n.integrate.x + n.integrate.w / 2} ${n.integrate.y} L ${n.complete.x - n.complete.w / 2} ${n.complete.y}`}
                stroke="url(#flowGrad)"
                strokeWidth="8"
                opacity="0.14"
              />
            </g>

            {/* Main strokes */}
            <g strokeLinecap="round" strokeLinejoin="round">
              <path
                d={`M ${n.spec.x + n.spec.w / 2} ${n.spec.y} L ${n.orchestrator.x - n.orchestrator.w / 2} ${n.orchestrator.y}`}
                stroke={goldSoft}
                strokeWidth="3"
              />

              <path
                d={`M ${n.orchestrator.x + n.orchestrator.w / 2 - 6} ${n.orchestrator.y} C ${n.orchestrator.x + 120} ${n.orchestrator.y}, ${n.code.x - 120} ${n.code.y}, ${n.code.x - n.code.w / 2} ${n.code.y}`}
                stroke={goldSoft}
                strokeWidth="3"
              />
              <path
                d={`M ${n.orchestrator.x + n.orchestrator.w / 2 - 6} ${n.orchestrator.y} L ${n.test.x - n.test.w / 2} ${n.test.y}`}
                stroke={goldSoft}
                strokeWidth="3"
              />
              <path
                d={`M ${n.orchestrator.x + n.orchestrator.w / 2 - 6} ${n.orchestrator.y} C ${n.orchestrator.x + 120} ${n.orchestrator.y}, ${n.review.x - 120} ${n.review.y}, ${n.review.x - n.review.w / 2} ${n.review.y}`}
                stroke={goldSoft}
                strokeWidth="3"
              />

              <path
                d={`M ${n.code.x + n.code.w / 2} ${n.code.y} C ${n.code.x + 120} ${n.code.y}, ${n.gate.x - 160} ${n.gate.y - 40}, ${n.gate.x - n.gate.w / 2} ${n.gate.y}`}
                stroke={goldSoft}
                strokeWidth="3"
              />
              <path
                d={`M ${n.test.x + n.test.w / 2} ${n.test.y} L ${n.gate.x - n.gate.w / 2} ${n.gate.y}`}
                stroke={goldSoft}
                strokeWidth="3"
              />
              <path
                d={`M ${n.review.x + n.review.w / 2} ${n.review.y} C ${n.review.x + 120} ${n.review.y}, ${n.gate.x - 160} ${n.gate.y + 40}, ${n.gate.x - n.gate.w / 2} ${n.gate.y}`}
                stroke={goldSoft}
                strokeWidth="3"
              />

              <path
                d={`M ${n.gate.x + n.gate.w / 2} ${n.gate.y} L ${n.integrate.x - n.integrate.w / 2} ${n.integrate.y}`}
                stroke={goldSoft}
                strokeWidth="3"
              />
              <path
                d={`M ${n.integrate.x + n.integrate.w / 2} ${n.integrate.y} L ${n.complete.x - n.complete.w / 2} ${n.complete.y}`}
                stroke="url(#flowGrad)"
                strokeWidth="3"
                opacity="0.95"
              />
            </g>
          </svg>

          {/* Spec */}
          <div
            style={{
              position: "absolute",
              ...topLeft(n.spec),
              borderRadius: "18px",
              background:
                "linear-gradient(135deg, rgba(255, 208, 74, 0.16) 0%, rgba(255, 138, 42, 0.08) 100%)",
              border: "2px solid rgba(255, 208, 74, 0.42)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 14px 34px rgba(0,0,0,0.55), 0 0 18px rgba(255, 208, 74, 0.12)",
            }}
          >
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
              <path
                d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
                stroke={gold}
                strokeWidth="2"
                fill="none"
              />
              <polyline
                points="14,2 14,8 20,8"
                stroke={gold}
                strokeWidth="2"
                fill="none"
              />
              <line
                x1="16"
                y1="13"
                x2="8"
                y2="13"
                stroke={gold}
                strokeWidth="2"
              />
              <line
                x1="16"
                y1="17"
                x2="8"
                y2="17"
                stroke={gold}
                strokeWidth="2"
              />
            </svg>
          </div>
          <div
            style={{
              position: "absolute",
              left: `${n.spec.x - 40}px`,
              top: `${n.spec.y + n.spec.h / 2 + 10}px`,
              width: "80px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                fontSize: "13px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: muted,
              }}
            >
              Spec
            </span>
          </div>

          {/* Orchestrator */}
          <div
            style={{
              position: "absolute",
              ...topLeft(n.orchestrator),
              borderRadius: `${n.orchestrator.w / 2}px`,
              background:
                "linear-gradient(135deg, #FFE78A 0%, #FFD04A 52%, #FF8A2A 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 18px 52px rgba(0,0,0,0.55), 0 0 26px rgba(255, 208, 74, 0.30)",
            }}
          >
            <svg width="50" height="50" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2a4 4 0 0 1 4 4v1a3 3 0 0 1 3 3v1a3 3 0 0 1-1 2.24V16a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4v-2.76A3 3 0 0 1 5 11v-1a3 3 0 0 1 3-3V6a4 4 0 0 1 4-4z"
                stroke={ink}
                strokeWidth="2"
                fill="none"
              />
              <circle cx="9" cy="10" r="1" fill={ink} />
              <circle cx="15" cy="10" r="1" fill={ink} />
              <path
                d="M9 14h6"
                stroke={ink}
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <div
            style={{
              position: "absolute",
              left: `${n.orchestrator.x - 80}px`,
              top: `${n.orchestrator.y + n.orchestrator.h / 2 + 10}px`,
              width: "160px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                fontSize: "13px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: gold,
              }}
            >
              Orchestrator
            </span>
          </div>

          {/* Parallel Agents label */}
          <div
            style={{
              position: "absolute",
              left: `${n.code.x - 120}px`,
              top: "16px",
              width: "240px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                fontSize: "11px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "rgba(255, 208, 74, 0.70)",
                textTransform: "uppercase",
                letterSpacing: "2px",
              }}
            >
              Parallel Agents
            </span>
          </div>

          {/* Code */}
          <div
            style={{
              position: "absolute",
              ...topLeft(n.code),
              borderRadius: `${n.code.w / 2}px`,
              background: "linear-gradient(135deg, #FFE78A 0%, #FFD04A 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 14px 34px rgba(0,0,0,0.55), 0 0 18px rgba(255, 231, 138, 0.18)",
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <polyline
                points="16,18 22,12 16,6"
                stroke={ink}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <polyline
                points="8,6 2,12 8,18"
                stroke={ink}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div
            style={{
              position: "absolute",
              left: `${n.code.x - 40}px`,
              top: `${n.code.y + n.code.h / 2 + 8}px`,
              width: "80px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                fontSize: "11px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: muted,
              }}
            >
              Code
            </span>
          </div>

          {/* Test */}
          <div
            style={{
              position: "absolute",
              ...topLeft(n.test),
              borderRadius: `${n.test.w / 2}px`,
              background: "linear-gradient(135deg, #FFD04A 0%, #F0A500 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 14px 34px rgba(0,0,0,0.55), 0 0 18px rgba(240, 165, 0, 0.16)",
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path
                d="M9 11l3 3L22 4"
                stroke={ink}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"
                stroke={ink}
                strokeWidth="2"
                fill="none"
              />
            </svg>
          </div>
          <div
            style={{
              position: "absolute",
              left: `${n.test.x - 40}px`,
              top: `${n.test.y + n.test.h / 2 + 8}px`,
              width: "80px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                fontSize: "11px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: muted,
              }}
            >
              Test
            </span>
          </div>

          {/* Review */}
          <div
            style={{
              position: "absolute",
              ...topLeft(n.review),
              borderRadius: `${n.review.w / 2}px`,
              background: "linear-gradient(135deg, #F0A500 0%, #E8A317 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 14px 34px rgba(0,0,0,0.55), 0 0 18px rgba(232, 163, 23, 0.14)",
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path
                d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
                stroke={ink}
                strokeWidth="2"
                fill="none"
              />
              <circle
                cx="12"
                cy="12"
                r="3"
                stroke={ink}
                strokeWidth="2"
                fill="none"
              />
            </svg>
          </div>
          <div
            style={{
              position: "absolute",
              left: `${n.review.x - 40}px`,
              top: `${n.review.y + n.review.h / 2 + 8}px`,
              width: "80px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                fontSize: "11px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: muted,
              }}
            >
              Review
            </span>
          </div>

          {/* Gate */}
          <div
            style={{
              position: "absolute",
              ...topLeft(n.gate),
              transform: "rotate(45deg)",
              background:
                "linear-gradient(135deg, rgba(255, 208, 74, 0.20) 0%, rgba(255, 138, 42, 0.12) 100%)",
              border: "3px solid rgba(255, 208, 74, 0.42)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 14px 34px rgba(0,0,0,0.55), 0 0 18px rgba(255, 208, 74, 0.14)",
            }}
          >
            <div style={{ transform: "rotate(-45deg)", display: "flex" }}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 2L2 7l10 5 10-5-10-5z"
                  stroke={gold}
                  strokeWidth="2"
                  fill="none"
                />
                <path
                  d="M2 17l10 5 10-5"
                  stroke={gold}
                  strokeWidth="2"
                  fill="none"
                />
                <path
                  d="M2 12l10 5 10-5"
                  stroke={gold}
                  strokeWidth="2"
                  fill="none"
                />
              </svg>
            </div>
          </div>
          <div
            style={{
              position: "absolute",
              left: `${n.gate.x - 40}px`,
              top: `${n.gate.y + n.gate.h / 2 + 14}px`,
              width: "80px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                fontSize: "11px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: "rgba(255, 208, 74, 0.78)",
              }}
            >
              Gate
            </span>
          </div>

          {/* Integrate */}
          <div
            style={{
              position: "absolute",
              ...topLeft(n.integrate),
              borderRadius: `${n.integrate.w / 2}px`,
              background: "linear-gradient(135deg, #E8A317 0%, #D4920A 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 14px 34px rgba(0,0,0,0.55), 0 0 18px rgba(232, 163, 23, 0.16)",
            }}
          >
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none">
              <path
                d="M18 8L22 12L18 16"
                stroke={ink}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M2 12H22"
                stroke={ink}
                strokeWidth="2.5"
                strokeLinecap="round"
              />
              <path
                d="M8 6L2 12L8 18"
                stroke={ink}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div
            style={{
              position: "absolute",
              left: `${n.integrate.x - 50}px`,
              top: `${n.integrate.y + n.integrate.h / 2 + 10}px`,
              width: "100px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                fontSize: "11px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: muted,
              }}
            >
              Integrate
            </span>
          </div>

          {/* Complete */}
          <div
            style={{
              position: "absolute",
              ...topLeft(n.complete),
              borderRadius: `${n.complete.w / 2}px`,
              background: "linear-gradient(135deg, #50C878 0%, #3CB371 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 16px 44px rgba(0,0,0,0.55), 0 0 18px rgba(80, 200, 120, 0.22)",
            }}
          >
            <svg width="38" height="38" viewBox="0 0 24 24" fill="none">
              <path
                d="M20 6L9 17l-5-5"
                stroke="#ffffff"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div
            style={{
              position: "absolute",
              left: `${n.complete.x - 55}px`,
              top: `${n.complete.y + n.complete.h / 2 + 10}px`,
              width: "110px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                fontSize: "13px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "rgba(80, 200, 120, 0.95)",
              }}
            >
              Complete
            </span>
          </div>
        </div>
      </div>

      {/* Bottom tagline */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          marginTop: "12px",
          zIndex: 1,
        }}
      >
        <span
          style={{
            fontSize: "18px",
            fontFamily: "Montserrat",
            fontWeight: 300,
            color: "rgba(255, 236, 205, 0.62)",
            letterSpacing: "0.2px",
          }}
        >
          Spec → Orchestrate → Execute → Iterate → Complete
        </span>
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
