"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Hammer,
  FlaskConical,
  Rocket,
  CheckCircle2,
  User,
  GitPullRequest,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  PhaseInstructionsPanel,
  DoneCriterion,
} from "./PhaseInstructionsPanel";
import { SimpleFeedbackArrow } from "./FeedbackLoopArrow";
import { cn } from "@/lib/utils";

// Phase data from the actual codebase
interface JourneyPhase {
  id: string;
  phaseId: string;
  boardColumn: string;
  name: string;
  icon: React.ReactNode;
  duration: number; // seconds to display this phase
  agentRole: string;
  phaseInstructions: string[];
  doneCriteria: DoneCriterion[];
  canLoopBackTo?: string[];
  artifacts: { type: string; label: string; status: string }[];
}

const journeyPhases: JourneyPhase[] = [
  {
    id: "requirements",
    phaseId: "PHASE_REQUIREMENTS",
    boardColumn: "Analyzing",
    name: "Requirements",
    icon: <Search className="h-5 w-5" />,
    duration: 5,
    agentRole: "Architect",
    phaseInstructions: [
      "Read the PRD carefully",
      "Extract functional requirements",
      "Identify system components",
      "Create implementation tasks",
    ],
    doneCriteria: [
      {
        label: "Requirements extracted",
        completed: false,
        animationDelay: 1000,
      },
      {
        label: "Components identified",
        completed: false,
        animationDelay: 2500,
      },
      { label: "Tasks created", completed: false, animationDelay: 4000 },
    ],
    artifacts: [
      { type: "task", label: "JWT middleware", status: "pending" },
      { type: "task", label: "Login endpoint", status: "pending" },
      { type: "task", label: "Signup endpoint", status: "pending" },
    ],
  },
  {
    id: "implementation",
    phaseId: "PHASE_IMPLEMENTATION",
    boardColumn: "Building",
    name: "Implementation",
    icon: <Hammer className="h-5 w-5" />,
    duration: 8,
    agentRole: "Developer",
    phaseInstructions: [
      "Move ticket to building status",
      "Implement core component logic",
      "Write minimum 3 test cases",
      "If bugs found → spawn fix task",
    ],
    doneCriteria: [
      { label: "Status = building", completed: false, animationDelay: 500 },
      { label: "Code files created", completed: false, animationDelay: 2500 },
      { label: "3+ tests written", completed: false, animationDelay: 5000 },
      { label: "Tests passing", completed: false, animationDelay: 7000 },
    ],
    canLoopBackTo: ["requirements"],
    artifacts: [
      { type: "agent", label: "Agent-Dev-1", status: "active" },
      { type: "agent", label: "Agent-Dev-2", status: "active" },
    ],
  },
  {
    id: "testing",
    phaseId: "PHASE_TESTING",
    boardColumn: "Testing",
    name: "Testing",
    icon: <FlaskConical className="h-5 w-5" />,
    duration: 6,
    agentRole: "QA Engineer",
    phaseInstructions: [
      "Run integration tests",
      "Validate against requirements",
      "If PASS → create deploy task",
      "If FAIL → spawn fix task",
    ],
    doneCriteria: [
      {
        label: "Integration tests run",
        completed: false,
        animationDelay: 1500,
      },
      {
        label: "Requirements validated",
        completed: false,
        animationDelay: 3000,
      },
      { label: "All tests passing", completed: false, animationDelay: 5000 },
    ],
    canLoopBackTo: ["implementation"],
    artifacts: [{ type: "test", label: "24/24 passing", status: "complete" }],
  },
  {
    id: "deployment",
    phaseId: "PHASE_DEPLOYMENT",
    boardColumn: "Deploying",
    name: "Deployment",
    icon: <Rocket className="h-5 w-5" />,
    duration: 4,
    agentRole: "DevOps",
    phaseInstructions: [
      "Verify all tests passing",
      "Deploy to production",
      "Verify deployment health",
      "Enable monitoring",
    ],
    doneCriteria: [
      {
        label: "Deployed successfully",
        completed: false,
        animationDelay: 1500,
      },
      { label: "Health check passed", completed: false, animationDelay: 2500 },
      { label: "Monitoring enabled", completed: false, animationDelay: 3500 },
    ],
    artifacts: [{ type: "pr", label: "PR #147 merged", status: "complete" }],
  },
  {
    id: "done",
    phaseId: "PHASE_DONE",
    boardColumn: "Done",
    name: "Complete",
    icon: <CheckCircle2 className="h-5 w-5" />,
    duration: 4,
    agentRole: "—",
    phaseInstructions: ["Component successfully completed."],
    doneCriteria: [
      { label: "Component in production", completed: true, animationDelay: 0 },
    ],
    artifacts: [],
  },
];

