import type { Metadata } from "next"
import { Inter, JetBrains_Mono } from "next/font/google"
import "./globals.css"
import "xterm/css/xterm.css"
import { QueryProvider } from "@/providers/QueryProvider"
import { WebSocketProvider } from "@/providers/WebSocketProvider"
import { StoreProvider } from "@/providers/StoreProvider"
import { ThemeProvider } from "@/providers/ThemeProvider"
import { Toaster } from "@/components/ui/sonner"

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" })
const jetbrainsMono = JetBrains_Mono({ 
  subsets: ["latin"], 
  variable: "--font-jetbrains-mono" 
})

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
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans`}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <QueryProvider>
            <WebSocketProvider>
              <StoreProvider>
                {children}
                <Toaster />
              </StoreProvider>
            </WebSocketProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}

