"use client";

import { Button } from "@/components/ui/button";
import { CardTitle, CardDescription } from "@/components/ui/card";
import { ArrowRight, Moon, Code, GitPullRequest, Sparkles } from "lucide-react";
import { useOnboarding } from "@/hooks/useOnboarding";
import { useAuth } from "@/hooks/useAuth";

export function WelcomeStep() {
  const { nextStep } = useOnboarding();
  const { user } = useAuth();

  const firstName = user?.full_name?.split(" ")[0] || "there";

  const handleGetStarted = () => {
    console.log("Get Started clicked, calling nextStep...");
    nextStep();
    console.log("nextStep called");
  };

  return (
    <div className="space-y-6 text-center">
      {/* Welcome header */}
      <div className="space-y-3">
        <CardTitle className="text-2xl sm:text-3xl leading-tight">
          Hey {firstName}!<br />
          Ready to ship while you sleep?
        </CardTitle>
        <CardDescription className="text-base">
          Let&apos;s get you set up in under 2 minutes.
        </CardDescription>
      </div>

      {/* How it works - visual steps */}
      <div className="grid gap-3 text-left">
        <StepPreview
          number={1}
          icon={<Code className="h-4 w-4" />}
          title="Describe what to build"
          description="Tell us what feature you want in plain English"
        />
        <StepPreview
          number={2}
          icon={<Moon className="h-4 w-4" />}
          title="Go to sleep"
          description="Agents work through the night writing code"
        />
        <StepPreview
          number={3}
          icon={<GitPullRequest className="h-4 w-4" />}
          title="Wake up to a PR"
          description="Review and merge your completed feature"
        />
      </div>

      {/* Value proposition */}
      <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground py-2">
        <div className="flex items-center gap-1">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          <span>Your time: 5 min</span>
        </div>
        <div className="h-3 w-px bg-border" />
        <div>AI work: 8 hours</div>
        <div className="h-3 w-px bg-border" />
        <div>Result: Feature shipped</div>
      </div>

      {/* CTA */}
      <Button size="lg" onClick={handleGetStarted} className="w-full">
        Let&apos;s Get Started
        <ArrowRight className="ml-2 h-5 w-5" />
      </Button>
    </div>
  );
}

function StepPreview({
  number,
  icon,
  title,
  description,
}: {
  number: number;
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-sm font-semibold">
        {number}
      </div>
      <div className="space-y-0.5 min-w-0">
        <div className="flex items-center gap-1.5 font-medium text-sm">
          {icon}
          {title}
        </div>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
