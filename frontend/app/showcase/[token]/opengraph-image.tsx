import { ImageResponse } from "next/og";

export const runtime = "edge";

export const alt = "OmoiOS Showcase";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000";

export default async function Image({ params }: { params: { token: string } }) {
  const montserratRegular = fetch(
    new URL("../../../public/fonts/Montserrat-Regular.ttf", import.meta.url),
  ).then((res) => res.arrayBuffer());

  const montserratLight = fetch(
    new URL("../../../public/fonts/Montserrat-Light.ttf", import.meta.url),
  ).then((res) => res.arrayBuffer());

  // Fetch showcase data
  let title = "Spec Showcase";
  let taskCount = 0;
  let tasksCompleted = 0;
  let reqCount = 0;

  try {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/public/showcase/${params.token}`,
    );
    if (res.ok) {
      const data = await res.json();
      title = data.title;
      taskCount = data.stats.task_count;
      tasksCompleted = data.stats.tasks_completed;
      reqCount = data.stats.requirement_count;
    }
  } catch {
    // Use defaults
  }

  return new ImageResponse(
    <div
      style={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        background:
          "linear-gradient(145deg, #2d2618 0%, #1a150d 50%, #0f0c08 100%)",
        padding: "60px 80px",
        position: "relative",
      }}
    >
      {/* Golden gradient overlay */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background:
            "radial-gradient(ellipse 80% 60% at 20% 40%, rgba(255,200,50,0.1) 0%, transparent 50%)",
          display: "flex",
        }}
      />

      {/* OmoiOS badge */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          marginBottom: "32px",
        }}
      >
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
          omoios.dev/showcase
        </div>
      </div>

      {/* Title */}
      <div
        style={{
          display: "flex",
          fontSize: "52px",
          fontFamily: "Montserrat",
          fontWeight: 400,
          color: "#ffffff",
          lineHeight: 1.15,
          marginBottom: "40px",
          maxWidth: "900px",
        }}
      >
        {title.length > 60 ? title.slice(0, 57) + "..." : title}
      </div>

      {/* Stats row */}
      <div
        style={{
          display: "flex",
          gap: "48px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span
            style={{
              fontSize: "42px",
              fontFamily: "Montserrat",
              fontWeight: 400,
              background:
                "linear-gradient(135deg, #FFE78A 0%, #FFD04A 50%, #FF8A2A 100%)",
              backgroundClip: "text",
              color: "transparent",
            }}
          >
            {reqCount}
          </span>
          <span
            style={{
              fontSize: "16px",
              fontFamily: "Montserrat",
              fontWeight: 300,
              color: "rgba(255,230,200,0.5)",
            }}
          >
            Requirements
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span
            style={{
              fontSize: "42px",
              fontFamily: "Montserrat",
              fontWeight: 400,
              background:
                "linear-gradient(135deg, #FFE78A 0%, #FFD04A 50%, #FF8A2A 100%)",
              backgroundClip: "text",
              color: "transparent",
            }}
          >
            {tasksCompleted}/{taskCount}
          </span>
          <span
            style={{
              fontSize: "16px",
              fontFamily: "Montserrat",
              fontWeight: 300,
              color: "rgba(255,230,200,0.5)",
            }}
          >
            Tasks Completed
          </span>
        </div>
      </div>

      {/* Bottom branding */}
      <div
        style={{
          position: "absolute",
          bottom: "40px",
          right: "60px",
          display: "flex",
          alignItems: "center",
          gap: "12px",
        }}
      >
        <span
          style={{
            fontSize: "16px",
            fontFamily: "Montserrat",
            fontWeight: 300,
            color: "rgba(255,230,200,0.4)",
          }}
        >
          Built with
        </span>
        <span
          style={{
            fontSize: "18px",
            fontFamily: "Montserrat",
            fontWeight: 400,
            background:
              "linear-gradient(135deg, #FFE78A 0%, #FFD04A 50%, #FF8A2A 100%)",
            backgroundClip: "text",
            color: "transparent",
          }}
        >
          OmoiOS
        </span>
      </div>
    </div>,
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
    },
  );
}
