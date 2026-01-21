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
        {/* Subtle grid pattern overlay */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundImage: "radial-gradient(rgba(180,120,30,0.04) 1px, transparent 1px)",
            backgroundSize: "30px 30px",
            display: "flex",
          }}
        />

        {/* Warm gradient overlay */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              "radial-gradient(ellipse 80% 60% at 70% 50%, rgba(255,180,50,0.06) 0%, transparent 50%)",
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
                fontSize: "52px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "#3D2914",
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
                background: "linear-gradient(135deg, #D4920A 0%, #B8860B 35%, #996515 100%)",
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
              color: "rgba(80,55,25,0.6)",
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
            {/* Connection lines */}
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
                stroke="url(#lineGradLight)"
                strokeWidth="2"
                fill="none"
                opacity="0.7"
              />
              <path
                d="M 80 240 L 160 240"
                stroke="url(#lineGradLight)"
                strokeWidth="2"
                fill="none"
                opacity="0.7"
              />
              <path
                d="M 80 240 Q 140 240 160 360"
                stroke="url(#lineGradLight)"
                strokeWidth="2"
                fill="none"
                opacity="0.7"
              />

              {/* Layer 2 to Gate */}
              <path
                d="M 260 120 Q 320 120 340 200"
                stroke="url(#lineGradLight)"
                strokeWidth="2"
                fill="none"
                opacity="0.7"
              />
              <path
                d="M 260 240 L 340 200"
                stroke="url(#lineGradLight)"
                strokeWidth="2"
                fill="none"
                opacity="0.7"
              />
              <path
                d="M 260 360 Q 320 360 340 280"
                stroke="url(#lineGradLight)"
                strokeWidth="2"
                fill="none"
                opacity="0.7"
              />

              {/* Gate to Layer 3 */}
              <path
                d="M 400 240 Q 440 240 460 160"
                stroke="url(#lineGradLight)"
                strokeWidth="2"
                fill="none"
                opacity="0.7"
              />
              <path
                d="M 400 240 Q 440 240 460 320"
                stroke="url(#lineGradLight)"
                strokeWidth="2"
                fill="none"
                opacity="0.7"
              />

              {/* Layer 3 to Done */}
              <path
                d="M 540 160 Q 580 160 600 240"
                stroke="url(#lineGradLight)"
                strokeWidth="2"
                fill="none"
                opacity="0.7"
              />
              <path
                d="M 540 320 Q 580 320 600 240"
                stroke="url(#lineGradLight)"
                strokeWidth="2"
                fill="none"
                opacity="0.7"
              />

              <defs>
                <linearGradient id="lineGradLight" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#B8860B" stopOpacity="0.4" />
                  <stop offset="50%" stopColor="#B8860B" stopOpacity="0.7" />
                  <stop offset="100%" stopColor="#996515" stopOpacity="0.4" />
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
                  background: "linear-gradient(135deg, rgba(212,146,10,0.15) 0%, rgba(184,134,11,0.08) 100%)",
                  border: "2px solid rgba(180,120,30,0.35)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 20px rgba(180,120,30,0.15)",
                }}
              >
                {/* Document icon */}
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
                    stroke="#B8860B"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                  />
                  <polyline
                    points="14,2 14,8 20,8"
                    stroke="#B8860B"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                  />
                  <line x1="16" y1="13" x2="8" y2="13" stroke="#B8860B" strokeWidth="2" strokeLinecap="round" />
                  <line x1="16" y1="17" x2="8" y2="17" stroke="#B8860B" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "8px",
                  fontSize: "13px",
                  fontFamily: "Montserrat",
                  color: "rgba(80,55,25,0.7)",
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
                  background: "linear-gradient(135deg, #D4920A 0%, #B8860B 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 25px rgba(212,146,10,0.4)",
                }}
              >
                {/* API icon */}
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                  <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "6px",
                  fontSize: "12px",
                  fontFamily: "Montserrat",
                  color: "rgba(80,55,25,0.7)",
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
                  background: "linear-gradient(135deg, #B8860B 0%, #A67C00 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 25px rgba(184,134,11,0.4)",
                }}
              >
                {/* UI icon */}
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="3" width="18" height="18" rx="2" stroke="#FFF9F0" strokeWidth="2" fill="none" />
                  <line x1="3" y1="9" x2="21" y2="9" stroke="#FFF9F0" strokeWidth="2" />
                  <line x1="9" y1="21" x2="9" y2="9" stroke="#FFF9F0" strokeWidth="2" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "6px",
                  fontSize: "12px",
                  fontFamily: "Montserrat",
                  color: "rgba(80,55,25,0.7)",
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
                  background: "linear-gradient(135deg, #A67C00 0%, #996515 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 25px rgba(166,124,0,0.4)",
                }}
              >
                {/* Test icon */}
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                  <path d="M9 11l3 3L22 4" stroke="#FFF9F0" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "6px",
                  fontSize: "12px",
                  fontFamily: "Montserrat",
                  color: "rgba(80,55,25,0.7)",
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
                  background: "linear-gradient(135deg, rgba(180,120,30,0.2) 0%, rgba(150,100,20,0.12) 100%)",
                  border: "2px solid rgba(180,120,30,0.4)",
                  transform: "rotate(45deg)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 20px rgba(180,120,30,0.2)",
                }}
              >
                <div style={{ transform: "rotate(-45deg)", display: "flex" }}>
                  {/* Gate icon */}
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="#B8860B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                    <path d="M2 17l10 5 10-5" stroke="#B8860B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                    <path d="M2 12l10 5 10-5" stroke="#B8860B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  </svg>
                </div>
              </div>
              <span
                style={{
                  marginTop: "12px",
                  fontSize: "11px",
                  fontFamily: "Montserrat",
                  color: "rgba(120,80,20,0.8)",
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
                  background: "linear-gradient(135deg, #C78B15 0%, #A67C00 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 25px rgba(199,139,21,0.4)",
                }}
              >
                {/* Integration icon */}
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="3" stroke="#FFF9F0" strokeWidth="2" fill="none" />
                  <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" />
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
                  background: "linear-gradient(135deg, #996515 0%, #8B6914 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 25px rgba(153,101,21,0.4)",
                }}
              >
                {/* Deploy/Rocket icon */}
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
                  <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  <path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
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
                  background: "linear-gradient(135deg, #2E8B57 0%, #228B22 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 30px rgba(46,139,87,0.4)",
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
                  color: "rgba(46,139,87,0.9)",
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
                  color: "rgba(120,80,20,0.6)",
                  textTransform: "uppercase",
                  letterSpacing: "1px",
                }}
              >
                Parallel
              </div>
              <svg width="40" height="12" viewBox="0 0 40 12" fill="none">
                <path d="M0 6h35M30 1l5 5-5 5" stroke="rgba(180,120,30,0.5)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
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
