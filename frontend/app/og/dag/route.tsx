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
          background: "linear-gradient(145deg, #2d2618 0%, #1a150d 50%, #0f0c08 100%)",
          position: "relative",
          padding: "50px 60px",
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
            backgroundImage: "radial-gradient(rgba(255,200,50,0.03) 1px, transparent 1px)",
            backgroundSize: "30px 30px",
            display: "flex",
          }}
        />

        {/* Golden warm gradient overlay */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              "radial-gradient(ellipse 80% 60% at 70% 50%, rgba(255,180,50,0.08) 0%, transparent 50%)",
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
            paddingRight: "40px",
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
                <g strokeWidth="14">
                  <circle cx="256" cy="256" r="210" fill="none" opacity="0.55" />
                </g>
              </g>
            </svg>
            <div
              style={{
                display: "flex",
                background: "rgba(255,200,50,0.15)",
                borderRadius: "20px",
                padding: "6px 16px",
                fontSize: "16px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "rgba(255,230,180,0.9)",
                border: "1px solid rgba(255,200,50,0.2)",
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
                fontSize: "52px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "#ffffff",
                lineHeight: 1.1,
              }}
            >
              Parallel
            </span>
            <span
              style={{
                fontSize: "52px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                background: "linear-gradient(135deg, #FFE78A 0%, #FFD04A 35%, #FF8A2A 100%)",
                backgroundClip: "text",
                color: "transparent",
                lineHeight: 1.1,
              }}
            >
              by design.
            </span>
          </div>

          {/* Subheadline */}
          <div
            style={{
              display: "flex",
              fontSize: "20px",
              fontFamily: "Montserrat",
              fontWeight: 300,
              color: "rgba(255,230,200,0.6)",
              marginTop: "24px",
              lineHeight: 1.5,
            }}
          >
            Dependencies respected, speed maximized.
          </div>
        </div>

        {/* Right side - DAG Visualization */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flex: 1,
            position: "relative",
          }}
        >
          {/* DAG Container */}
          <div
            style={{
              display: "flex",
              position: "relative",
              width: "650px",
              height: "480px",
            }}
          >
            {/* Connection lines - Layer 1 to Layer 2 */}
            <svg
              width="650"
              height="480"
              viewBox="0 0 650 480"
              fill="none"
              style={{ position: "absolute", top: 0, left: 0 }}
            >
              {/* Spec to branches */}
              <path
                d="M 80 240 Q 140 240 160 120"
                stroke="url(#lineGrad)"
                strokeWidth="2"
                fill="none"
                opacity="0.6"
              />
              <path
                d="M 80 240 L 160 240"
                stroke="url(#lineGrad)"
                strokeWidth="2"
                fill="none"
                opacity="0.6"
              />
              <path
                d="M 80 240 Q 140 240 160 360"
                stroke="url(#lineGrad)"
                strokeWidth="2"
                fill="none"
                opacity="0.6"
              />

              {/* Layer 2 to Gate */}
              <path
                d="M 260 120 Q 320 120 340 200"
                stroke="url(#lineGrad)"
                strokeWidth="2"
                fill="none"
                opacity="0.6"
              />
              <path
                d="M 260 240 L 340 200"
                stroke="url(#lineGrad)"
                strokeWidth="2"
                fill="none"
                opacity="0.6"
              />
              <path
                d="M 260 360 Q 320 360 340 280"
                stroke="url(#lineGrad)"
                strokeWidth="2"
                fill="none"
                opacity="0.6"
              />

              {/* Gate to Layer 3 */}
              <path
                d="M 400 240 Q 440 240 460 160"
                stroke="url(#lineGrad)"
                strokeWidth="2"
                fill="none"
                opacity="0.6"
              />
              <path
                d="M 400 240 Q 440 240 460 320"
                stroke="url(#lineGrad)"
                strokeWidth="2"
                fill="none"
                opacity="0.6"
              />

              {/* Layer 3 to Done */}
              <path
                d="M 540 160 Q 580 160 600 240"
                stroke="url(#lineGrad)"
                strokeWidth="2"
                fill="none"
                opacity="0.6"
              />
              <path
                d="M 540 320 Q 580 320 600 240"
                stroke="url(#lineGrad)"
                strokeWidth="2"
                fill="none"
                opacity="0.6"
              />

              <defs>
                <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#FFD04A" stopOpacity="0.3" />
                  <stop offset="50%" stopColor="#FFD04A" stopOpacity="0.6" />
                  <stop offset="100%" stopColor="#FF8A2A" stopOpacity="0.3" />
                </linearGradient>
              </defs>
            </svg>

            {/* Layer 1: Spec Node */}
            <div
              style={{
                position: "absolute",
                left: "30px",
                top: "200px",
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
                  background: "linear-gradient(135deg, rgba(255,215,0,0.2) 0%, rgba(255,138,42,0.1) 100%)",
                  border: "2px solid rgba(255,200,50,0.4)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 0 30px rgba(255,180,50,0.2)",
                }}
              >
                {/* Document icon */}
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
                    stroke="#FFD04A"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                  />
                  <polyline
                    points="14,2 14,8 20,8"
                    stroke="#FFD04A"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                  />
                  <line x1="16" y1="13" x2="8" y2="13" stroke="#FFD04A" strokeWidth="2" strokeLinecap="round" />
                  <line x1="16" y1="17" x2="8" y2="17" stroke="#FFD04A" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "8px",
                  fontSize: "13px",
                  fontFamily: "Montserrat",
                  color: "rgba(255,230,200,0.7)",
                }}
              >
                Spec
              </span>
            </div>

            {/* Layer 2: Parallel Agent Nodes */}
            {/* Agent 1 - API */}
            <div
              style={{
                position: "absolute",
                left: "160px",
                top: "80px",
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
                  background: "linear-gradient(135deg, #FFE78A 0%, #FFD04A 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 0 35px rgba(255,215,0,0.5)",
                }}
              >
                {/* API icon */}
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                  <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" stroke="#1a150d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "6px",
                  fontSize: "12px",
                  fontFamily: "Montserrat",
                  color: "rgba(255,230,200,0.7)",
                }}
              >
                API Agent
              </span>
            </div>

            {/* Agent 2 - UI */}
            <div
              style={{
                position: "absolute",
                left: "160px",
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
                  background: "linear-gradient(135deg, #FFD04A 0%, #F0A500 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 0 35px rgba(255,179,71,0.5)",
                }}
              >
                {/* UI icon */}
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="3" width="18" height="18" rx="2" stroke="#1a150d" strokeWidth="2" fill="none" />
                  <line x1="3" y1="9" x2="21" y2="9" stroke="#1a150d" strokeWidth="2" />
                  <line x1="9" y1="21" x2="9" y2="9" stroke="#1a150d" strokeWidth="2" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "6px",
                  fontSize: "12px",
                  fontFamily: "Montserrat",
                  color: "rgba(255,230,200,0.7)",
                }}
              >
                UI Agent
              </span>
            </div>

            {/* Agent 3 - Test */}
            <div
              style={{
                position: "absolute",
                left: "160px",
                top: "320px",
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
                  background: "linear-gradient(135deg, #F0A500 0%, #E8A317 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 0 35px rgba(240,165,0,0.5)",
                }}
              >
                {/* Test icon */}
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                  <path d="M9 11l3 3L22 4" stroke="#1a150d" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke="#1a150d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "6px",
                  fontSize: "12px",
                  fontFamily: "Montserrat",
                  color: "rgba(255,230,200,0.7)",
                }}
              >
                Test Agent
              </span>
            </div>

            {/* Dependency Gate (Diamond) */}
            <div
              style={{
                position: "absolute",
                left: "330px",
                top: "200px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <div
                style={{
                  width: "60px",
                  height: "60px",
                  background: "linear-gradient(135deg, rgba(255,200,50,0.3) 0%, rgba(255,138,42,0.2) 100%)",
                  border: "2px solid rgba(255,200,50,0.5)",
                  transform: "rotate(45deg)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 0 25px rgba(255,180,50,0.3)",
                }}
              >
                <div style={{ transform: "rotate(-45deg)", display: "flex" }}>
                  {/* Gate icon */}
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="#FFD04A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                    <path d="M2 17l10 5 10-5" stroke="#FFD04A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                    <path d="M2 12l10 5 10-5" stroke="#FFD04A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  </svg>
                </div>
              </div>
              <span
                style={{
                  marginTop: "12px",
                  fontSize: "11px",
                  fontFamily: "Montserrat",
                  color: "rgba(255,200,50,0.8)",
                }}
              >
                Sync Gate
              </span>
            </div>

            {/* Layer 3: Post-gate parallel */}
            {/* Integration Agent */}
            <div
              style={{
                position: "absolute",
                left: "460px",
                top: "120px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <div
                style={{
                  width: "65px",
                  height: "65px",
                  borderRadius: "32px",
                  background: "linear-gradient(135deg, #FFB347 0%, #E8A317 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 0 30px rgba(255,179,71,0.5)",
                }}
              >
                {/* Integration icon */}
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="3" stroke="#1a150d" strokeWidth="2" fill="none" />
                  <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" stroke="#1a150d" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "6px",
                  fontSize: "11px",
                  fontFamily: "Montserrat",
                  color: "rgba(255,230,200,0.7)",
                }}
              >
                Integration
              </span>
            </div>

            {/* Deploy Agent */}
            <div
              style={{
                position: "absolute",
                left: "460px",
                top: "280px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <div
                style={{
                  width: "65px",
                  height: "65px",
                  borderRadius: "32px",
                  background: "linear-gradient(135deg, #E8A317 0%, #D4A017 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 0 30px rgba(232,163,23,0.5)",
                }}
              >
                {/* Deploy/Rocket icon */}
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
                  <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" stroke="#1a150d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  <path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" stroke="#1a150d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" stroke="#1a150d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "6px",
                  fontSize: "11px",
                  fontFamily: "Montserrat",
                  color: "rgba(255,230,200,0.7)",
                }}
              >
                Deploy
              </span>
            </div>

            {/* Final: Done Node */}
            <div
              style={{
                position: "absolute",
                left: "570px",
                top: "200px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <div
                style={{
                  width: "80px",
                  height: "80px",
                  borderRadius: "40px",
                  background: "linear-gradient(135deg, #50C878 0%, #3CB371 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 0 40px rgba(80,200,120,0.5)",
                }}
              >
                {/* Checkmark icon */}
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17l-5-5" stroke="#ffffff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "8px",
                  fontSize: "13px",
                  fontFamily: "Montserrat",
                  color: "rgba(80,200,120,0.9)",
                }}
              >
                Complete
              </span>
            </div>

            {/* "Parallel" indicator arrows */}
            <div
              style={{
                position: "absolute",
                left: "120px",
                top: "45px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <div
                style={{
                  fontSize: "10px",
                  fontFamily: "Montserrat",
                  color: "rgba(255,200,50,0.6)",
                  textTransform: "uppercase",
                  letterSpacing: "1px",
                }}
              >
                Parallel
              </div>
              <svg width="40" height="12" viewBox="0 0 40 12" fill="none">
                <path d="M0 6h35M30 1l5 5-5 5" stroke="rgba(255,200,50,0.4)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
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
