import { ImageResponse } from "next/og";

export const runtime = "edge";

export async function GET() {
  const montserratRegular = fetch(
    new URL("../../../public/fonts/Montserrat-Regular.ttf", import.meta.url),
  ).then((res) => res.arrayBuffer());

  const montserratLight = fetch(
    new URL("../../../public/fonts/Montserrat-Light.ttf", import.meta.url),
  ).then((res) => res.arrayBuffer());

  return new ImageResponse(
    <div
      style={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        background:
          "linear-gradient(145deg, #FFF9F0 0%, #FFF5E6 50%, #FFEDD5 100%)",
        position: "relative",
        padding: "40px 60px",
      }}
    >
      {/* Background gradient */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background:
            "radial-gradient(ellipse 100% 50% at 50% 60%, rgba(180,120,30,0.04) 0%, transparent 60%)",
          display: "flex",
        }}
      />

      {/* Top header bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "20px",
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
            <g
              stroke="url(#goldStrokeLight)"
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
              fontSize: "24px",
              fontFamily: "Montserrat",
              fontWeight: 400,
              color: "#3D2914",
            }}
          >
            OmoiOS
          </span>
        </div>

        {/* Tagline */}
        <div
          style={{
            display: "flex",
            background: "rgba(180,120,30,0.08)",
            borderRadius: "16px",
            padding: "6px 16px",
            fontSize: "14px",
            fontFamily: "Montserrat",
            fontWeight: 300,
            color: "rgba(80,55,25,0.8)",
            border: "1px solid rgba(180,120,30,0.12)",
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
          position: "relative",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Flow visualization SVG */}
        <svg
          width="1080"
          height="420"
          viewBox="0 0 1080 420"
          fill="none"
          style={{ position: "absolute" }}
        >
          <defs>
            <linearGradient
              id="flowGradLight"
              x1="0%"
              y1="50%"
              x2="100%"
              y2="50%"
            >
              <stop offset="0%" stopColor="#B8860B" stopOpacity="0.6" />
              <stop offset="70%" stopColor="#B8860B" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#2E8B57" stopOpacity="0.6" />
            </linearGradient>
          </defs>

          {/* Spec to Orchestrator - bold line */}
          <line
            x1="120"
            y1="210"
            x2="200"
            y2="210"
            stroke="#B8860B"
            strokeWidth="3"
            opacity="0.6"
          />

          {/* Orchestrator to Agents (fan out) - smooth bezier curves */}
          <path
            d="M 300 210 C 360 210, 380 100, 440 100"
            stroke="#B8860B"
            strokeWidth="3"
            opacity="0.5"
            fill="none"
          />
          <path
            d="M 300 210 L 440 210"
            stroke="#B8860B"
            strokeWidth="3"
            opacity="0.5"
          />
          <path
            d="M 300 210 C 360 210, 380 320, 440 320"
            stroke="#B8860B"
            strokeWidth="3"
            opacity="0.5"
            fill="none"
          />

          {/* Agents to Gate (converge) - curves meet at gate diamond center */}
          <path
            d="M 520 100 C 580 100, 620 170, 680 210"
            stroke="#B8860B"
            strokeWidth="3"
            opacity="0.5"
            fill="none"
          />
          <path
            d="M 520 210 L 680 210"
            stroke="#B8860B"
            strokeWidth="3"
            opacity="0.5"
          />
          <path
            d="M 520 320 C 580 320, 620 250, 680 210"
            stroke="#B8860B"
            strokeWidth="3"
            opacity="0.5"
            fill="none"
          />

          {/* Gate to Integration - bold line */}
          <line
            x1="700"
            y1="210"
            x2="855"
            y2="210"
            stroke="#B8860B"
            strokeWidth="3"
            opacity="0.5"
          />

          {/* Integration to Done - green transition */}
          <line
            x1="935"
            y1="210"
            x2="1030"
            y2="210"
            stroke="#2E8B57"
            strokeWidth="3"
            opacity="0.6"
          />
        </svg>

        {/* Spec Input Node */}
        <div
          style={{
            position: "absolute",
            left: "35px",
            top: "50%",
            transform: "translateY(-50%)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <div
            style={{
              width: "80px",
              height: "80px",
              borderRadius: "16px",
              background:
                "linear-gradient(135deg, rgba(212,146,10,0.1) 0%, rgba(184,134,11,0.05) 100%)",
              border: "2px solid rgba(180,120,30,0.4)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 6px 20px rgba(120,80,30,0.15), 0 2px 6px rgba(120,80,30,0.1)",
            }}
          >
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
              <path
                d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
                stroke="#B8860B"
                strokeWidth="2"
                fill="none"
              />
              <polyline
                points="14,2 14,8 20,8"
                stroke="#B8860B"
                strokeWidth="2"
                fill="none"
              />
              <line
                x1="16"
                y1="13"
                x2="8"
                y2="13"
                stroke="#B8860B"
                strokeWidth="2"
              />
              <line
                x1="16"
                y1="17"
                x2="8"
                y2="17"
                stroke="#B8860B"
                strokeWidth="2"
              />
            </svg>
          </div>
          <span
            style={{
              marginTop: "10px",
              fontSize: "13px",
              fontFamily: "Montserrat",
              color: "rgba(80,55,25,0.8)",
            }}
          >
            Spec
          </span>
        </div>

        {/* Orchestrator */}
        <div
          style={{
            position: "absolute",
            left: "175px",
            top: "50%",
            transform: "translateY(-50%)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <div
            style={{
              width: "110px",
              height: "110px",
              borderRadius: "55px",
              background:
                "linear-gradient(135deg, #E8A917 0%, #D4920A 50%, #B8860B 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 8px 40px rgba(180,120,30,0.4), 0 4px 15px rgba(120,80,30,0.2)",
            }}
          >
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2a4 4 0 0 1 4 4v1a3 3 0 0 1 3 3v1a3 3 0 0 1-1 2.24V16a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4v-2.76A3 3 0 0 1 5 11v-1a3 3 0 0 1 3-3V6a4 4 0 0 1 4-4z"
                stroke="#FFF9F0"
                strokeWidth="2"
                fill="none"
              />
              <circle cx="9" cy="10" r="1" fill="#FFF9F0" />
              <circle cx="15" cy="10" r="1" fill="#FFF9F0" />
              <path
                d="M9 14h6"
                stroke="#FFF9F0"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <span
            style={{
              marginTop: "10px",
              fontSize: "13px",
              fontFamily: "Montserrat",
              color: "#B8860B",
            }}
          >
            Orchestrator
          </span>
        </div>

        {/* Parallel Agents Label */}
        <div
          style={{
            position: "absolute",
            left: "420px",
            top: "25px",
            display: "flex",
            alignItems: "center",
          }}
        >
          <span
            style={{
              fontSize: "11px",
              fontFamily: "Montserrat",
              color: "rgba(120,80,20,0.6)",
              textTransform: "uppercase",
              letterSpacing: "2px",
            }}
          >
            Parallel Agents
          </span>
        </div>

        {/* Agent 1 - Code (top) */}
        <div
          style={{
            position: "absolute",
            left: "400px",
            top: "55px",
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
              boxShadow:
                "0 6px 25px rgba(180,120,30,0.35), 0 3px 10px rgba(120,80,30,0.2)",
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <polyline
                points="16,18 22,12 16,6"
                stroke="#FFF9F0"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <polyline
                points="8,6 2,12 8,18"
                stroke="#FFF9F0"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span
            style={{
              marginTop: "6px",
              fontSize: "11px",
              fontFamily: "Montserrat",
              color: "rgba(80,55,25,0.7)",
            }}
          >
            Code
          </span>
        </div>

        {/* Agent 2 - Test (middle) */}
        <div
          style={{
            position: "absolute",
            left: "400px",
            top: "50%",
            transform: "translateY(-50%)",
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
              boxShadow:
                "0 6px 25px rgba(160,110,20,0.35), 0 3px 10px rgba(100,70,20,0.2)",
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path
                d="M9 11l3 3L22 4"
                stroke="#FFF9F0"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"
                stroke="#FFF9F0"
                strokeWidth="2"
                fill="none"
              />
            </svg>
          </div>
          <span
            style={{
              marginTop: "6px",
              fontSize: "11px",
              fontFamily: "Montserrat",
              color: "rgba(80,55,25,0.7)",
            }}
          >
            Test
          </span>
        </div>

        {/* Agent 3 - Review (bottom) */}
        <div
          style={{
            position: "absolute",
            left: "400px",
            top: "275px",
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
              boxShadow:
                "0 6px 25px rgba(140,100,20,0.35), 0 3px 10px rgba(90,60,15,0.2)",
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path
                d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
                stroke="#FFF9F0"
                strokeWidth="2"
                fill="none"
              />
              <circle
                cx="12"
                cy="12"
                r="3"
                stroke="#FFF9F0"
                strokeWidth="2"
                fill="none"
              />
            </svg>
          </div>
          <span
            style={{
              marginTop: "6px",
              fontSize: "11px",
              fontFamily: "Montserrat",
              color: "rgba(80,55,25,0.7)",
            }}
          >
            Review
          </span>
        </div>

        {/* Sync Gate - Centered properly */}
        <div
          style={{
            position: "absolute",
            left: "610px",
            top: "50%",
            transform: "translateY(-50%)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <div
            style={{
              width: "65px",
              height: "65px",
              background:
                "linear-gradient(135deg, rgba(180,120,30,0.15) 0%, rgba(150,100,20,0.08) 100%)",
              border: "3px solid rgba(180,120,30,0.5)",
              transform: "rotate(45deg)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 6px 20px rgba(120,80,30,0.2), 0 3px 8px rgba(100,65,20,0.15)",
            }}
          >
            <div style={{ transform: "rotate(-45deg)", display: "flex" }}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 2L2 7l10 5 10-5-10-5z"
                  stroke="#B8860B"
                  strokeWidth="2"
                  fill="none"
                />
                <path
                  d="M2 17l10 5 10-5"
                  stroke="#B8860B"
                  strokeWidth="2"
                  fill="none"
                />
                <path
                  d="M2 12l10 5 10-5"
                  stroke="#B8860B"
                  strokeWidth="2"
                  fill="none"
                />
              </svg>
            </div>
          </div>
          <span
            style={{
              marginTop: "18px",
              fontSize: "11px",
              fontFamily: "Montserrat",
              color: "rgba(120,80,20,0.8)",
            }}
          >
            Gate
          </span>
        </div>

        {/* Integration - with merge icon */}
        <div
          style={{
            position: "absolute",
            left: "820px",
            top: "50%",
            transform: "translateY(-50%)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <div
            style={{
              width: "75px",
              height: "75px",
              borderRadius: "38px",
              background: "linear-gradient(135deg, #996515 0%, #8B6914 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 6px 25px rgba(130,90,20,0.35), 0 3px 10px rgba(90,60,15,0.2)",
            }}
          >
            {/* Merge arrows icon */}
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none">
              <path
                d="M18 8L22 12L18 16"
                stroke="#FFF9F0"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M2 12H22"
                stroke="#FFF9F0"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
              <path
                d="M8 6L2 12L8 18"
                stroke="#FFF9F0"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span
            style={{
              marginTop: "8px",
              fontSize: "11px",
              fontFamily: "Montserrat",
              color: "rgba(80,55,25,0.7)",
            }}
          >
            Integrate
          </span>
        </div>

        {/* Complete */}
        <div
          style={{
            position: "absolute",
            right: "35px",
            top: "50%",
            transform: "translateY(-50%)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <div
            style={{
              width: "85px",
              height: "85px",
              borderRadius: "43px",
              background: "linear-gradient(135deg, #2E8B57 0%, #228B22 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                "0 8px 30px rgba(46,139,87,0.4), 0 4px 12px rgba(34,110,34,0.25)",
            }}
          >
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
              <path
                d="M20 6L9 17l-5-5"
                stroke="#ffffff"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span
            style={{
              marginTop: "10px",
              fontSize: "13px",
              fontFamily: "Montserrat",
              color: "rgba(46,139,87,0.95)",
            }}
          >
            Complete
          </span>
        </div>
      </div>

      {/* Bottom tagline */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          marginTop: "10px",
          zIndex: 1,
        }}
      >
        <span
          style={{
            fontSize: "18px",
            fontFamily: "Montserrat",
            fontWeight: 300,
            color: "rgba(80,55,25,0.6)",
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
