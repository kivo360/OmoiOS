import Link from "next/link"
import { Card } from "@/components/ui/card"

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-4">
      {/* Logo */}
      <Link href="/" className="mb-8 flex items-center gap-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
          <span className="text-lg font-bold text-primary-foreground">O</span>
        </div>
        <span className="text-2xl font-bold">OmoiOS</span>
      </Link>

      {/* Auth Card */}
      <Card className="w-full max-w-md p-6">
        {children}
      </Card>

      {/* Footer */}
      <footer className="mt-12 text-center text-sm text-muted-foreground">
        <p>© {new Date().getFullYear()} OmoiOS. All rights reserved.</p>
      </footer>
    </div>
  )
}