interface TicketJourneyProps {
  autoPlay?: boolean;
  speed?: "slow" | "normal" | "fast";
  showPhaseInstructions?: boolean;
  showDoneCriteria?: boolean;
  showFeedbackLoops?: boolean;
  className?: string;
}

export function TicketJourney({
  autoPlay = true,
  speed = "normal",
  showPhaseInstructions = true,
  showFeedbackLoops = true,
  className,
}: TicketJourneyProps) {
  const [currentPhaseIndex, setCurrentPhaseIndex] = useState(0);
  const [phaseProgress, setPhaseProgress] = useState(0);
  const [completedCriteria, setCompletedCriteria] = useState<Set<string>>(
    new Set(),
  );
  const [showFeedbackLoop, setShowFeedbackLoop] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  const speedMultiplier = speed === "slow" ? 1.5 : speed === "fast" ? 0.5 : 1;

  const currentPhase = journeyPhases[currentPhaseIndex];

  // Reset animation
  const resetAnimation = useCallback(() => {
    setCurrentPhaseIndex(0);
    setPhaseProgress(0);
    setCompletedCriteria(new Set());
    setShowFeedbackLoop(false);
    setElapsedTime(0);
    setIsComplete(false);
  }, []);

  // Progress through phases
  useEffect(() => {
    if (!autoPlay) return;

    const phaseDuration = currentPhase.duration * 1000 * speedMultiplier;
    const progressInterval = 50;

    const timer = setInterval(() => {
      setPhaseProgress((prev) => {
        const newProgress = prev + (progressInterval / phaseDuration) * 100;

        // Update elapsed time
        setElapsedTime((prevTime) => prevTime + progressInterval);

        // Check for done criteria completion
        currentPhase.doneCriteria.forEach((criterion, i) => {
          const criterionTime = criterion.animationDelay * speedMultiplier;
          if (
            (newProgress / 100) * phaseDuration >= criterionTime &&
            !completedCriteria.has(`${currentPhase.id}-${i}`)
          ) {
            setCompletedCriteria((prev) =>
              new Set(prev).add(`${currentPhase.id}-${i}`),
            );
          }
        });

        // Show feedback loop in testing phase at ~60%
        if (
          currentPhase.id === "testing" &&
          newProgress > 40 &&
          newProgress < 50 &&
          showFeedbackLoops
        ) {
          setShowFeedbackLoop(true);
          setTimeout(() => setShowFeedbackLoop(false), 2000);
        }

        if (newProgress >= 100) {
          // Move to next phase or restart
          if (currentPhaseIndex < journeyPhases.length - 1) {
            setCurrentPhaseIndex((prev) => prev + 1);
            return 0;
          } else {
            setIsComplete(true);
            setTimeout(resetAnimation, 3000);
            return 100;
          }
        }
        return newProgress;
      });
    }, progressInterval);

    return () => clearInterval(timer);
  }, [
    autoPlay,
    currentPhase,
    currentPhaseIndex,
    speedMultiplier,
    showFeedbackLoops,
    completedCriteria,
    resetAnimation,
  ]);

  const formatTime = (ms: number) => {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };

  return (
    <div className={cn("w-full", className)}>
      {/* Ticket Card */}
      <motion.div
        className="mx-auto mb-8 max-w-md rounded-lg border border-border bg-card p-4"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded bg-primary/10">
              <GitPullRequest className="h-4 w-4 text-primary" />
            </div>
            <div>
              <div className="font-semibold text-foreground">
                Add user authentication
              </div>
              <div className="text-xs text-muted-foreground">FEAT-147</div>
            </div>
          </div>
          <div className="font-mono text-sm text-success">
            {formatTime(elapsedTime)}
          </div>
        </div>
      </motion.div>

      {/* Phase Rail */}
      <div className="relative mb-8">
        {/* Connection Line - behind nodes, centered vertically (h-16 nodes = 64px, center at 32px = top-8) */}
        <div className="absolute left-8 right-8 top-8 z-0 h-0.5 bg-border" />

        {/* Progress Line - behind nodes */}
        <motion.div
          className="absolute left-8 top-8 z-0 h-0.5 bg-primary"
          style={{ maxWidth: "calc(100% - 4rem)" }}
          initial={{ width: "0%" }}
          animate={{
            width: `${((currentPhaseIndex + phaseProgress / 100) / (journeyPhases.length - 1)) * 100}%`,
          }}
          transition={{ duration: 0.3 }}
        />

        {/* Phase Nodes */}
        <div className="relative flex justify-between">
          {journeyPhases.map((phase, index) => {
            const isActive = index === currentPhaseIndex;
            const isComplete = index < currentPhaseIndex;
            const isPending = index > currentPhaseIndex;

            return (
              <div key={phase.id} className="flex flex-col items-center">
                {/* Node - solid backgrounds so line appears behind */}
                <motion.div
                  className={cn(
                    "relative z-10 flex h-16 w-16 items-center justify-center rounded-xl border-2 bg-background transition-all duration-300",
                    isComplete && "border-primary",
                    isActive && "border-primary",
                    isPending && "border-border",
                  )}
                  animate={isActive ? { scale: [1, 1.05, 1] } : {}}
                  transition={{
                    duration: 2,
                    repeat: isActive ? Infinity : 0,
                    ease: "easeInOut",
                  }}
                >
                  <div
                    className={cn(
                      "transition-colors duration-300",
                      isComplete && "text-primary",
                      isActive && "text-primary",
                      isPending && "text-muted-foreground",
                    )}
                  >
                    {phase.icon}
                  </div>

                  {/* Pulse rings for active phase */}
                  {isActive && (
                    <>
                      <motion.div
                        className="absolute inset-0 rounded-xl border-2 border-primary"
                        animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                      />
                      <motion.div
                        className="absolute inset-0 rounded-xl border-2 border-primary"
                        animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
                        transition={{
                          duration: 1.5,
                          repeat: Infinity,
                          delay: 0.5,
                        }}
                      />
                    </>
                  )}

                  {/* Completion checkmark */}
                  {isComplete && (
                    <motion.div
                      className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-primary"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{
                        type: "spring",
                        stiffness: 500,
                        damping: 25,
                      }}
                    >
                      <CheckCircle2 className="h-3 w-3 text-primary-foreground" />
                    </motion.div>
                  )}
                </motion.div>

                {/* Phase Label */}
                <div className="mt-3 text-center">
                  <div
                    className={cn(
                      "text-sm font-medium transition-colors duration-300",
                      isActive && "text-primary",
                      isComplete && "text-primary",
                      isPending && "text-muted-foreground",
                    )}
                  >
                    {phase.boardColumn}
                  </div>
                  {isActive && phase.agentRole !== "—" && (
                    <motion.div
                      className="mt-1"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                    >
                      <Badge variant="secondary" className="text-xs">
                        <User className="mr-1 h-3 w-3" />
                        {phase.agentRole}
                      </Badge>
                    </motion.div>
                  )}
                </div>

                {/* Feedback loop indicator */}
                {phase.id === "testing" && showFeedbackLoop && (
                  <SimpleFeedbackArrow
                    show={showFeedbackLoop}
                    className="absolute -left-8 top-8"
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Separator */}
      {showPhaseInstructions && <Separator className="mx-auto mb-6 max-w-lg" />}

      {/* Phase Instructions Panel */}
      {showPhaseInstructions && (
        <div className="mx-auto max-w-lg">
          <PhaseInstructionsPanel
            phaseName={currentPhase.name}
            phaseEmoji={
              currentPhase.id === "requirements"
                ? "🔍"
                : currentPhase.id === "implementation"
                  ? "🔨"
                  : currentPhase.id === "testing"
                    ? "🧪"
                    : currentPhase.id === "deployment"
                      ? "🚀"
                      : "✅"
            }
            instructions={currentPhase.phaseInstructions}
            doneCriteria={currentPhase.doneCriteria.map((criterion, i) => ({
              ...criterion,
              completed: completedCriteria.has(`${currentPhase.id}-${i}`),
            }))}
            isActive={!isComplete}
          />
        </div>
      )}

      {/* Completion Stats */}
      <AnimatePresence>
        {isComplete && (
          <motion.div
            className="mx-auto mt-6 max-w-md rounded-lg border border-border bg-card p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <div className="mb-2 text-center text-lg font-semibold text-success">
              Component Complete
            </div>
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-xl font-bold text-foreground">
                  {formatTime(elapsedTime)}
                </div>
                <div className="text-xs text-muted-foreground">Total Time</div>
              </div>
              <div>
                <div className="text-xl font-bold text-foreground">5</div>
                <div className="text-xs text-muted-foreground">Tasks</div>
              </div>
              <div>
                <div className="text-xl font-bold text-foreground">1</div>
                <div className="text-xs text-muted-foreground">Bug Fixed</div>
              </div>
              <div>
                <div className="text-xl font-bold text-foreground">24</div>
                <div className="text-xs text-muted-foreground">Tests</div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
