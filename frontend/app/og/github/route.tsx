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
          padding: "60px",
        }}
      >
        {/* Golden warm gradient overlay */}
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
            {/* OSS badge */}
            <div
              style={{
                display: "flex",
                background: "rgba(255,200,50,0.15)",
                borderRadius: "20px",
                padding: "8px 20px",
                fontSize: "18px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "rgba(255,230,180,0.9)",
                border: "1px solid rgba(255,200,50,0.2)",
              }}
            >
              Open Source — Apache 2.0
            </div>
          </div>

          {/* Main headline */}
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
                color: "#ffffff",
                lineHeight: 1.1,
              }}
            >
              Run structured
            </span>
            <span
              style={{
                fontSize: "64px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                background: "linear-gradient(135deg, #FFE78A 0%, #FFD04A 35%, #FF8A2A 100%)",
                backgroundClip: "text",
                color: "transparent",
                lineHeight: 1.1,
              }}
            >
              agent swarms.
            </span>
          </div>

          {/* Subheadline */}
          <div
            style={{
              display: "flex",
              fontSize: "22px",
              fontFamily: "Montserrat",
              fontWeight: 300,
              color: "rgba(255,230,200,0.6)",
              marginTop: "28px",
              lineHeight: 1.5,
            }}
          >
            Spec-driven multi-agent orchestration with DAGs, sandboxes, and supervision.
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
          {/* Golden glow effect */}
          <div
            style={{
              position: "absolute",
              width: "380px",
              height: "380px",
              borderRadius: "200px",
              background:
                "radial-gradient(circle, rgba(255,180,50,0.25) 0%, rgba(255,138,42,0.1) 40%, transparent 70%)",
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
            {/* Outer ring */}
            <div
              style={{
                position: "absolute",
                width: "280px",
                height: "280px",
                borderRadius: "140px",
                border: "2px solid rgba(255,200,50,0.2)",
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
                border: "2px solid rgba(255,200,50,0.3)",
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
                border: "2px solid rgba(255,200,50,0.45)",
                display: "flex",
              }}
            />

            {/* Agent nodes on outer ring */}
            <div style={{ position: "absolute", width: "20px", height: "20px", borderRadius: "10px", background: "#FFD700", boxShadow: "0 0 24px rgba(255,215,0,0.5)", transform: "translate(140px, 0px)", display: "flex" }} />
            <div style={{ position: "absolute", width: "20px", height: "20px", borderRadius: "10px", background: "#FFB347", boxShadow: "0 0 24px rgba(255,179,71,0.5)", transform: "translate(70px, 121px)", display: "flex" }} />
            <div style={{ position: "absolute", width: "20px", height: "20px", borderRadius: "10px", background: "#F0A500", boxShadow: "0 0 24px rgba(240,165,0,0.5)", transform: "translate(-70px, 121px)", display: "flex" }} />
            <div style={{ position: "absolute", width: "20px", height: "20px", borderRadius: "10px", background: "#E8A317", boxShadow: "0 0 24px rgba(232,163,23,0.5)", transform: "translate(-140px, 0px)", display: "flex" }} />
            <div style={{ position: "absolute", width: "20px", height: "20px", borderRadius: "10px", background: "#D4A017", boxShadow: "0 0 24px rgba(212,160,23,0.5)", transform: "translate(-70px, -121px)", display: "flex" }} />
            <div style={{ position: "absolute", width: "20px", height: "20px", borderRadius: "10px", background: "#C5A000", boxShadow: "0 0 24px rgba(197,160,0,0.5)", transform: "translate(70px, -121px)", display: "flex" }} />

            {/* Nodes on middle ring */}
            <div style={{ position: "absolute", width: "14px", height: "14px", borderRadius: "7px", background: "#FFC107", boxShadow: "0 0 16px rgba(255,193,7,0.4)", transform: "translate(87px, 50px)", display: "flex" }} />
            <div style={{ position: "absolute", width: "14px", height: "14px", borderRadius: "7px", background: "#F39C12", boxShadow: "0 0 16px rgba(243,156,18,0.4)", transform: "translate(0px, 100px)", display: "flex" }} />
            <div style={{ position: "absolute", width: "14px", height: "14px", borderRadius: "7px", background: "#E67E22", boxShadow: "0 0 16px rgba(230,126,34,0.4)", transform: "translate(-87px, 50px)", display: "flex" }} />
            <div style={{ position: "absolute", width: "14px", height: "14px", borderRadius: "7px", background: "#D4AC0D", boxShadow: "0 0 16px rgba(212,172,13,0.4)", transform: "translate(-87px, -50px)", display: "flex" }} />
            <div style={{ position: "absolute", width: "14px", height: "14px", borderRadius: "7px", background: "#F1C40F", boxShadow: "0 0 16px rgba(241,196,15,0.4)", transform: "translate(0px, -100px)", display: "flex" }} />
            <div style={{ position: "absolute", width: "14px", height: "14px", borderRadius: "7px", background: "#DAA520", boxShadow: "0 0 16px rgba(218,165,32,0.4)", transform: "translate(87px, -50px)", display: "flex" }} />

            {/* Center core - DAG icon instead of moon */}
            <div
              style={{
                width: "70px",
                height: "70px",
                borderRadius: "35px",
                background: "linear-gradient(135deg, #FFE78A 0%, #FFD04A 50%, #FF8A2A 100%)",
                boxShadow: "0 0 50px rgba(255,180,50,0.6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {/* DAG/network icon */}
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="5" r="2.5" fill="#1a150d" />
                <circle cx="6" cy="19" r="2.5" fill="#1a150d" />
                <circle cx="18" cy="19" r="2.5" fill="#1a150d" />
                <line x1="12" y1="7.5" x2="7" y2="16.5" stroke="#1a150d" strokeWidth="2" strokeLinecap="round" />
                <line x1="12" y1="7.5" x2="17" y2="16.5" stroke="#1a150d" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    ),
    {
      width: 1280,
      height: 640,
      fonts: [
        {
          name: "Montserrat",
          data: await montserratRegular,
          style: "normal" as const,
          weight: 400 as const,
        },
        {
          name: "Montserrat",
          data: await montserratLight,
          style: "normal" as const,
          weight: 300 as const,
        },
      ],
    }
  )
}
