import { ImageResponse } from "next/og"

export const runtime = "edge"

export async function GET() {
  const montserratRegular = fetch(
    new URL("../../../public/fonts/Montserrat-Regular.ttf", import.meta.url)
  ).then((res) => res.arrayBuffer())

  const montserratLight = fetch(
    new URL("../../../public/fonts/Montserrat-Light.ttf", import.meta.url)
  ).then((res) => res.arrayBuffer())

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "row",
          background: "linear-gradient(145deg, #FFF9F0 0%, #FFF5E6 50%, #FFEDD5 100%)",
          position: "relative",
          padding: "50px 60px",
        }}
      >
        {/* Radial pattern from center */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              "radial-gradient(ellipse 60% 60% at 65% 50%, rgba(180,120,30,0.05) 0%, transparent 60%)",
            display: "flex",
          }}
        />

        {/* Left side - Text content */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            width: "380px",
            paddingRight: "30px",
            zIndex: 1,
          }}
        >
          {/* Logo + domain pill */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              marginBottom: "32px",
            }}
          >
            <svg
              width="44"
              height="44"
              viewBox="0 0 512 512"
              fill="none"
              style={{ marginRight: "14px" }}
            >
              <defs>
                <linearGradient
                  id="goldStrokeLight"
                  x1="120"
                  y1="96"
                  x2="392"
                  y2="416"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop offset="0" stopColor="#D4920A" />
                  <stop offset="0.35" stopColor="#B8860B" />
                  <stop offset="1" stopColor="#996515" />
                </linearGradient>
              </defs>
              <g stroke="url(#goldStrokeLight)" strokeLinecap="round" strokeLinejoin="round">
                <g strokeWidth="20">
                  <circle cx="256" cy="256" r="112" fill="none" />
                  <circle cx="368" cy="256" r="112" fill="none" />
                  <circle cx="312" cy="352.99" r="112" fill="none" />
                  <circle cx="200" cy="352.99" r="112" fill="none" />
                  <circle cx="144" cy="256" r="112" fill="none" />
                  <circle cx="200" cy="159.01" r="112" fill="none" />
                  <circle cx="312" cy="159.01" r="112" fill="none" />
                </g>
                <g strokeWidth="14">
                  <circle cx="256" cy="256" r="210" fill="none" opacity="0.55" />
                </g>
              </g>
            </svg>
            <div
              style={{
                display: "flex",
                background: "rgba(180,120,30,0.1)",
                borderRadius: "20px",
                padding: "6px 16px",
                fontSize: "16px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "rgba(120,80,20,0.85)",
                border: "1px solid rgba(180,120,30,0.2)",
              }}
            >
              omoios.dev
            </div>
          </div>

          {/* Main headline */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "2px",
            }}
          >
            <span
              style={{
                fontSize: "48px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "#3D2914",
                lineHeight: 1.1,
              }}
            >
              Intelligent
            </span>
            <span
              style={{
                fontSize: "48px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                background: "linear-gradient(135deg, #D4920A 0%, #B8860B 35%, #996515 100%)",
                backgroundClip: "text",
                color: "transparent",
                lineHeight: 1.1,
              }}
            >
              orchestration.
            </span>
          </div>

          {/* Subheadline */}
          <div
            style={{
              display: "flex",
              fontSize: "20px",
              fontFamily: "Montserrat",
              fontWeight: 300,
              color: "rgba(80,55,25,0.6)",
              marginTop: "24px",
              lineHeight: 1.5,
            }}
          >
            The right agent for every task.
          </div>
        </div>

        {/* Right side - Orchestration Visualization */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flex: 1,
            position: "relative",
          }}
        >
          {/* Main container */}
          <div
            style={{
              display: "flex",
              position: "relative",
              width: "600px",
              height: "500px",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {/* Connection lines from center to agents */}
            <svg
              width="600"
              height="500"
              viewBox="0 0 600 500"
              fill="none"
              style={{ position: "absolute" }}
            >
              <defs>
                <linearGradient id="lineGradL1" x1="50%" y1="50%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#B8860B" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#D4920A" stopOpacity="0.3" />
                </linearGradient>
                <linearGradient id="lineGradL2" x1="50%" y1="50%" x2="100%" y2="50%">
                  <stop offset="0%" stopColor="#B8860B" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#A67C00" stopOpacity="0.3" />
                </linearGradient>
                <linearGradient id="lineGradL3" x1="50%" y1="50%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#B8860B" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#996515" stopOpacity="0.3" />
                </linearGradient>
                <linearGradient id="lineGradL4" x1="50%" y1="50%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#B8860B" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#8B6914" stopOpacity="0.3" />
                </linearGradient>
              </defs>

              {/* Lines to agents with decision diamonds */}
              <path d="M 260 250 L 380 250 L 480 100" stroke="url(#lineGradL1)" strokeWidth="2" fill="none" />
              <polygon points="380,250 390,240 380,230 370,240" fill="#B8860B" opacity="0.6" />

              <path d="M 260 250 L 380 250 L 520 250" stroke="url(#lineGradL2)" strokeWidth="2" fill="none" />

              <path d="M 260 250 L 380 250 L 480 400" stroke="url(#lineGradL3)" strokeWidth="2" fill="none" />
              <polygon points="380,250 390,260 380,270 370,260" fill="#A67C00" opacity="0.6" />

              <path d="M 260 250 L 260 340 L 260 430" stroke="url(#lineGradL4)" strokeWidth="2" fill="none" />
              <polygon points="260,340 270,350 260,360 250,350" fill="#996515" opacity="0.6" />

              {/* Incoming task lines */}
              <path d="M 50 100 L 180 250" stroke="rgba(180,120,30,0.3)" strokeWidth="1.5" strokeDasharray="4 4" fill="none" />
              <path d="M 50 250 L 180 250" stroke="rgba(180,120,30,0.3)" strokeWidth="1.5" strokeDasharray="4 4" fill="none" />
              <path d="M 50 400 L 180 250" stroke="rgba(180,120,30,0.3)" strokeWidth="1.5" strokeDasharray="4 4" fill="none" />
            </svg>

            {/* Incoming task cards */}
            <div
              style={{
                position: "absolute",
                left: "10px",
                top: "70px",
                display: "flex",
              }}
            >
              <div
                style={{
                  width: "50px",
                  height: "35px",
                  borderRadius: "6px",
                  background: "rgba(180,120,30,0.1)",
                  border: "1px solid rgba(180,120,30,0.25)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="3" width="18" height="18" rx="2" stroke="#B8860B" strokeWidth="1.5" fill="none" opacity="0.7" />
                </svg>
              </div>
            </div>

            <div
              style={{
                position: "absolute",
                left: "10px",
                top: "230px",
                display: "flex",
              }}
            >
              <div
                style={{
                  width: "50px",
                  height: "35px",
                  borderRadius: "6px",
                  background: "rgba(180,120,30,0.1)",
                  border: "1px solid rgba(180,120,30,0.25)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="3" width="18" height="18" rx="2" stroke="#B8860B" strokeWidth="1.5" fill="none" opacity="0.7" />
                </svg>
              </div>
            </div>

            <div
              style={{
                position: "absolute",
                left: "10px",
                top: "380px",
                display: "flex",
              }}
            >
              <div
                style={{
                  width: "50px",
                  height: "35px",
                  borderRadius: "6px",
                  background: "rgba(180,120,30,0.1)",
                  border: "1px solid rgba(180,120,30,0.25)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="3" width="18" height="18" rx="2" stroke="#B8860B" strokeWidth="1.5" fill="none" opacity="0.7" />
                </svg>
              </div>
            </div>

            {/* Central Orchestrator */}
            <div
              style={{
                position: "absolute",
                left: "180px",
                top: "175px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <div
                style={{
                  width: "120px",
                  height: "120px",
                  borderRadius: "60px",
                  background: "linear-gradient(135deg, #E8A917 0%, #D4920A 50%, #B8860B 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 40px rgba(212,146,10,0.45)",
                }}
              >
                {/* Brain/Network icon */}
                <svg width="50" height="50" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2a4 4 0 0 1 4 4v1a3 3 0 0 1 3 3v1a3 3 0 0 1-1 2.24V16a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4v-2.76A3 3 0 0 1 5 11v-1a3 3 0 0 1 3-3V6a4 4 0 0 1 4-4z" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  <circle cx="9" cy="10" r="1" fill="#FFF9F0" />
                  <circle cx="15" cy="10" r="1" fill="#FFF9F0" />
                  <path d="M9 14h6" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "10px",
                  fontSize: "14px",
                  fontFamily: "Montserrat",
                  fontWeight: 400,
                  color: "#B8860B",
                }}
              >
                Orchestrator
              </span>
            </div>

            {/* Code Agent (top-right) */}
            <div
              style={{
                position: "absolute",
                right: "60px",
                top: "50px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <div
                style={{
                  width: "70px",
                  height: "70px",
                  borderRadius: "35px",
                  background: "linear-gradient(135deg, #D4920A 0%, #B8860B 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 25px rgba(212,146,10,0.4)",
                }}
              >
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                  <polyline points="16,18 22,12 16,6" stroke="#FFF9F0" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  <polyline points="8,6 2,12 8,18" stroke="#FFF9F0" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "6px",
                  fontSize: "12px",
                  fontFamily: "Montserrat",
                  color: "rgba(80,55,25,0.8)",
                }}
              >
                Code Agent
              </span>
            </div>

            {/* Test Agent (right) */}
            <div
              style={{
                position: "absolute",
                right: "20px",
                top: "200px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <div
                style={{
                  width: "70px",
                  height: "70px",
                  borderRadius: "35px",
                  background: "linear-gradient(135deg, #B8860B 0%, #A67C00 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 25px rgba(184,134,11,0.4)",
                }}
              >
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                  <path d="M9 11l3 3L22 4" stroke="#FFF9F0" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "6px",
                  fontSize: "12px",
                  fontFamily: "Montserrat",
                  color: "rgba(80,55,25,0.8)",
                }}
              >
                Test Agent
              </span>
            </div>

            {/* Review Agent (bottom-right) */}
            <div
              style={{
                position: "absolute",
                right: "60px",
                top: "350px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <div
                style={{
                  width: "70px",
                  height: "70px",
                  borderRadius: "35px",
                  background: "linear-gradient(135deg, #A67C00 0%, #996515 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 25px rgba(166,124,0,0.4)",
                }}
              >
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  <circle cx="12" cy="12" r="3" stroke="#FFF9F0" strokeWidth="2" fill="none" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "6px",
                  fontSize: "12px",
                  fontFamily: "Montserrat",
                  color: "rgba(80,55,25,0.8)",
                }}
              >
                Review Agent
              </span>
            </div>

            {/* Deploy Agent (bottom) */}
            <div
              style={{
                position: "absolute",
                left: "200px",
                bottom: "20px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <div
                style={{
                  width: "70px",
                  height: "70px",
                  borderRadius: "35px",
                  background: "linear-gradient(135deg, #996515 0%, #8B6914 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 25px rgba(153,101,21,0.4)",
                }}
              >
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
                  <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  <path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "6px",
                  fontSize: "12px",
                  fontFamily: "Montserrat",
                  color: "rgba(80,55,25,0.8)",
                }}
              >
                Deploy Agent
              </span>
            </div>

            {/* Priority/Score indicators */}
            <div
              style={{
                position: "absolute",
                right: "140px",
                top: "130px",
                display: "flex",
                alignItems: "center",
                background: "rgba(180,120,30,0.08)",
                borderRadius: "8px",
                padding: "3px 8px",
              }}
            >
              <span style={{ fontSize: "10px", fontFamily: "Montserrat", color: "rgba(120,80,20,0.8)" }}>P1</span>
            </div>

            <div
              style={{
                position: "absolute",
                right: "90px",
                top: "260px",
                display: "flex",
                alignItems: "center",
                background: "rgba(180,120,30,0.08)",
                borderRadius: "8px",
                padding: "3px 8px",
              }}
            >
              <span style={{ fontSize: "10px", fontFamily: "Montserrat", color: "rgba(120,80,20,0.8)" }}>P2</span>
            </div>
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
