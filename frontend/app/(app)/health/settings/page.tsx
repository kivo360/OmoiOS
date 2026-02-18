"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Info } from "lucide-react";

export default function HealthSettingsPage() {
  const [alignmentThreshold, setAlignmentThreshold] = useState([70]);
  const [idleMinutes, setIdleMinutes] = useState("10");
  const [pollInterval, setPollInterval] = useState("60");
  const [notifyEmail, setNotifyEmail] = useState(true);
  const [notifySlack, setNotifySlack] = useState(true);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const handleSave = () => {
    // Settings API not yet implemented - show message
    setSaveMessage("Settings saved locally (backend persistence coming soon)");
    setTimeout(() => setSaveMessage(null), 3000);
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <Button asChild variant="ghost" size="sm">
          <Link href="/health">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <div className="text-right">
          <div className="flex items-center gap-2 justify-end">
            <h1 className="text-2xl font-bold">Monitoring Settings</h1>
            <Badge variant="secondary" className="text-xs">
              <Info className="h-3 w-3 mr-1" />
              Local Only
            </Badge>
          </div>
          <p className="text-muted-foreground">
            Thresholds, cadence, and notifications
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Thresholds</CardTitle>
          <CardDescription>
            Alignment, idle, and constraint checks
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label>Minimum alignment score (%)</Label>
            <Slider
              value={alignmentThreshold}
              onValueChange={setAlignmentThreshold}
              min={50}
              max={100}
              step={1}
            />
            <p className="text-sm text-muted-foreground">
              Current: {alignmentThreshold[0]}% — interventions triggered below
              this score
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="idle">Idle detection (minutes)</Label>
            <Input
              id="idle"
              type="number"
              min={1}
              value={idleMinutes}
              onChange={(e) => setIdleMinutes(e.target.value)}
              className="w-32"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Cadence</CardTitle>
          <CardDescription>Monitoring poll intervals</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Monitoring loop interval</Label>
            <Select defaultValue={pollInterval} onValueChange={setPollInterval}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30">30s</SelectItem>
                <SelectItem value="60">60s</SelectItem>
                <SelectItem value="90">90s</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Notification batch window</Label>
            <Select defaultValue="5">
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1 minute</SelectItem>
                <SelectItem value="5">5 minutes</SelectItem>
                <SelectItem value="15">15 minutes</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
          <CardDescription>
            Delivery channels for alerts and interventions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div>
              <p className="font-semibold">Email alerts</p>
              <p className="text-sm text-muted-foreground">
                Send critical alerts and failures
              </p>
            </div>
            <Switch checked={notifyEmail} onCheckedChange={setNotifyEmail} />
          </div>
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div>
              <p className="font-semibold">Slack notifications</p>
              <p className="text-sm text-muted-foreground">
                Guardian interventions and warnings
              </p>
            </div>
            <Switch checked={notifySlack} onCheckedChange={setNotifySlack} />
          </div>
        </CardContent>
      </Card>

      <Separator />

      <div className="flex items-center gap-3">
        <Button variant="outline" asChild>
          <Link href="/health">Cancel</Link>
        </Button>
        <Button onClick={handleSave}>Save settings</Button>
        {saveMessage && (
          <span className="text-sm text-muted-foreground animate-in fade-in">
            {saveMessage}
          </span>
        )}
      </div>
    </div>
  );
}
