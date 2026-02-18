import { notFound } from "next/navigation";
import {
  Star,
  GitPullRequest,
  ExternalLink,
  BarChart3,
  ListChecks,
  Shield,
} from "lucide-react";
import type { Metadata } from "next";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000";

interface ShowcaseData {
  title: string;
  description: string | null;
  stats: {
    requirement_count: number;
    task_count: number;
    tasks_completed: number;
    test_coverage: number;
  };
  project_name: string | null;
  pull_request_url: string | null;
  pull_request_number: number | null;
  share_view_count: number;
}

async function getShowcaseData(token: string): Promise<ShowcaseData | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/public/showcase/${token}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ token: string }>;
}): Promise<Metadata> {
  const { token } = await params;
  const data = await getShowcaseData(token);

  if (!data) {
    return { title: "Showcase — OmoiOS" };
  }

  return {
    title: `${data.title} — OmoiOS Showcase`,
    description:
      data.description ||
      `${data.stats.task_count} tasks automated with OmoiOS`,
    openGraph: {
      title: `${data.title} — Built with OmoiOS`,
      description:
        data.description ||
        `${data.stats.task_count} tasks automated, ${data.stats.tasks_completed} completed`,
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: `${data.title} — Built with OmoiOS`,
      description:
        data.description ||
        `${data.stats.task_count} tasks automated with OmoiOS`,
    },
  };
}

export default async function ShowcasePage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  const data = await getShowcaseData(token);

  if (!data) notFound();

  const { stats } = data;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#2d2618] via-[#1a150d] to-[#0f0c08] text-white">
      <div className="mx-auto max-w-2xl px-6 py-16">
        {/* Header */}
        <div className="mb-2 text-sm font-medium text-amber-400/80">
          OmoiOS Showcase
        </div>
        <h1 className="text-3xl font-bold tracking-tight">{data.title}</h1>
        {data.description && (
          <p className="mt-3 text-base text-white/60 leading-relaxed">
            {data.description}
          </p>
        )}
        {data.project_name && (
          <p className="mt-1 text-sm text-white/40">
            Project: {data.project_name}
          </p>
        )}

        {/* Stats cards */}
        <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            icon={<ListChecks className="h-5 w-5 text-amber-400" />}
            value={stats.requirement_count}
            label="Requirements"
          />
          <StatCard
            icon={<BarChart3 className="h-5 w-5 text-amber-400" />}
            value={stats.task_count}
            label="Tasks"
          />
          <StatCard
            icon={<BarChart3 className="h-5 w-5 text-green-400" />}
            value={stats.tasks_completed}
            label="Completed"
          />
          <StatCard
            icon={<Shield className="h-5 w-5 text-amber-400" />}
            value={`${stats.test_coverage.toFixed(0)}%`}
            label="Coverage"
          />
        </div>

        {/* PR link */}
        {data.pull_request_url && (
          <a
            href={data.pull_request_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-8 flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 p-4 transition-colors hover:bg-white/10"
          >
            <GitPullRequest className="h-5 w-5 text-green-400" />
            <span className="flex-1 text-sm">
              Pull Request #{data.pull_request_number}
            </span>
            <ExternalLink className="h-4 w-4 text-white/40" />
          </a>
        )}

        {/* CTAs */}
        <div className="mt-12 flex flex-col gap-3 sm:flex-row">
          <a
            href="/register"
            className="inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 px-6 py-3 text-sm font-semibold text-black transition-opacity hover:opacity-90"
          >
            Try OmoiOS
          </a>
          <a
            href="https://github.com/kivo360/OmoiOS"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/20 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-white/10"
          >
            <Star className="h-4 w-4" />
            Star on GitHub
          </a>
        </div>

        {/* Footer */}
        <p className="mt-16 text-center text-xs text-white/30">
          Built with{" "}
          <a
            href="https://omoios.dev"
            className="underline hover:text-white/50"
          >
            OmoiOS
          </a>{" "}
          — spec-driven AI agents
        </p>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: number | string;
  label: string;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-4">
      <div className="mb-2">{icon}</div>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs text-white/50">{label}</p>
    </div>
  );
}
