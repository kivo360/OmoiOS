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
        {/* Circular pattern overlay */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              "radial-gradient(ellipse 70% 70% at 65% 50%, rgba(255,180,50,0.06) 0%, transparent 60%)",
            display: "flex",
          }}
        />

        {/* Left side - Text content */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            width: "400px",
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
              Agents that
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
              iterate.
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
            Refine until it's right.
          </div>
        </div>

        {/* Right side - Iteration Loop Visualization */}
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
              width: "520px",
              height: "520px",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {/* Outer faded ring (past iterations) */}
            <div
              style={{
                position: "absolute",
                width: "480px",
                height: "480px",
                borderRadius: "240px",
                border: "1px solid rgba(255,200,50,0.1)",
                display: "flex",
              }}
            />

            {/* Middle ring */}
            <div
              style={{
                position: "absolute",
                width: "400px",
                height: "400px",
                borderRadius: "200px",
                border: "2px solid rgba(255,200,50,0.15)",
                display: "flex",
              }}
            />

            {/* Main iteration ring */}
            <div
              style={{
                position: "absolute",
                width: "320px",
                height: "320px",
                borderRadius: "160px",
                border: "3px solid rgba(255,200,50,0.25)",
                display: "flex",
              }}
            />

            {/* Circular flow arrows (SVG) */}
            <svg
              width="520"
              height="520"
              viewBox="0 0 520 520"
              fill="none"
              style={{ position: "absolute" }}
            >
              {/* Circular arrow path */}
              <defs>
                <linearGradient id="arrowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#FFE78A" stopOpacity="0.8" />
                  <stop offset="50%" stopColor="#FFD04A" stopOpacity="0.6" />
                  <stop offset="100%" stopColor="#FF8A2A" stopOpacity="0.8" />
                </linearGradient>
              </defs>

              {/* Top arc arrow */}
              <path
                d="M 340 115 A 145 145 0 0 1 405 260"
                stroke="url(#arrowGrad)"
                strokeWidth="2"
                fill="none"
                strokeDasharray="8 4"
              />
              <polygon points="408,250 400,270 415,265" fill="#FFD04A" opacity="0.8" />

              {/* Right arc arrow */}
              <path
                d="M 405 260 A 145 145 0 0 1 340 405"
                stroke="url(#arrowGrad)"
                strokeWidth="2"
                fill="none"
                strokeDasharray="8 4"
              />
              <polygon points="350,408 330,400 335,415" fill="#FFD04A" opacity="0.8" />

              {/* Bottom arc arrow */}
              <path
                d="M 340 405 A 145 145 0 0 1 180 405"
                stroke="url(#arrowGrad)"
                strokeWidth="2"
                fill="none"
                strokeDasharray="8 4"
              />
              <polygon points="170,400 190,408 185,393" fill="#FFD04A" opacity="0.8" />

              {/* Left arc arrow */}
              <path
                d="M 180 405 A 145 145 0 0 1 115 260"
                stroke="url(#arrowGrad)"
                strokeWidth="2"
                fill="none"
                strokeDasharray="8 4"
              />
              <polygon points="112,250 120,270 105,265" fill="#FFD04A" opacity="0.8" />

              {/* Top-left arc arrow */}
              <path
                d="M 115 260 A 145 145 0 0 1 180 115"
                stroke="url(#arrowGrad)"
                strokeWidth="2"
                fill="none"
                strokeDasharray="8 4"
              />
              <polygon points="190,112 170,120 175,105" fill="#FFD04A" opacity="0.8" />

              {/* Close the loop */}
              <path
                d="M 180 115 A 145 145 0 0 1 340 115"
                stroke="url(#arrowGrad)"
                strokeWidth="2"
                fill="none"
                strokeDasharray="8 4"
              />
              <polygon points="350,120 330,112 335,127" fill="#FFD04A" opacity="0.8" />
            </svg>

            {/* Phase nodes on the ring */}
            {/* Execute - Top */}
            <div
              style={{
                position: "absolute",
                top: "35px",
                left: "50%",
                transform: "translateX(-50%)",
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
                {/* Code icon */}
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none">
                  <polyline points="16,18 22,12 16,6" stroke="#1a150d" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  <polyline points="8,6 2,12 8,18" stroke="#1a150d" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "8px",
                  fontSize: "13px",
                  fontFamily: "Montserrat",
                  fontWeight: 400,
                  color: "#FFD04A",
                }}
              >
                Execute
              </span>
            </div>

            {/* Test - Right */}
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
                {/* Test/Check icon */}
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none">
                  <path d="M9 11l3 3L22 4" stroke="#1a150d" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke="#1a150d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "8px",
                  fontSize: "13px",
                  fontFamily: "Montserrat",
                  fontWeight: 400,
                  color: "#F0A500",
                }}
              >
                Test
              </span>
            </div>

            {/* Analyze - Bottom */}
            <div
              style={{
                position: "absolute",
                bottom: "35px",
                left: "50%",
                transform: "translateX(-50%)",
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
                {/* Magnifying glass icon */}
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                  <circle cx="11" cy="11" r="8" stroke="#1a150d" strokeWidth="2.5" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" stroke="#1a150d" strokeWidth="2.5" strokeLinecap="round" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "8px",
                  fontSize: "13px",
                  fontFamily: "Montserrat",
                  fontWeight: 400,
                  color: "#E8A317",
                }}
              >
                Analyze
              </span>
            </div>

            {/* Refine - Left */}
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
                  width: "70px",
                  height: "70px",
                  borderRadius: "35px",
                  background: "linear-gradient(135deg, #E8A317 0%, #D4A017 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 0 35px rgba(232,163,23,0.5)",
                }}
              >
                {/* Wrench/tool icon */}
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                  <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" stroke="#1a150d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                </svg>
              </div>
              <span
                style={{
                  marginTop: "8px",
                  fontSize: "13px",
                  fontFamily: "Montserrat",
                  fontWeight: 400,
                  color: "#D4A017",
                }}
              >
                Refine
              </span>
            </div>

            {/* Center Agent Core */}
            <div
              style={{
                width: "100px",
                height: "100px",
                borderRadius: "50px",
                background: "linear-gradient(135deg, #FFE78A 0%, #FFD04A 50%, #FF8A2A 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 0 60px rgba(255,180,50,0.6)",
                zIndex: 10,
              }}
            >
              {/* Infinity/loop icon */}
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none">
                <path
                  d="M18.178 8c5.096 0 5.096 8 0 8-5.095 0-7.133-8-12.739-8-4.585 0-4.585 8 0 8 5.606 0 7.644-8 12.74-8z"
                  stroke="#1a150d"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
              </svg>
            </div>

            {/* Iteration counter */}
            <div
              style={{
                position: "absolute",
                bottom: "-15px",
                right: "80px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "rgba(255,200,50,0.1)",
                borderRadius: "12px",
                padding: "6px 14px",
                border: "1px solid rgba(255,200,50,0.2)",
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M23 4v6h-6M1 20v-6h6" stroke="#FFD04A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" stroke="#FFD04A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span
                style={{
                  fontSize: "12px",
                  fontFamily: "Montserrat",
                  color: "rgba(255,230,180,0.8)",
                }}
              >
                Continuous
              </span>
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
