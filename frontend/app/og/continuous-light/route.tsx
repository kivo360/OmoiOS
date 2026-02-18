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
        flexDirection: "row",
        background:
          "linear-gradient(145deg, #FFF9F0 0%, #FFF5E6 50%, #FFEDD5 100%)",
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
            "radial-gradient(ellipse 70% 70% at 65% 50%, rgba(180,120,30,0.04) 0%, transparent 60%)",
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
            Agents that
          </span>
          <span
            style={{
              fontSize: "52px",
              fontFamily: "Montserrat",
              fontWeight: 400,
              background:
                "linear-gradient(135deg, #D4920A 0%, #B8860B 35%, #996515 100%)",
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
            color: "rgba(80,55,25,0.6)",
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
              border: "1px solid rgba(180,120,30,0.08)",
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
              border: "2px solid rgba(180,120,30,0.12)",
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
              border: "3px solid rgba(180,120,30,0.2)",
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
              <linearGradient
                id="arrowGradLight"
                x1="0%"
                y1="0%"
                x2="100%"
                y2="100%"
              >
                <stop offset="0%" stopColor="#D4920A" stopOpacity="0.8" />
                <stop offset="50%" stopColor="#B8860B" stopOpacity="0.6" />
                <stop offset="100%" stopColor="#996515" stopOpacity="0.8" />
              </linearGradient>
            </defs>

            {/* Top arc arrow */}
            <path
              d="M 340 115 A 145 145 0 0 1 405 260"
              stroke="url(#arrowGradLight)"
              strokeWidth="2"
              fill="none"
              strokeDasharray="8 4"
            />
            <polygon
              points="408,250 400,270 415,265"
              fill="#B8860B"
              opacity="0.8"
            />

            {/* Right arc arrow */}
            <path
              d="M 405 260 A 145 145 0 0 1 340 405"
              stroke="url(#arrowGradLight)"
              strokeWidth="2"
              fill="none"
              strokeDasharray="8 4"
            />
            <polygon
              points="350,408 330,400 335,415"
              fill="#B8860B"
              opacity="0.8"
            />

            {/* Bottom arc arrow */}
            <path
              d="M 340 405 A 145 145 0 0 1 180 405"
              stroke="url(#arrowGradLight)"
              strokeWidth="2"
              fill="none"
              strokeDasharray="8 4"
            />
            <polygon
              points="170,400 190,408 185,393"
              fill="#B8860B"
              opacity="0.8"
            />

            {/* Left arc arrow */}
            <path
              d="M 180 405 A 145 145 0 0 1 115 260"
              stroke="url(#arrowGradLight)"
              strokeWidth="2"
              fill="none"
              strokeDasharray="8 4"
            />
            <polygon
              points="112,250 120,270 105,265"
              fill="#B8860B"
              opacity="0.8"
            />

            {/* Top-left arc arrow */}
            <path
              d="M 115 260 A 145 145 0 0 1 180 115"
              stroke="url(#arrowGradLight)"
              strokeWidth="2"
              fill="none"
              strokeDasharray="8 4"
            />
            <polygon
              points="190,112 170,120 175,105"
              fill="#B8860B"
              opacity="0.8"
            />

            {/* Close the loop */}
            <path
              d="M 180 115 A 145 145 0 0 1 340 115"
              stroke="url(#arrowGradLight)"
              strokeWidth="2"
              fill="none"
              strokeDasharray="8 4"
            />
            <polygon
              points="350,120 330,112 335,127"
              fill="#B8860B"
              opacity="0.8"
            />
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
                background: "linear-gradient(135deg, #D4920A 0%, #B8860B 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 25px rgba(212,146,10,0.4)",
              }}
            >
              {/* Code icon */}
              <svg width="30" height="30" viewBox="0 0 24 24" fill="none">
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
                marginTop: "8px",
                fontSize: "13px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "#B8860B",
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
                background: "linear-gradient(135deg, #B8860B 0%, #A67C00 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 25px rgba(184,134,11,0.4)",
              }}
            >
              {/* Test/Check icon */}
              <svg width="30" height="30" viewBox="0 0 24 24" fill="none">
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
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <span
              style={{
                marginTop: "8px",
                fontSize: "13px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "#A67C00",
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
                background: "linear-gradient(135deg, #A67C00 0%, #996515 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 25px rgba(166,124,0,0.4)",
              }}
            >
              {/* Magnifying glass icon */}
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                <circle
                  cx="11"
                  cy="11"
                  r="8"
                  stroke="#FFF9F0"
                  strokeWidth="2.5"
                />
                <line
                  x1="21"
                  y1="21"
                  x2="16.65"
                  y2="16.65"
                  stroke="#FFF9F0"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <span
              style={{
                marginTop: "8px",
                fontSize: "13px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "#996515",
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
                background: "linear-gradient(135deg, #996515 0%, #8B6914 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 25px rgba(153,101,21,0.4)",
              }}
            >
              {/* Wrench/tool icon */}
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                <path
                  d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"
                  stroke="#FFF9F0"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
              </svg>
            </div>
            <span
              style={{
                marginTop: "8px",
                fontSize: "13px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "#8B6914",
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
              background:
                "linear-gradient(135deg, #E8A917 0%, #D4920A 50%, #B8860B 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 4px 40px rgba(212,146,10,0.45)",
              zIndex: 10,
            }}
          >
            {/* Infinity/loop icon */}
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none">
              <path
                d="M18.178 8c5.096 0 5.096 8 0 8-5.095 0-7.133-8-12.739-8-4.585 0-4.585 8 0 8 5.606 0 7.644-8 12.74-8z"
                stroke="#FFF9F0"
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
              background: "rgba(180,120,30,0.08)",
              borderRadius: "12px",
              padding: "6px 14px",
              border: "1px solid rgba(180,120,30,0.15)",
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path
                d="M23 4v6h-6M1 20v-6h6"
                stroke="#B8860B"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
                stroke="#B8860B"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span
              style={{
                fontSize: "12px",
                fontFamily: "Montserrat",
                color: "rgba(120,80,20,0.8)",
              }}
            >
              Continuous
            </span>
          </div>
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
