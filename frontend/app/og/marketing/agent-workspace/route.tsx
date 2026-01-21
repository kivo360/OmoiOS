import { ImageResponse } from "next/og"

export const runtime = "edge"

// Color palette - warmer tones matching main OG image
const colors = {
  bg: "#1a150d",
  bgGradient: "linear-gradient(145deg, #2d2618 0%, #1a150d 50%, #0f0c08 100%)",
  gold: "#FFD04A",
  goldSoft: "rgba(255, 208, 74, 0.70)",
  goldMuted: "rgba(255, 208, 74, 0.40)",
  green: "#50C878",
  greenSoft: "rgba(80, 200, 120, 0.85)",
  orange: "#FF8A2A",
  blue: "#60A5FA",
  cyan: "#22D3EE",
  purple: "#A78BFA",
  pink: "#F472B6",
  text: "rgba(255, 248, 235, 0.92)",
  textMuted: "rgba(255, 236, 205, 0.70)",
  textDim: "rgba(255, 236, 205, 0.50)",
  cardBg: "rgba(255, 208, 74, 0.06)",
  cardBorder: "rgba(255, 208, 74, 0.18)",
  terminalBg: "#0d0d0d",
  terminalBorder: "rgba(255, 208, 74, 0.12)",
}

function TerminalLine({
  prompt,
  command,
  output,
  highlight,
}: {
  prompt?: string
  command?: string
  output?: string
  highlight?: boolean
}) {
  if (output) {
    return (
      <div style={{ display: "flex", marginBottom: "4px" }}>
        <span
          style={{
            fontSize: "11px",
            fontFamily: "monospace",
            color: highlight ? colors.green : colors.textDim,
          }}
        >
          {output}
        </span>
      </div>
    )
  }

  return (
    <div style={{ display: "flex", marginBottom: "4px" }}>
      <span
        style={{
          fontSize: "11px",
          fontFamily: "monospace",
          color: colors.cyan,
          marginRight: "8px",
        }}
      >
        {prompt || "❯"}
      </span>
      <span
        style={{
          fontSize: "11px",
          fontFamily: "monospace",
          color: colors.text,
        }}
      >
        {command}
      </span>
    </div>
  )
}

function CodeLine({
  lineNum,
  code,
  highlight,
  added,
}: {
  lineNum: number
  code: string
  highlight?: boolean
  added?: boolean
}) {
  return (
    <div
      style={{
        display: "flex",
        background: added
          ? "rgba(80, 200, 120, 0.08)"
          : highlight
            ? "rgba(255, 208, 74, 0.06)"
            : "transparent",
        paddingLeft: "8px",
        paddingRight: "8px",
      }}
    >
      <span
        style={{
          fontSize: "10px",
          fontFamily: "monospace",
          color: colors.textDim,
          width: "28px",
          textAlign: "right",
          marginRight: "12px",
          flexShrink: 0,
        }}
      >
        {lineNum}
      </span>
      {added && (
        <span
          style={{
            fontSize: "10px",
            fontFamily: "monospace",
            color: colors.green,
            marginRight: "4px",
          }}
        >
          +
        </span>
      )}
      <span
        style={{
          fontSize: "11px",
          fontFamily: "monospace",
          color: colors.text,
          whiteSpace: "pre",
        }}
      >
        {code}
      </span>
    </div>
  )
}

function FileTreeItem({
  name,
  indent,
  isFolder,
  isOpen,
  isModified,
}: {
  name: string
  indent: number
  isFolder?: boolean
  isOpen?: boolean
  isModified?: boolean
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        paddingLeft: `${indent * 12}px`,
        marginBottom: "4px",
      }}
    >
      {isFolder ? (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
          {isOpen ? (
            <path
              d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
              stroke={colors.gold}
              strokeWidth="2"
              fill="rgba(255, 208, 74, 0.15)"
            />
          ) : (
            <path
              d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
              stroke={colors.textDim}
              strokeWidth="2"
              fill="none"
            />
          )}
        </svg>
      ) : (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
          <path
            d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
            stroke={isModified ? colors.green : colors.textDim}
            strokeWidth="2"
            fill="none"
          />
          <polyline
            points="14,2 14,8 20,8"
            stroke={isModified ? colors.green : colors.textDim}
            strokeWidth="2"
            fill="none"
          />
        </svg>
      )}
      <span
        style={{
          fontSize: "11px",
          fontFamily: "monospace",
          color: isModified ? colors.green : isFolder && isOpen ? colors.gold : colors.textMuted,
        }}
      >
        {name}
      </span>
      {isModified && (
        <span
          style={{
            fontSize: "9px",
            fontFamily: "monospace",
            color: colors.green,
          }}
        >
          M
        </span>
      )}
    </div>
  )
}

