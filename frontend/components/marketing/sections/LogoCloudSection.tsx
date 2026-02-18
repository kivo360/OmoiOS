"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const logos = [
  { name: "GitHub", icon: GitHubIcon },
  { name: "GitLab", icon: GitLabIcon, comingSoon: true },
  { name: "VS Code", icon: VSCodeIcon },
  { name: "Anthropic", icon: AnthropicIcon },
  { name: "OpenAI", icon: OpenAIIcon },
  { name: "Linear", icon: LinearIcon },
];

interface LogoCloudSectionProps {
  className?: string;
}

export function LogoCloudSection({ className }: LogoCloudSectionProps) {
  return (
    <section className={cn("bg-landing-bg-muted py-12", className)}>
      <div className="container mx-auto px-4">
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mb-8 text-center text-xs font-medium uppercase tracking-widest text-landing-text-subtle"
        >
          Integrates with your stack
        </motion.p>

        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-center gap-8 md:gap-12">
          {logos.map((logo, i) => (
            <motion.div
              key={logo.name}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="group relative flex items-center gap-2"
            >
              <logo.icon className="h-6 w-6 text-landing-text-subtle transition-colors group-hover:text-landing-text" />
              <span className="text-sm font-medium text-landing-text-subtle transition-colors group-hover:text-landing-text">
                {logo.name}
              </span>
              {logo.comingSoon && (
                <span className="absolute -right-2 -top-2 rounded bg-landing-accent/10 px-1.5 py-0.5 text-[8px] font-medium uppercase text-landing-accent">
                  Soon
                </span>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// Icon Components
function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
    </svg>
  );
}

function GitLabIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M23.955 13.587l-1.342-4.135-2.664-8.189c-.135-.423-.73-.423-.867 0L16.418 9.45H7.582L4.918 1.263c-.135-.423-.73-.423-.867 0L1.386 9.452.044 13.587c-.1.306.019.64.281.833l11.654 8.47 11.654-8.47c.262-.193.382-.527.282-.833z" />
    </svg>
  );
}

function VSCodeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.583.063a1.5 1.5 0 00-1.032.392L6.978 9.26l-4.416-3.35a1 1 0 00-1.27.057l-.9.822a1 1 0 00-.003 1.474l3.839 3.489-3.84 3.49a1 1 0 00.003 1.474l.9.822a1 1 0 001.27.057l4.416-3.35 9.573 8.805a1.5 1.5 0 002.417-1.181V1.245a1.5 1.5 0 00-1.385-1.182zm-.083 4.234v15.406l-8.084-7.703 8.084-7.703z" />
    </svg>
  );
}

function AnthropicIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.304 3.541h-3.773l6.696 16.918h3.773l-6.696-16.918zm-10.608 0l-6.696 16.918h3.883l1.41-3.727h6.638l1.41 3.727h3.883L10.528 3.541H6.696zm.888 10.012l2.128-5.621 2.128 5.621H7.584z" />
    </svg>
  );
}

function OpenAIIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.282 9.821a5.985 5.985 0 00-.516-4.91 6.046 6.046 0 00-6.51-2.9A6.065 6.065 0 0012 0C9.626 0 7.454 1.32 6.294 3.406a5.984 5.984 0 00-4.002 2.879 6.062 6.062 0 00.752 7.117 5.985 5.985 0 00.516 4.91 6.048 6.048 0 006.51 2.9A6.04 6.04 0 0012 24c2.374 0 4.546-1.32 5.706-3.406a5.98 5.98 0 004.002-2.879 6.053 6.053 0 00-.752-7.117zM12 22.003c-1.244 0-2.442-.418-3.418-1.187l.171-.097 5.674-3.278a.917.917 0 00.463-.797V10.15l2.398 1.385a.085.085 0 01.046.066v6.625c-.002 2.08-1.69 3.777-3.767 3.777zM3.635 17.955a3.735 3.735 0 01-.445-2.52l.17.102 5.675 3.278a.925.925 0 00.927 0l6.93-4.001v2.769a.083.083 0 01-.033.072l-5.737 3.312c-1.801 1.04-4.099.423-5.138-1.378a3.77 3.77 0 01-.35-.634zM2.35 7.977a3.746 3.746 0 011.955-1.648v6.752a.916.916 0 00.463.796l6.93 4.001-2.399 1.385a.084.084 0 01-.078.007L3.484 16a3.78 3.78 0 01-1.377-5.159c.194-.385.435-.744.718-1.067zm16.518 3.82l-6.93-4.002 2.398-1.385a.083.083 0 01.078-.007l5.737 3.312a3.777 3.777 0 01-.659 6.828v-6.75a.924.924 0 00-.463-.796zm2.386-2.52l-.17-.102-5.675-3.278a.925.925 0 00-.927 0l-6.93 4.001V7.13a.084.084 0 01.033-.072l5.737-3.312a3.778 3.778 0 015.488 4.1zM8.355 12.852L5.957 11.47a.083.083 0 01-.046-.066V4.78a3.777 3.777 0 016.223-2.892l-.17.097-5.675 3.278a.917.917 0 00-.464.797v6.792zm1.302-2.386l3.086-1.782 3.086 1.782v3.565l-3.086 1.782-3.086-1.782V10.466z" />
    </svg>
  );
}

function LinearIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M3.024 10.13A9.79 9.79 0 010 3.009a1.5 1.5 0 011.5-1.5 9.79 9.79 0 017.121 3.024l5.878 5.878a9.79 9.79 0 013.024 7.121 1.5 1.5 0 01-1.5 1.5 9.79 9.79 0 01-7.121-3.024l-5.878-5.878zm.678 2.797a7.282 7.282 0 002.298 3.075 7.282 7.282 0 003.075 2.298L3.702 12.927zm6.398 6.398a7.282 7.282 0 003.075 2.298 7.282 7.282 0 002.298 3.075L10.1 19.325zm7.6-7.6a7.282 7.282 0 00-2.298-3.075 7.282 7.282 0 00-3.075-2.298l5.373 5.373z" />
    </svg>
  );
}
