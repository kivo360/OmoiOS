import { ImageResponse } from "next/og"

export const runtime = "edge"

export async function GET() {
  // Load Montserrat font
  const montserratRegular = fetch(
    new URL("../../public/fonts/Montserrat-Regular.ttf", import.meta.url)
  ).then((res) => res.arrayBuffer())

  const montserratLight = fetch(
    new URL("../../public/fonts/Montserrat-Light.ttf", import.meta.url)
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
          padding: "60px",
        }}
      >
        {/* Warm golden gradient overlay */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              "radial-gradient(ellipse 100% 80% at 30% 30%, rgba(255,180,50,0.08) 0%, transparent 50%)",
            display: "flex",
          }}
        />

        {/* Left side - Text content */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            flex: 1,
            paddingRight: "40px",
            zIndex: 1,
          }}
        >
          {/* Logo + domain pill */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              marginBottom: "36px",
            }}
          >
            {/* Mini logo */}
            <svg
              width="52"
              height="52"
              viewBox="0 0 512 512"
              fill="none"
              style={{ marginRight: "16px" }}
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
            {/* Domain pill - warm amber tint */}
            <div
              style={{
                display: "flex",
                background: "rgba(180,120,30,0.1)",
                borderRadius: "20px",
                padding: "8px 20px",
                fontSize: "18px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "rgba(120,80,20,0.85)",
                border: "1px solid rgba(180,120,30,0.2)",
              }}
            >
              omoios.dev
            </div>
          </div>

          {/* Main headline - bigger, bolder */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "4px",
            }}
          >
            <span
              style={{
                fontSize: "64px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "#3D2914",
                lineHeight: 1.1,
              }}
            >
              Go to sleep.
            </span>
            <span
              style={{
                fontSize: "64px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                background: "linear-gradient(135deg, #D4920A 0%, #B8860B 35%, #996515 100%)",
                backgroundClip: "text",
                color: "transparent",
                lineHeight: 1.1,
              }}
            >
              Wake up to
            </span>
            <span
              style={{
                fontSize: "64px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                background: "linear-gradient(135deg, #B8860B 0%, #8B6914 100%)",
                backgroundClip: "text",
                color: "transparent",
                lineHeight: 1.1,
              }}
            >
              finished features.
            </span>
          </div>

          {/* Subheadline */}
          <div
            style={{
              display: "flex",
              fontSize: "22px",
              fontFamily: "Montserrat",
              fontWeight: 300,
              color: "rgba(80,55,25,0.6)",
              marginTop: "28px",
              lineHeight: 1.5,
            }}
          >
            AI agents that build while you rest.
          </div>
        </div>

        {/* Right side - Visual element */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "380px",
            position: "relative",
          }}
        >
          {/* Warm glow effect */}
          <div
            style={{
              position: "absolute",
              width: "380px",
              height: "380px",
              borderRadius: "200px",
              background:
                "radial-gradient(circle, rgba(255,180,50,0.15) 0%, rgba(255,138,42,0.06) 40%, transparent 70%)",
              display: "flex",
            }}
          />

          {/* Agent visualization - concentric rings with golden agent nodes */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
              width: "300px",
              height: "300px",
            }}
          >
            {/* Outer ring - warm amber */}
            <div
              style={{
                position: "absolute",
                width: "280px",
                height: "280px",
                borderRadius: "140px",
                border: "2px solid rgba(180,120,30,0.2)",
                display: "flex",
              }}
            />
            {/* Middle ring */}
            <div
              style={{
                position: "absolute",
                width: "200px",
                height: "200px",
                borderRadius: "100px",
                border: "2px solid rgba(180,120,30,0.3)",
                display: "flex",
              }}
            />
            {/* Inner ring */}
            <div
              style={{
                position: "absolute",
                width: "120px",
                height: "120px",
                borderRadius: "60px",
                border: "2px solid rgba(180,120,30,0.45)",
                display: "flex",
              }}
            />

            {/* Agent nodes on outer ring - deeper golden/amber tones */}
            <div
              style={{
                position: "absolute",
                width: "20px",
                height: "20px",
                borderRadius: "10px",
                background: "#D4920A",
                boxShadow: "0 0 24px rgba(212,146,10,0.4)",
                transform: "translate(140px, 0px)",
                display: "flex",
              }}
            />
            <div
              style={{
                position: "absolute",
                width: "20px",
                height: "20px",
                borderRadius: "10px",
                background: "#C78B15",
                boxShadow: "0 0 24px rgba(199,139,21,0.4)",
                transform: "translate(70px, 121px)",
                display: "flex",
              }}
            />
            <div
              style={{
                position: "absolute",
                width: "20px",
                height: "20px",
                borderRadius: "10px",
                background: "#B8860B",
                boxShadow: "0 0 24px rgba(184,134,11,0.4)",
                transform: "translate(-70px, 121px)",
                display: "flex",
              }}
            />
            <div
              style={{
                position: "absolute",
                width: "20px",
                height: "20px",
                borderRadius: "10px",
                background: "#A67C00",
                boxShadow: "0 0 24px rgba(166,124,0,0.4)",
                transform: "translate(-140px, 0px)",
                display: "flex",
              }}
            />
            <div
              style={{
                position: "absolute",
                width: "20px",
                height: "20px",
                borderRadius: "10px",
                background: "#996515",
                boxShadow: "0 0 24px rgba(153,101,21,0.4)",
                transform: "translate(-70px, -121px)",
                display: "flex",
              }}
            />
            <div
              style={{
                position: "absolute",
                width: "20px",
                height: "20px",
                borderRadius: "10px",
                background: "#8B6914",
                boxShadow: "0 0 24px rgba(139,105,20,0.4)",
                transform: "translate(70px, -121px)",
                display: "flex",
              }}
            />

            {/* Nodes on middle ring */}
            <div
              style={{
                position: "absolute",
                width: "14px",
                height: "14px",
                borderRadius: "7px",
                background: "#DAA520",
                boxShadow: "0 0 16px rgba(218,165,32,0.35)",
                transform: "translate(87px, 50px)",
                display: "flex",
              }}
            />
            <div
              style={{
                position: "absolute",
                width: "14px",
                height: "14px",
                borderRadius: "7px",
                background: "#CD950C",
                boxShadow: "0 0 16px rgba(205,149,12,0.35)",
                transform: "translate(0px, 100px)",
                display: "flex",
              }}
            />
            <div
              style={{
                position: "absolute",
                width: "14px",
                height: "14px",
                borderRadius: "7px",
                background: "#C68E17",
                boxShadow: "0 0 16px rgba(198,142,23,0.35)",
                transform: "translate(-87px, 50px)",
                display: "flex",
              }}
            />
            <div
              style={{
                position: "absolute",
                width: "14px",
                height: "14px",
                borderRadius: "7px",
                background: "#B8860B",
                boxShadow: "0 0 16px rgba(184,134,11,0.35)",
                transform: "translate(-87px, -50px)",
                display: "flex",
              }}
            />
            <div
              style={{
                position: "absolute",
                width: "14px",
                height: "14px",
                borderRadius: "7px",
                background: "#D4A017",
                boxShadow: "0 0 16px rgba(212,160,23,0.35)",
                transform: "translate(0px, -100px)",
                display: "flex",
              }}
            />
            <div
              style={{
                position: "absolute",
                width: "14px",
                height: "14px",
                borderRadius: "7px",
                background: "#C5A000",
                boxShadow: "0 0 16px rgba(197,160,0,0.35)",
                transform: "translate(87px, -50px)",
                display: "flex",
              }}
            />

            {/* Center core - larger, more prominent */}
            <div
              style={{
                width: "70px",
                height: "70px",
                borderRadius: "35px",
                background: "linear-gradient(135deg, #E8A917 0%, #D4920A 50%, #B8860B 100%)",
                boxShadow: "0 0 50px rgba(212,146,10,0.45)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {/* Sun icon in the center - represents daytime/light mode */}
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="5" fill="#FFF9F0" stroke="#FFF9F0" strokeWidth="2" />
                <line x1="12" y1="1" x2="12" y2="3" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" />
                <line x1="12" y1="21" x2="12" y2="23" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" />
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" />
                <line x1="1" y1="12" x2="3" y2="12" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" />
                <line x1="21" y1="12" x2="23" y2="12" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" />
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" stroke="#FFF9F0" strokeWidth="2" strokeLinecap="round" />
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
