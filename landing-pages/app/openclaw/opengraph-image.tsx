import { ImageResponse } from "next/og"

export const runtime = "edge"

export const alt = "OpenClaw - Your AI Assistant That Handles Clients While You Sleep"
export const size = {
  width: 1200,
  height: 630,
}
export const contentType = "image/png"

export default async function Image() {
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
          background: "linear-gradient(145deg, #1a1a2e 0%, #16213e 50%, #0f0f1a 100%)",
          position: "relative",
          padding: "60px",
        }}
      >
        {/* Orange/amber gradient overlay */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              "radial-gradient(ellipse 100% 80% at 30% 30%, rgba(251,146,60,0.15) 0%, transparent 50%)",
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
            {/* Bot icon as logo */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: "52px",
                height: "52px",
                borderRadius: "26px",
                background: "linear-gradient(135deg, #f59e0b 0%, #ea580c 100%)",
                marginRight: "16px",
              }}
            >
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2zM7.5 13a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm9 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z"
                  fill="#ffffff"
                />
              </svg>
            </div>
            {/* Domain pill */}
            <div
              style={{
                display: "flex",
                background: "rgba(251,146,60,0.15)",
                borderRadius: "20px",
                padding: "8px 20px",
                fontSize: "18px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "rgba(255,220,180,0.9)",
                border: "1px solid rgba(251,146,60,0.3)",
              }}
            >
              openclaw.omoios.dev
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
                fontSize: "52px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "#ffffff",
                lineHeight: 1.1,
              }}
            >
              Your AI Assistant
            </span>
            <span
              style={{
                fontSize: "52px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "#ffffff",
                lineHeight: 1.1,
              }}
            >
              That Handles
            </span>
            <span
              style={{
                fontSize: "52px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                background: "linear-gradient(135deg, #fbbf24 0%, #f59e0b 35%, #ea580c 100%)",
                backgroundClip: "text",
                color: "transparent",
                lineHeight: 1.1,
              }}
            >
              Clients While You Sleep
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
              marginTop: "28px",
              lineHeight: 1.5,
            }}
          >
            Stop answering the same WhatsApp questions 50 times a day.
          </div>

          {/* Feature pills */}
          <div
            style={{
              display: "flex",
              gap: "12px",
              marginTop: "24px",
            }}
          >
            <div
              style={{
                display: "flex",
                background: "rgba(34,197,94,0.15)",
                borderRadius: "16px",
                padding: "8px 16px",
                fontSize: "14px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "rgba(134,239,172,0.9)",
                border: "1px solid rgba(34,197,94,0.3)",
              }}
            >
              30-day guarantee
            </div>
            <div
              style={{
                display: "flex",
                background: "rgba(251,146,60,0.15)",
                borderRadius: "16px",
                padding: "8px 16px",
                fontSize: "14px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: "rgba(253,186,116,0.9)",
                border: "1px solid rgba(251,146,60,0.3)",
              }}
            >
              Ready in 48 hours
            </div>
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
          {/* Orange glow effect */}
          <div
            style={{
              position: "absolute",
              width: "380px",
              height: "380px",
              borderRadius: "200px",
              background:
                "radial-gradient(circle, rgba(251,146,60,0.25) 0%, rgba(234,88,12,0.1) 40%, transparent 70%)",
              display: "flex",
            }}
          />

          {/* Bot visualization - concentric rings */}
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
                border: "2px solid rgba(251,146,60,0.2)",
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
                border: "2px solid rgba(251,146,60,0.3)",
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
                border: "2px solid rgba(251,146,60,0.45)",
                display: "flex",
              }}
            />

            {/* Channel icons on outer ring */}
            {/* WhatsApp position */}
            <div
              style={{
                position: "absolute",
                width: "36px",
                height: "36px",
                borderRadius: "18px",
                background: "#25D366",
                boxShadow: "0 0 24px rgba(37,211,102,0.5)",
                transform: "translate(140px, 0px)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <span style={{ color: "#fff", fontSize: "18px" }}>W</span>
            </div>
            {/* Slack position */}
            <div
              style={{
                position: "absolute",
                width: "36px",
                height: "36px",
                borderRadius: "18px",
                background: "#4A154B",
                boxShadow: "0 0 24px rgba(74,21,75,0.5)",
                transform: "translate(70px, 121px)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <span style={{ color: "#fff", fontSize: "18px" }}>S</span>
            </div>
            {/* Discord position */}
            <div
              style={{
                position: "absolute",
                width: "36px",
                height: "36px",
                borderRadius: "18px",
                background: "#5865F2",
                boxShadow: "0 0 24px rgba(88,101,242,0.5)",
                transform: "translate(-70px, 121px)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <span style={{ color: "#fff", fontSize: "18px" }}>D</span>
            </div>
            {/* Telegram position */}
            <div
              style={{
                position: "absolute",
                width: "36px",
                height: "36px",
                borderRadius: "18px",
                background: "#0088cc",
                boxShadow: "0 0 24px rgba(0,136,204,0.5)",
                transform: "translate(-140px, 0px)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <span style={{ color: "#fff", fontSize: "18px" }}>T</span>
            </div>
            {/* Email position */}
            <div
              style={{
                position: "absolute",
                width: "36px",
                height: "36px",
                borderRadius: "18px",
                background: "#EA4335",
                boxShadow: "0 0 24px rgba(234,67,53,0.5)",
                transform: "translate(-70px, -121px)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <span style={{ color: "#fff", fontSize: "18px" }}>@</span>
            </div>
            {/* Calendar position */}
            <div
              style={{
                position: "absolute",
                width: "36px",
                height: "36px",
                borderRadius: "18px",
                background: "#4285F4",
                boxShadow: "0 0 24px rgba(66,133,244,0.5)",
                transform: "translate(70px, -121px)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <span style={{ color: "#fff", fontSize: "18px" }}>C</span>
            </div>

            {/* Center core - Bot */}
            <div
              style={{
                width: "80px",
                height: "80px",
                borderRadius: "40px",
                background: "linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #ea580c 100%)",
                boxShadow: "0 0 50px rgba(251,146,60,0.6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2zM7.5 13a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm9 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z"
                  fill="#1a1a2e"
                />
              </svg>
            </div>
          </div>
        </div>
      </div>
    ),
    {
      ...size,
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
