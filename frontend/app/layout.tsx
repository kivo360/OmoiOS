import type { Metadata } from "next"
import { Inter, JetBrains_Mono } from "next/font/google"
import "./globals.css"
import "xterm/css/xterm.css"
import "katex/dist/katex.min.css"
import { QueryProvider } from "@/providers/QueryProvider"
import { WebSocketProvider } from "@/providers/WebSocketProvider"
import { StoreProvider } from "@/providers/StoreProvider"
import { ThemeProvider } from "@/providers/ThemeProvider"
import { AuthProvider } from "@/providers/AuthProvider"
import { Toaster } from "@/components/ui/sonner"

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" })
const jetbrainsMono = JetBrains_Mono({ 
  subsets: ["latin"], 
  variable: "--font-jetbrains-mono" 
})

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://omoios.com"

export const metadata: Metadata = {
  title: {
    default: "OmoiOS - AI Agent Orchestration Platform",
    template: "%s | OmoiOS",
  },
  description:
    "OmoiOS is an AI-powered multi-agent orchestration platform. Deploy autonomous agents that work while you sleep, automate complex workflows, and scale your operations with intelligent automation.",
  keywords: [
    "AI agents",
    "agent orchestration",
    "automation",
    "multi-agent systems",
    "autonomous agents",
    "workflow automation",
    "AI platform",
  ],
  authors: [{ name: "OmoiOS Team" }],
  creator: "OmoiOS",
  publisher: "OmoiOS",
  metadataBase: new URL(siteUrl),
  openGraph: {
    type: "website",
    locale: "en_US",
    url: siteUrl,
    siteName: "OmoiOS",
    title: "OmoiOS - AI Agent Orchestration Platform",
    description:
      "Deploy autonomous AI agents that work while you sleep. Automate complex workflows and scale your operations with intelligent multi-agent orchestration.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "OmoiOS - AI Agent Orchestration Platform",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "OmoiOS - AI Agent Orchestration Platform",
    description:
      "Deploy autonomous AI agents that work while you sleep. Automate complex workflows and scale your operations.",
    images: ["/og-image.png"],
    creator: "@omoios",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
    ],
    shortcut: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
  manifest: "/site.webmanifest",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans`}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <QueryProvider>
            <AuthProvider>
              <WebSocketProvider>
                <StoreProvider>
                  {children}
                  <Toaster />
                </StoreProvider>
              </WebSocketProvider>
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}

