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
import { PostHogProvider } from "@/providers/PostHogProvider"
import { Toaster } from "@/components/ui/sonner"

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" })
const jetbrainsMono = JetBrains_Mono({ 
  subsets: ["latin"], 
  variable: "--font-jetbrains-mono" 
})

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://omoios.dev"

export const metadata: Metadata = {
  title: {
    default: "OmoiOS - Go to sleep. Wake up to finished features.",
    template: "%s | OmoiOS",
  },
  description:
    "AI agents that build while you rest. Deploy autonomous agents that ship features, fix bugs, and handle complex workflows overnight. Wake up to progress.",
  keywords: [
    "AI agents",
    "autonomous coding",
    "AI developer tools",
    "automated software development",
    "overnight automation",
    "AI pair programming",
    "agent orchestration",
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
    title: "Go to sleep. Wake up to finished features.",
    description:
      "AI agents that build while you rest. Deploy autonomous agents that ship features, fix bugs, and handle complex workflows overnight.",
    // images handled automatically by app/opengraph-image.tsx
  },
  twitter: {
    card: "summary_large_image",
    title: "Go to sleep. Wake up to finished features.",
    description:
      "AI agents that build while you rest. Ship features overnight with autonomous agents.",
    // images handled automatically by app/twitter-image.tsx
    creator: "@TheGeodexes",
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
        <PostHogProvider>
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
        </PostHogProvider>
      </body>
    </html>
  )
}

