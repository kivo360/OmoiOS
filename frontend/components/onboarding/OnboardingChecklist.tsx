"use client";

import { cn } from "@/lib/utils";
import { Check, Circle, Loader2, Lock } from "lucide-react";
import {
  useOnboarding,
  type OnboardingStep,
  type ChecklistItemId,
} from "@/hooks/useOnboarding";

export interface ChecklistItem {
  id: string;
  label: string;
  description?: string;
  step?: OnboardingStep; // If tied to an onboarding step
  isPostOnboarding?: boolean; // Post-onboarding tasks
}

const CHECKLIST_ITEMS: ChecklistItem[] = [
  // Onboarding steps
  {
    id: "welcome",
    label: "Get started",
    description: "Learn what Omoios can do",
    step: "welcome",
  },
  {
    id: "github",
    label: "Connect GitHub",
    description: "Link your repositories",
    step: "github",
  },
  {
    id: "repo",
    label: "Select repository",
    description: "Choose your first project",
    step: "repo",
  },
  {
    id: "first-spec",
    label: "Describe your feature",
    description: "Tell the agent what to build",
    step: "first-spec",
  },
  {
    id: "plan",
    label: "Choose your plan",
    description: "Free or paid options",
    step: "plan",
  },
  // Post-onboarding tasks
  {
    id: "watch-agent",
    label: "Watch agent work",
    description: "See your feature being built",
    isPostOnboarding: true,
  },
  {
    id: "review-pr",
    label: "Review your first PR",
    description: "Agent creates a pull request",
    isPostOnboarding: true,
  },
  {
    id: "invite-team",
    label: "Invite team members",
    description: "Collaborate with your team",
    isPostOnboarding: true,
  },
];

interface OnboardingChecklistProps {
  className?: string;
  showPostOnboarding?: boolean;
}

export function OnboardingChecklist({
  className,
  showPostOnboarding = true,
}: OnboardingChecklistProps) {
  const { currentStep, completedSteps, completedChecklistItems, data } =
    useOnboarding();

  // Ensure arrays and objects have defaults to prevent undefined errors
  const safeCompletedSteps = completedSteps || [];
  const safeCompletedChecklistItems = completedChecklistItems || [];
  const safeData = data || {};

  const getItemStatus = (
    item: ChecklistItem,
  ): "completed" | "current" | "locked" | "pending" => {
    // Check if explicitly completed via completedChecklistItems
    if (safeCompletedChecklistItems.includes(item.id as ChecklistItemId)) {
      return "completed";
    }

    // Post-onboarding items
    if (item.isPostOnboarding) {
      if (item.id === "watch-agent" && safeData.firstSpecId) {
        // Available once spec is submitted, check if it's running
        if (safeData.firstSpecStatus === "running") {
          return "current";
        }
        if (safeData.firstSpecStatus === "completed") {
          return "completed";
        }
        return "pending";
      }
      if (item.id === "review-pr") {
        // Available after agent completes
        if (safeData.firstSpecStatus === "completed") {
          return "pending";
        }
        return "locked";
      }
      if (item.id === "invite-team") {
        // Available after onboarding wizard steps are done
        if (currentStep === "complete") {
          return "pending";
        }
        return "locked";
      }
      return "locked";
    }

    // Onboarding steps
    if (!item.step) return "pending";

    if (safeCompletedSteps.includes(item.step)) {
      return "completed";
    }
    if (currentStep === item.step) {
      return "current";
    }

    // Check if this step is before or after current
    const steps: OnboardingStep[] = [
      "welcome",
      "github",
      "repo",
      "first-spec",
      "plan",
      "complete",
    ];
    const currentIndex = steps.indexOf(currentStep);
    const itemIndex = steps.indexOf(item.step);

    if (itemIndex < currentIndex) {
      return "completed";
    }

    return "locked";
  };

  const items = showPostOnboarding
    ? CHECKLIST_ITEMS
    : CHECKLIST_ITEMS.filter((item) => !item.isPostOnboarding);

  return (
    <div className={cn("space-y-1", className)}>
      <h3 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wide">
        Setup Checklist
      </h3>
      <div className="space-y-1">
        {items.map((item, index) => {
          const status = getItemStatus(item);
          const showDivider =
            item.isPostOnboarding &&
            !CHECKLIST_ITEMS[index - 1]?.isPostOnboarding;

          return (
            <div key={item.id}>
              {showDivider && (
                <div className="my-3 border-t border-dashed pt-3">
                  <span className="text-xs text-muted-foreground">
                    After onboarding
                  </span>
                </div>
              )}
              <ChecklistItemRow item={item} status={status} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface ChecklistItemRowProps {
  item: ChecklistItem;
  status: "completed" | "current" | "locked" | "pending";
}

function ChecklistItemRow({ item, status }: ChecklistItemRowProps) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 p-2 rounded-lg transition-colors",
        status === "current" && "bg-primary/5 border border-primary/20",
        status === "locked" && "opacity-50",
      )}
    >
      {/* Status icon */}
      <div className="mt-0.5 shrink-0">
        {status === "completed" && (
          <div className="h-5 w-5 rounded-full bg-green-500 flex items-center justify-center">
            <Check className="h-3 w-3 text-white" />
          </div>
        )}
        {status === "current" && (
          <div className="h-5 w-5 rounded-full bg-primary flex items-center justify-center">
            <Loader2 className="h-3 w-3 text-primary-foreground animate-spin" />
          </div>
        )}
        {status === "pending" && (
          <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30 flex items-center justify-center">
            <Circle className="h-2 w-2 text-muted-foreground/30" />
          </div>
        )}
        {status === "locked" && (
          <div className="h-5 w-5 rounded-full bg-muted flex items-center justify-center">
            <Lock className="h-3 w-3 text-muted-foreground" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-sm font-medium",
            status === "completed" && "text-muted-foreground line-through",
            status === "locked" && "text-muted-foreground",
          )}
        >
          {item.label}
        </p>
        {item.description && (
          <p className="text-xs text-muted-foreground truncate">
            {item.description}
          </p>
        )}
      </div>
    </div>
  );
}

export { CHECKLIST_ITEMS };
