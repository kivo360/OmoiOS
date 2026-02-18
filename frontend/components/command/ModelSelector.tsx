"use client";

import { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export interface Model {
  id: string;
  name: string;
  description?: string;
}

const defaultModels: Model[] = [
  { id: "opus-4.5", name: "Opus 4.5", description: "Most capable" },
  { id: "sonnet-4", name: "Sonnet 4", description: "Balanced" },
  { id: "haiku-3", name: "Haiku 3", description: "Fast" },
];

interface ModelSelectorProps {
  models?: Model[];
  value?: string;
  onValueChange?: (value: string) => void;
  className?: string;
}

export function ModelSelector({
  models = defaultModels,
  value,
  onValueChange,
  className,
}: ModelSelectorProps) {
  const [selectedModel, setSelectedModel] = useState(value || models[0]?.id);

  const handleChange = (newValue: string) => {
    setSelectedModel(newValue);
    onValueChange?.(newValue);
  };

  return (
    <Select value={selectedModel} onValueChange={handleChange}>
      <SelectTrigger className={cn("w-[140px] h-8 text-sm", className)}>
        <SelectValue placeholder="Select model" />
      </SelectTrigger>
      <SelectContent>
        {models.map((model) => (
          <SelectItem key={model.id} value={model.id}>
            <div className="flex items-center gap-2">
              <span>{model.name}</span>
              {model.description && (
                <span className="text-xs text-muted-foreground">
                  ({model.description})
                </span>
              )}
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
