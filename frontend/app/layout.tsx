import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import "xterm/css/xterm.css"
import { QueryProvider } from "@/providers/QueryProvider"
import { WebSocketProvider } from "@/providers/WebSocketProvider"
import { StoreProvider } from "@/providers/StoreProvider"
import { ThemeProvider } from "@/providers/ThemeProvider"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "OmoiOS Dashboard",
  description: "Multi-agent orchestration system dashboard",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <QueryProvider>
            <WebSocketProvider>
              <StoreProvider>
                {children}
              </StoreProvider>
            </WebSocketProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}

