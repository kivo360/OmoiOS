"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { Minus, Plus, RotateCcw } from "lucide-react"

export interface CounterProps {
  initialValue?: number
  min?: number
  max?: number
  step?: number
  onChange?: (value: number) => void
  className?: string
}

const Counter = React.forwardRef<HTMLDivElement, CounterProps>(
  (
    {
      initialValue = 0,
      min = Number.MIN_SAFE_INTEGER,
      max = Number.MAX_SAFE_INTEGER,
      step = 1,
      onChange,
      className,
    },
    ref
  ) => {
    const [count, setCount] = React.useState(initialValue)

    const updateCount = React.useCallback(
      (newValue: number) => {
        const clampedValue = Math.max(min, Math.min(max, newValue))
        setCount(clampedValue)
        onChange?.(clampedValue)
      },
      [min, max, onChange]
    )

    const increment = React.useCallback(() => {
      updateCount(count + step)
    }, [count, step, updateCount])

    const decrement = React.useCallback(() => {
      updateCount(count - step)
    }, [count, step, updateCount])

    const reset = React.useCallback(() => {
      updateCount(initialValue)
    }, [initialValue, updateCount])

    return (
      <Card ref={ref} className={cn("w-full max-w-sm", className)}>
        <CardHeader className="pb-2">
          <CardTitle className="text-center text-lg">Counter</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            className="flex items-center justify-center rounded-lg bg-muted py-6"
            data-testid="counter-display"
          >
            <span className="text-4xl font-bold tabular-nums">{count}</span>
          </div>
          <div className="flex items-center justify-center gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={decrement}
              disabled={count <= min}
              aria-label="Decrement"
              data-testid="decrement-button"
            >
              <Minus className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={reset}
              aria-label="Reset"
              data-testid="reset-button"
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={increment}
              disabled={count >= max}
              aria-label="Increment"
              data-testid="increment-button"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }
)
Counter.displayName = "Counter"

export { Counter }
