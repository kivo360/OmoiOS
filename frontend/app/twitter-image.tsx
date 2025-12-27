import { ImageResponse } from "next/og"

export const runtime = "edge"

export const alt = "OmoiOS - AI Agent Orchestration Platform"
export const size = {
  width: 1200,
  height: 630,
}
export const contentType = "image/png"

export default async function Image() {
  // Load Montserrat font
  const montserratThin = fetch(
    new URL("../public/fonts/Montserrat-Thin.ttf", import.meta.url)
  ).then((res) => res.arrayBuffer())

  const montserratLight = fetch(
    new URL("../public/fonts/Montserrat-Light.ttf", import.meta.url)
  ).then((res) => res.arrayBuffer())

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0d0d0d 100%)",
          position: "relative",
        }}
      >
        {/* Subtle grid pattern overlay */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundImage:
              "linear-gradient(rgba(255,215,0,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,215,0,0.03) 1px, transparent 1px)",
            backgroundSize: "50px 50px",
          }}
        />

        {/* Glow effect behind logo */}
        <div
          style={{
            position: "absolute",
            width: "400px",
            height: "400px",
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(255,200,50,0.15) 0%, rgba(255,138,42,0.05) 50%, transparent 70%)",
            filter: "blur(40px)",
          }}
        />

        {/* Logo SVG - Flower of Life pattern */}
        <svg
          width="200"
          height="200"
          viewBox="0 0 512 512"
          fill="none"
          style={{ marginBottom: "30px" }}
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
            {/* Core mark */}
            <g strokeWidth="14">
              <circle cx="256" cy="256" r="112" fill="none" />
              <circle cx="368" cy="256" r="112" fill="none" />
              <circle cx="312" cy="352.99" r="112" fill="none" />
              <circle cx="200" cy="352.99" r="112" fill="none" />
              <circle cx="144" cy="256" r="112" fill="none" />
              <circle cx="200" cy="159.01" r="112" fill="none" />
              <circle cx="312" cy="159.01" r="112" fill="none" />
            </g>
            {/* Outer rings */}
            <g strokeWidth="10">
              <circle cx="256" cy="256" r="210" fill="none" opacity="0.55" />
              <circle cx="256" cy="256" r="236" fill="none" opacity="0.25" />
            </g>
          </g>
        </svg>

        {/* Logo text */}
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            marginBottom: "20px",
          }}
        >
          <span
            style={{
              fontSize: "72px",
              fontFamily: "Montserrat",
              fontWeight: 200,
              background: "linear-gradient(135deg, #FFE78A 0%, #FFD04A 35%, #FF8A2A 100%)",
              backgroundClip: "text",
              color: "transparent",
              letterSpacing: "-2px",
            }}
          >
            Omoi
          </span>
          <span
            style={{
              fontSize: "72px",
              fontFamily: "Montserrat",
              fontWeight: 300,
              background: "linear-gradient(135deg, #FFD04A 0%, #FF8A2A 100%)",
              backgroundClip: "text",
              color: "transparent",
              letterSpacing: "-2px",
            }}
          >
            OS
          </span>
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: "28px",
            fontFamily: "Montserrat",
            fontWeight: 300,
            color: "rgba(255, 255, 255, 0.7)",
            letterSpacing: "4px",
            textTransform: "uppercase",
          }}
        >
          AI Agent Orchestration
        </div>

        {/* Subtle bottom accent */}
        <div
          style={{
            position: "absolute",
            bottom: "40px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <div
            style={{
              width: "60px",
              height: "2px",
              background:
                "linear-gradient(90deg, transparent, rgba(255,200,50,0.5), transparent)",
            }}
          />
          <span
            style={{
              fontSize: "14px",
              fontFamily: "Montserrat",
              fontWeight: 300,
              color: "rgba(255, 255, 255, 0.4)",
              letterSpacing: "2px",
            }}
          >
            DEPLOY AGENTS THAT WORK WHILE YOU SLEEP
          </span>
          <div
            style={{
              width: "60px",
              height: "2px",
              background:
                "linear-gradient(90deg, transparent, rgba(255,200,50,0.5), transparent)",
            }}
          />
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [
        {
          name: "Montserrat",
          data: await montserratThin,
          style: "normal",
          weight: 200,
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
