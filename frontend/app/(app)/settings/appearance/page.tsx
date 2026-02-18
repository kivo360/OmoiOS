"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ArrowLeft,
  Loader2,
  Sun,
  Moon,
  Monitor,
  Type,
  Layout,
  Eye,
  Columns,
  PanelLeftClose,
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function AppearanceSettingsPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [theme, setTheme] = useState("system");
  const [accentColor, setAccentColor] = useState("blue");
  const [fontSize, setFontSize] = useState([14]);
  const [codeFont, setCodeFont] = useState("jetbrains");
  const [sidebarPosition, setSidebarPosition] = useState("left");
  const [compactMode, setCompactMode] = useState(false);
  const [animationsEnabled, setAnimationsEnabled] = useState(true);
  const [highContrastMode, setHighContrastMode] = useState(false);
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [wordWrap, setWordWrap] = useState(true);

  const handleSave = async () => {
    setIsLoading(true);
    try {
      // Save to local storage (these are UI preferences)
      localStorage.setItem(
        "appearance-settings",
        JSON.stringify({
          theme,
          accentColor,
          fontSize,
          codeFont,
          sidebarPosition,
          compactMode,
          animationsEnabled,
          highContrastMode,
          showLineNumbers,
          wordWrap,
        }),
      );
      toast.success("Appearance settings saved!");
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setIsLoading(false);
    }
  };

  // Load saved preferences on mount
  useEffect(() => {
    const saved = localStorage.getItem("appearance-settings");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.theme) setTheme(parsed.theme);
        if (parsed.accentColor) setAccentColor(parsed.accentColor);
        if (parsed.fontSize) setFontSize(parsed.fontSize);
        if (parsed.codeFont) setCodeFont(parsed.codeFont);
        if (parsed.sidebarPosition) setSidebarPosition(parsed.sidebarPosition);
        if (parsed.compactMode !== undefined)
          setCompactMode(parsed.compactMode);
        if (parsed.animationsEnabled !== undefined)
          setAnimationsEnabled(parsed.animationsEnabled);
        if (parsed.highContrastMode !== undefined)
          setHighContrastMode(parsed.highContrastMode);
        if (parsed.showLineNumbers !== undefined)
          setShowLineNumbers(parsed.showLineNumbers);
        if (parsed.wordWrap !== undefined) setWordWrap(parsed.wordWrap);
      } catch (e) {
        console.error("Failed to parse appearance settings", e);
      }
    }
  }, []);

  const accentColors = [
    { value: "blue", label: "Blue", color: "#3B82F6" },
    { value: "purple", label: "Purple", color: "#8B5CF6" },
    { value: "green", label: "Green", color: "#10B981" },
    { value: "orange", label: "Orange", color: "#F59E0B" },
    { value: "pink", label: "Pink", color: "#EC4899" },
    { value: "red", label: "Red", color: "#EF4444" },
  ];

  return (
    <div className="container mx-auto max-w-3xl p-6 space-y-6">
      <Link
        href="/settings"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Settings
      </Link>

      <div>
        <h1 className="text-2xl font-bold">Appearance Settings</h1>
        <p className="text-muted-foreground">
          Customize the look and feel of your workspace
        </p>
      </div>

      <div className="space-y-6">
        {/* Theme Selection Card */}
        <Card>
          <CardHeader>
            <CardTitle>Theme</CardTitle>
            <CardDescription>
              Choose your preferred color scheme
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RadioGroup
              value={theme}
              onValueChange={setTheme}
              className="grid grid-cols-3 gap-4"
            >
              <div>
                <RadioGroupItem
                  value="light"
                  id="theme-light"
                  className="peer sr-only"
                />
                <Label
                  htmlFor="theme-light"
                  className="flex flex-col items-center justify-between rounded-lg border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer"
                >
                  <Sun className="mb-3 h-6 w-6" />
                  <span className="text-sm font-medium">Light</span>
                </Label>
              </div>
              <div>
                <RadioGroupItem
                  value="dark"
                  id="theme-dark"
                  className="peer sr-only"
                />
                <Label
                  htmlFor="theme-dark"
                  className="flex flex-col items-center justify-between rounded-lg border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer"
                >
                  <Moon className="mb-3 h-6 w-6" />
                  <span className="text-sm font-medium">Dark</span>
                </Label>
              </div>
              <div>
                <RadioGroupItem
                  value="system"
                  id="theme-system"
                  className="peer sr-only"
                />
                <Label
                  htmlFor="theme-system"
                  className="flex flex-col items-center justify-between rounded-lg border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary [&:has([data-state=checked])]:border-primary cursor-pointer"
                >
                  <Monitor className="mb-3 h-6 w-6" />
                  <span className="text-sm font-medium">System</span>
                </Label>
              </div>
            </RadioGroup>
          </CardContent>
        </Card>

        {/* Accent Color Card */}
        <Card>
          <CardHeader>
            <CardTitle>Accent Color</CardTitle>
            <CardDescription>
              Choose your preferred accent color
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {accentColors.map((color) => (
                <button
                  key={color.value}
                  onClick={() => setAccentColor(color.value)}
                  className={cn(
                    "flex h-12 w-12 items-center justify-center rounded-full transition-all border-2",
                    accentColor === color.value
                      ? "border-foreground scale-110"
                      : "border-transparent hover:scale-110",
                  )}
                  style={{ backgroundColor: color.color }}
                  title={color.label}
                >
                  {accentColor === color.value && (
                    <svg
                      className="h-5 w-5 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  )}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Typography Card */}
        <Card>
          <CardHeader>
            <CardTitle>Typography</CardTitle>
            <CardDescription>Adjust font settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="flex items-center gap-2">
                    <Type className="h-4 w-4" />
                    Font Size
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Adjust the base font size
                  </p>
                </div>
                <span className="text-sm font-mono w-12 text-right">
                  {fontSize[0]}px
                </span>
              </div>
              <Slider
                value={fontSize}
                onValueChange={setFontSize}
                min={12}
                max={20}
                step={1}
                className="w-full"
              />
            </div>

            <Separator />

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Code Font</Label>
                <p className="text-sm text-muted-foreground">
                  Font family for code blocks
                </p>
              </div>
              <Select value={codeFont} onValueChange={setCodeFont}>
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="jetbrains">JetBrains Mono</SelectItem>
                  <SelectItem value="fira">Fira Code</SelectItem>
                  <SelectItem value="source">Source Code Pro</SelectItem>
                  <SelectItem value="monaco">Monaco</SelectItem>
                  <SelectItem value="consolas">Consolas</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Layout Card */}
        <Card>
          <CardHeader>
            <CardTitle>Layout</CardTitle>
            <CardDescription>
              Configure workspace layout preferences
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="flex items-center gap-2">
                  <PanelLeftClose className="h-4 w-4" />
                  Sidebar Position
                </Label>
                <p className="text-sm text-muted-foreground">
                  Position of the navigation sidebar
                </p>
              </div>
              <Select
                value={sidebarPosition}
                onValueChange={setSidebarPosition}
              >
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="left">Left</SelectItem>
                  <SelectItem value="right">Right</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Separator />

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="flex items-center gap-2">
                  <Columns className="h-4 w-4" />
                  Compact Mode
                </Label>
                <p className="text-sm text-muted-foreground">
                  Reduce spacing for more content density
                </p>
              </div>
              <Switch checked={compactMode} onCheckedChange={setCompactMode} />
            </div>

            <Separator />

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="flex items-center gap-2">
                  <Layout className="h-4 w-4" />
                  Animations
                </Label>
                <p className="text-sm text-muted-foreground">
                  Enable interface animations and transitions
                </p>
              </div>
              <Switch
                checked={animationsEnabled}
                onCheckedChange={setAnimationsEnabled}
              />
            </div>
          </CardContent>
        </Card>

        {/* Accessibility Card */}
        <Card>
          <CardHeader>
            <CardTitle>Accessibility</CardTitle>
            <CardDescription>Adjust accessibility settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="flex items-center gap-2">
                  <Eye className="h-4 w-4" />
                  High Contrast Mode
                </Label>
                <p className="text-sm text-muted-foreground">
                  Increase contrast for better visibility
                </p>
              </div>
              <Switch
                checked={highContrastMode}
                onCheckedChange={setHighContrastMode}
              />
            </div>
          </CardContent>
        </Card>

        {/* Editor Card */}
        <Card>
          <CardHeader>
            <CardTitle>Editor Preferences</CardTitle>
            <CardDescription>Configure code editor behavior</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Show Line Numbers</Label>
                <p className="text-sm text-muted-foreground">
                  Display line numbers in code blocks
                </p>
              </div>
              <Switch
                checked={showLineNumbers}
                onCheckedChange={setShowLineNumbers}
              />
            </div>

            <Separator />

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Word Wrap</Label>
                <p className="text-sm text-muted-foreground">
                  Wrap long lines in code blocks
                </p>
              </div>
              <Switch checked={wordWrap} onCheckedChange={setWordWrap} />
            </div>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => window.location.reload()}>
            Reset to Defaults
          </Button>
          <Button onClick={handleSave} disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
          </Button>
        </div>
      </div>
    </div>
  );
}
