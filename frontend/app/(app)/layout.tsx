import { MainLayout } from "@/components/layout"

export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <MainLayout>{children}</MainLayout>
}