export async function GET() {
  const montserratRegular = fetch(
    new URL("../../../../public/fonts/Montserrat-Regular.ttf", import.meta.url)
  ).then((res) => res.arrayBuffer())

  const montserratLight = fetch(
    new URL("../../../../public/fonts/Montserrat-Light.ttf", import.meta.url)
  ).then((res) => res.arrayBuffer())

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          background: colors.bgGradient,
          position: "relative",
          padding: "50px 60px",
        }}
      >
        {/* Texture */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundImage:
              "radial-gradient(rgba(255, 208, 74, 0.03) 1px, transparent 1px)",
            backgroundSize: "32px 32px",
            display: "flex",
          }}
        />

        {/* Warm golden overlay - matching main OG image */}
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

        {/* Ambient glow */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              "radial-gradient(ellipse 50% 40% at 40% 55%, rgba(34, 211, 238, 0.05) 0%, transparent 60%), radial-gradient(ellipse 50% 40% at 70% 55%, rgba(80, 200, 120, 0.05) 0%, transparent 60%)",
            display: "flex",
          }}
        />

        {/* Vignette */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background:
              "radial-gradient(ellipse 120% 90% at 50% 50%, transparent 52%, rgba(0,0,0,0.5) 100%)",
            display: "flex",
          }}
        />

        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            marginBottom: "24px",
            zIndex: 1,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div
              style={{
                display: "flex",
                fontSize: "36px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: colors.text,
                marginBottom: "10px",
              }}
            >
              Full Dev Environment Access
            </div>
            <div
              style={{
                display: "flex",
                fontSize: "18px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: colors.textMuted,
              }}
            >
              Watch agents code, test, and debug in isolated sandboxes
            </div>
          </div>

          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center" }}>
            <svg
              width="36"
              height="36"
              viewBox="0 0 512 512"
              fill="none"
              style={{ marginRight: "10px" }}
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
              </g>
            </svg>
            <span
              style={{
                fontSize: "22px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: colors.text,
              }}
            >
              OmoiOS
            </span>
          </div>
        </div>

        {/* Main Content - IDE Layout */}
        <div
          style={{
            display: "flex",
            flex: 1,
            gap: "16px",
            zIndex: 1,
          }}
        >
          {/* File Tree */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              width: "180px",
              background: "rgba(0, 0, 0, 0.40)",
              borderRadius: "12px",
              padding: "14px",
              border: `1px solid ${colors.terminalBorder}`,
            }}
          >
            <div
              style={{
                display: "flex",
                fontSize: "10px",
                fontFamily: "Montserrat",
                fontWeight: 400,
                color: colors.textDim,
                textTransform: "uppercase",
                letterSpacing: "1px",
                marginBottom: "12px",
              }}
            >
              Explorer
            </div>

            <FileTreeItem name="src" indent={0} isFolder isOpen />
            <FileTreeItem name="api" indent={1} isFolder isOpen />
            <FileTreeItem name="stripe" indent={2} isFolder isOpen />
            <FileTreeItem name="webhook.ts" indent={3} isModified />
            <FileTreeItem name="checkout.ts" indent={3} isModified />
            <FileTreeItem name="types.ts" indent={3} />
            <FileTreeItem name="tests" indent={1} isFolder />
            <FileTreeItem name="utils" indent={1} isFolder />
            <FileTreeItem name="package.json" indent={0} />
            <FileTreeItem name="tsconfig.json" indent={0} />
          </div>

          {/* Code Editor */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              flex: 1,
              background: colors.terminalBg,
              borderRadius: "12px",
              border: `1px solid ${colors.terminalBorder}`,
              overflow: "hidden",
            }}
          >
            {/* Editor tabs */}
            <div
              style={{
                display: "flex",
                borderBottom: `1px solid ${colors.terminalBorder}`,
                background: "rgba(255, 208, 74, 0.03)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "10px 16px",
                  background: colors.terminalBg,
                  borderBottom: `2px solid ${colors.gold}`,
                }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
                    stroke={colors.green}
                    strokeWidth="2"
                    fill="none"
                  />
                </svg>
                <span
                  style={{
                    fontSize: "11px",
                    fontFamily: "monospace",
                    color: colors.text,
                  }}
                >
                  webhook.ts
                </span>
                <div
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "3px",
                    background: colors.green,
                  }}
                />
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "10px 16px",
                }}
              >
                <span
                  style={{
                    fontSize: "11px",
                    fontFamily: "monospace",
                    color: colors.textDim,
                  }}
                >
                  checkout.ts
                </span>
              </div>
            </div>

            {/* Code content */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                padding: "12px 0",
                flex: 1,
              }}
            >
              <CodeLine lineNum={1} code="import Stripe from 'stripe';" />
              <CodeLine lineNum={2} code="import { WebhookEvent } from './types';" />
              <CodeLine lineNum={3} code="" />
              <CodeLine lineNum={4} code="export async function handleWebhook(" highlight />
              <CodeLine lineNum={5} code="  event: Stripe.Event" highlight />
              <CodeLine lineNum={6} code="): Promise<WebhookEvent> {" highlight />
              <CodeLine lineNum={7} code="  switch (event.type) {" />
              <CodeLine lineNum={8} code="    case 'checkout.session.completed':" added />
              <CodeLine lineNum={9} code="      await updateOrderStatus(event);" added />
              <CodeLine lineNum={10} code="      await sendConfirmationEmail(event);" added />
              <CodeLine lineNum={11} code="      break;" added />
              <CodeLine lineNum={12} code="    case 'payment_intent.succeeded':" />
              <CodeLine lineNum={13} code="      await processPayment(event);" />
              <CodeLine lineNum={14} code="      break;" />
              <CodeLine lineNum={15} code="  }" />
              <CodeLine lineNum={16} code="}" />
            </div>
          </div>

          {/* Terminal */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              width: "340px",
              background: colors.terminalBg,
              borderRadius: "12px",
              border: `1px solid ${colors.terminalBorder}`,
              overflow: "hidden",
            }}
          >
            {/* Terminal header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 14px",
                borderBottom: `1px solid ${colors.terminalBorder}`,
                background: "rgba(255, 208, 74, 0.03)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <polyline
                    points="4,17 10,11 4,5"
                    stroke={colors.cyan}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <line
                    x1="12"
                    y1="19"
                    x2="20"
                    y2="19"
                    stroke={colors.cyan}
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
                <span
                  style={{
                    fontSize: "11px",
                    fontFamily: "Montserrat",
                    fontWeight: 400,
                    color: colors.text,
                  }}
                >
                  Terminal
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <div
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "3px",
                    background: colors.green,
                    boxShadow: `0 0 6px ${colors.green}`,
                  }}
                />
                <span
                  style={{
                    fontSize: "10px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.greenSoft,
                  }}
                >
                  Live
                </span>
              </div>
            </div>

            {/* Terminal content */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                padding: "12px 14px",
                flex: 1,
              }}
            >
              <TerminalLine command="npm run test:webhook" />
              <TerminalLine output="" />
              <TerminalLine output="PASS  tests/webhook.test.ts" highlight />
              <TerminalLine output="  ✓ handles checkout.session.completed" />
              <TerminalLine output="  ✓ validates webhook signature" />
              <TerminalLine output="  ✓ updates order status correctly" />
              <TerminalLine output="  ✓ sends confirmation email" />
              <TerminalLine output="" />
              <TerminalLine output="Test Suites: 1 passed, 1 total" highlight />
              <TerminalLine output="Tests:       4 passed, 4 total" highlight />
              <TerminalLine output="Time:        1.247s" />
              <TerminalLine output="" />
              <TerminalLine prompt="❯" command="git add -A && git commit" />
            </div>

            {/* Sandbox status */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 14px",
                borderTop: `1px solid ${colors.terminalBorder}`,
                background: "rgba(255, 208, 74, 0.03)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <rect
                    x="3"
                    y="3"
                    width="18"
                    height="18"
                    rx="2"
                    stroke={colors.gold}
                    strokeWidth="2"
                    fill="none"
                  />
                  <path d="M3 9h18" stroke={colors.gold} strokeWidth="2" />
                  <path d="M9 21V9" stroke={colors.gold} strokeWidth="2" />
                </svg>
                <span
                  style={{
                    fontSize: "10px",
                    fontFamily: "Montserrat",
                    fontWeight: 300,
                    color: colors.textMuted,
                  }}
                >
                  Daytona Sandbox
                </span>
              </div>
              <span
                style={{
                  fontSize: "10px",
                  fontFamily: "monospace",
                  color: colors.textDim,
                }}
              >
                sandbox-a7f3k
              </span>
            </div>
          </div>
        </div>

        {/* Bottom tagline */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginTop: "20px",
            zIndex: 1,
          }}
        >
          <div
            style={{
              display: "flex",
              background: "rgba(255, 208, 74, 0.08)",
              borderRadius: "999px",
              padding: "10px 20px",
              border: `1px solid ${colors.cardBorder}`,
            }}
          >
            <span
              style={{
                fontSize: "14px",
                fontFamily: "Montserrat",
                fontWeight: 300,
                color: colors.textMuted,
              }}
            >
              Complete transparency into agent execution
            </span>
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
