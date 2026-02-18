"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ArrowRight,
  Sparkles,
  Clock,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { useOnboarding } from "@/hooks/useOnboarding";

const SUGGESTION_CHIPS = [
  "Add form validation to the contact form",
  "Create a dark mode toggle",
  "Add a logout button to the navbar",
  "Fix the broken link in the footer",
  "Add loading states to buttons",
  "Improve mobile navigation",
];

export function FirstSpecStep() {
  const { data, submitFirstSpec, isLoading, error, clearError, nextStep } =
    useOnboarding();
  const [specText, setSpecText] = useState(data.firstSpecText || "");

  const handleSubmit = async () => {
    if (!specText.trim()) return;
    await submitFirstSpec(specText.trim());
  };

  const handleSuggestionClick = (suggestion: string) => {
    setSpecText(suggestion);
    clearError();
  };

  const characterCount = specText.length;
  const isValidLength = characterCount >= 10 && characterCount <= 2000;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <CardTitle className="text-2xl flex items-center justify-center gap-2">
          <Sparkles className="h-6 w-6 text-primary" />
          Describe Your First Feature
        </CardTitle>
        <CardDescription>
          What should we build tonight? Start simple - you can go bigger later.
        </CardDescription>
      </div>

      {/* Selected repo context */}
      {data.selectedRepo && (
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <span>Building in</span>
          <Badge variant="secondary">{data.selectedRepo.fullName}</Badge>
        </div>
      )}

      {/* Spec input */}
      <div className="space-y-2">
        <Textarea
          placeholder="Example: Add a logout button to the navbar that clears the session and redirects to the login page..."
          value={specText}
          onChange={(e) => {
            setSpecText(e.target.value);
            if (error) clearError();
          }}
          className="min-h-[120px] resize-none"
          disabled={isLoading}
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>
            {characterCount < 10
              ? `${10 - characterCount} more characters needed`
              : "Looks good!"}
          </span>
          <span className={characterCount > 2000 ? "text-destructive" : ""}>
            {characterCount}/2000
          </span>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Suggestion chips */}
      <div className="space-y-2">
        <p className="text-sm text-muted-foreground flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          Quick starts (click to use):
        </p>
        <div className="flex flex-wrap gap-2">
          {SUGGESTION_CHIPS.map((suggestion) => (
            <Button
              key={suggestion}
              variant="outline"
              size="sm"
              onClick={() => handleSuggestionClick(suggestion)}
              className="text-xs"
              disabled={isLoading}
            >
              {suggestion}
            </Button>
          ))}
        </div>
      </div>

      {/* Usage note */}
      <div className="flex items-center justify-center gap-2 p-3 rounded-lg bg-muted/50 text-sm text-muted-foreground">
        <Clock className="h-4 w-4" />
        <span>This will use 1 of your 5 free monthly workflows</span>
      </div>

      {/* Submit button */}
      <Button
        size="lg"
        onClick={handleSubmit}
        disabled={!isValidLength || isLoading}
        className="w-full"
      >
        {isLoading ? (
          <>
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Starting Agent...
          </>
        ) : (
          <>
            Submit First Spec
            <ArrowRight className="ml-2 h-5 w-5" />
          </>
        )}
      </Button>

      {/* Skip option */}
      <Button
        variant="ghost"
        onClick={nextStep}
        disabled={isLoading}
        className="w-full text-muted-foreground"
      >
        Skip for now - I&apos;ll create a spec later
      </Button>
    </div>
  );
}
