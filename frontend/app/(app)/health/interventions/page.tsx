"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, AlertCircle, CheckCircle } from "lucide-react";
import { useAnomalies, useAcknowledgeAnomaly } from "@/hooks/useMonitor";

const resultColor = (severity: string, acknowledged: boolean) => {
  if (acknowledged) return "bg-emerald-100 text-emerald-700";
  if (severity === "low") return "bg-emerald-100 text-emerald-700";
  if (severity === "medium") return "bg-amber-100 text-amber-700";
  return "bg-rose-100 text-rose-700";
};

const formatTimeAgo = (dateStr: string | null | undefined) => {
  if (!dateStr) return "N/A";
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / (1000 * 60));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
};

export default function InterventionsPage() {
  const [tab, setTab] = useState("all");
  const { data: anomalies, isLoading } = useAnomalies({ hours: 24 });
  const acknowledgeMutation = useAcknowledgeAnomaly();

  // Calculate stats
  const stats = useMemo(() => {
    if (!anomalies)
      return [
        { label: "Total (24h)", value: 0 },
        { label: "High", value: 0 },
        { label: "Medium", value: 0 },
        { label: "Low", value: 0 },
      ];
    return [
      { label: "Total (24h)", value: anomalies.length },
      {
        label: "High",
        value: anomalies.filter((a) => a.severity === "high").length,
      },
      {
        label: "Medium",
        value: anomalies.filter((a) => a.severity === "medium").length,
      },
      {
        label: "Low",
        value: anomalies.filter((a) => a.severity === "low").length,
      },
    ];
  }, [anomalies]);

  // Filter anomalies by tab
  const filteredAnomalies = useMemo(() => {
    if (!anomalies) return [];
    if (tab === "all") return anomalies;
    if (tab === "acknowledged")
      return anomalies.filter((a) => a.acknowledged_at);
    if (tab === "pending") return anomalies.filter((a) => !a.acknowledged_at);
    return anomalies.filter((a) => a.severity === tab);
  }, [anomalies, tab]);

  const handleAcknowledge = (anomalyId: string) => {
    acknowledgeMutation.mutate(anomalyId);
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
          <h1 className="text-2xl font-bold">Intervention History</h1>
          <p className="text-muted-foreground">
            Guardian steering and constraint enforcement
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">{s.label}</p>
              {isLoading ? (
                <Skeleton className="h-8 w-12 mt-1" />
              ) : (
                <p className="text-2xl font-bold">{s.value}</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>System Anomalies</CardTitle>
          <CardDescription>
            Detected anomalies and interventions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList>
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="pending">Pending</TabsTrigger>
              <TabsTrigger value="acknowledged">Acknowledged</TabsTrigger>
              <TabsTrigger value="high">High</TabsTrigger>
            </TabsList>
            <TabsContent value={tab} className="space-y-3 mt-4">
              {isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3, 4].map((i) => (
                    <Skeleton key={i} className="h-20 w-full" />
                  ))}
                </div>
              ) : filteredAnomalies.length === 0 ? (
                <div className="py-8 text-center text-muted-foreground">
                  <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No anomalies in this category</p>
                </div>
              ) : (
                filteredAnomalies.map((anomaly) => (
                  <div
                    key={anomaly.anomaly_id}
                    className="rounded-lg border p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-col flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">
                            {anomaly.metric_name}
                          </span>
                          <Badge variant="secondary" className="capitalize">
                            {anomaly.anomaly_type}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {anomaly.description}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                          <span>
                            Baseline: {anomaly.baseline_value.toFixed(2)}
                          </span>
                          <span>
                            Observed: {anomaly.observed_value.toFixed(2)}
                          </span>
                          <span>
                            Deviation: {anomaly.deviation_percent.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge
                          className={resultColor(
                            anomaly.severity,
                            !!anomaly.acknowledged_at,
                          )}
                          variant="outline"
                        >
                          {anomaly.acknowledged_at
                            ? "Acknowledged"
                            : anomaly.severity}
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                          {formatTimeAgo(anomaly.detected_at)}
                        </span>
                        {!anomaly.acknowledged_at && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              handleAcknowledge(anomaly.anomaly_id)
                            }
                            disabled={acknowledgeMutation.isPending}
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Ack
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
