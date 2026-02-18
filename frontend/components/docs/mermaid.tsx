"use client";

import { useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";

interface MermaidProps {
  chart: string;
}

// Theme configurations
const darkTheme = {
  background: "#0a0a0a",
  primaryColor: "#292524",
  primaryTextColor: "#fafaf9",
  primaryBorderColor: "#f59e0b",
  secondaryColor: "#1c1917",
  secondaryTextColor: "#e7e5e4",
  secondaryBorderColor: "#78716c",
  tertiaryColor: "#171717",
  tertiaryTextColor: "#a8a29e",
  tertiaryBorderColor: "#57534e",
  lineColor: "#78716c",
  textColor: "#fafaf9",
  mainBkg: "#1c1917",
  nodeBkg: "#292524",
  nodeBorder: "#f59e0b",
  clusterBkg: "#0a0a0a",
  clusterBorder: "#f59e0b",
  edgeLabelBackground: "#1c1917",
  fontSize: "14px",
};

const lightTheme = {
  background: "#ffffff",
  primaryColor: "#fef3c7",
  primaryTextColor: "#1c1917",
  primaryBorderColor: "#d97706",
  secondaryColor: "#fffbeb",
  secondaryTextColor: "#292524",
  secondaryBorderColor: "#b45309",
  tertiaryColor: "#fefce8",
  tertiaryTextColor: "#44403c",
  tertiaryBorderColor: "#92400e",
  lineColor: "#78716c",
  textColor: "#1c1917",
  mainBkg: "#fffbeb",
  nodeBkg: "#fef3c7",
  nodeBorder: "#d97706",
  clusterBkg: "#ffffff",
  clusterBorder: "#d97706",
  edgeLabelBackground: "#fffbeb",
  fontSize: "14px",
};

// Inner component that actually renders mermaid
function MermaidRenderer({ chart, theme }: { chart: string; theme: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const renderDiagram = async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        const isDark = theme === "dark";
        const themeVars = isDark ? darkTheme : lightTheme;

        mermaid.initialize({
          startOnLoad: false,
          theme: "base",
          securityLevel: "loose",
          fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif",
          themeVariables: themeVars,
          flowchart: {
            htmlLabels: true,
            curve: "basis",
            padding: 20,
            nodeSpacing: 50,
            rankSpacing: 70,
          },
        });

        const id = `mermaid-${theme}-${Math.random().toString(36).substr(2, 9)}`;
        const { svg: renderedSvg } = await mermaid.render(id, chart);

        if (isMounted) {
          setSvg(renderedSvg);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError(
            err instanceof Error ? err.message : "Failed to render diagram",
          );
        }
      }
    };

    renderDiagram();

    return () => {
      isMounted = false;
    };
  }, [chart, theme]);

  if (error) {
    return (
      <div className="my-4 p-4 rounded-lg bg-red-500/10 border border-red-500/20">
        <p className="text-sm text-red-400 font-medium mb-2">
          Failed to render Mermaid diagram
        </p>
        <pre className="text-xs text-neutral-400 overflow-x-auto">{chart}</pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="my-4 p-4 rounded-lg bg-neutral-100 dark:bg-neutral-800/50 text-center text-sm text-neutral-500 dark:text-neutral-400">
        Loading diagram...
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="my-6 overflow-x-auto rounded-xl border border-amber-500/30 bg-white dark:bg-neutral-950 p-6 shadow-sm"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

// Wrapper that forces remount on theme change via key prop
export function Mermaid({ chart }: MermaidProps) {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="my-4 p-4 rounded-lg bg-neutral-100 dark:bg-neutral-800/50 text-center text-sm text-neutral-500 dark:text-neutral-400">
        Loading diagram...
      </div>
    );
  }

  const theme = resolvedTheme || "dark";

  // Key forces complete remount when theme changes
  return <MermaidRenderer key={theme} chart={chart} theme={theme} />;
}
