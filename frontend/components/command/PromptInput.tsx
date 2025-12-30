"use client"

import { useState, useRef, useCallback } from "react"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { ArrowUp, Paperclip, Loader2 } from "lucide-react"

interface PromptInputProps {
  onSubmit?: (prompt: string) => void
  isLoading?: boolean
  placeholder?: string
  submitLabel?: string
  className?: string
}

export function PromptInput({
  onSubmit,
  isLoading = false,
  placeholder = "Ask Cursor to build, fix bugs, explore",
  submitLabel,
  className,
}: PromptInputProps) {
  const [value, setValue] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = useCallback(() => {
    if (value.trim() && !isLoading) {
      onSubmit?.(value.trim())
    }
  }, [value, isLoading, onSubmit])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleSubmit()
      }
    },
    [handleSubmit]
  )

  // Auto-resize textarea
  const handleInput = useCallback(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = "auto"
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [])

  return (
    <div className={cn("relative", className)}>
      <div className="rounded-lg border border-border bg-card shadow-sm focus-within:ring-1 focus-within:ring-ring">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder={placeholder}
          disabled={isLoading}
          className="min-h-[100px] resize-none border-0 bg-transparent px-4 py-3 text-base focus-visible:ring-0 focus-visible:ring-offset-0"
          rows={3}
        />
        <div className="flex items-center justify-between border-t border-border px-3 py-2">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-foreground"
              disabled={isLoading}
            >
              <Paperclip className="h-4 w-4" />
              <span className="sr-only">Attach file</span>
            </Button>
          </div>
          <Button
            type="button"
            size={submitLabel ? "sm" : "icon"}
            className={submitLabel ? "h-8 gap-1.5 px-3" : "h-8 w-8"}
            onClick={handleSubmit}
            disabled={!value.trim() || isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                {submitLabel && <span>{submitLabel}</span>}
                <ArrowUp className="h-4 w-4" />
              </>
            )}
            {!submitLabel && <span className="sr-only">Submit</span>}
          </Button>
        </div>
      </div>
    </div>
  )
}
