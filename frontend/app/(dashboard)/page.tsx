import { redirect } from "next/navigation";

// Dashboard route group's index redirects to /command
// The actual command center lives at (app)/command/page.tsx
export default function DashboardIndexPage() {
  redirect("/command");
}
