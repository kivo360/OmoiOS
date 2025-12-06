"use client"

import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArrowLeft } from "lucide-react"

const stats = [
    { label: "Total (24h)", value: 12 },
    { label: "Success", value: 9 },
    { label: "Warnings", value: 2 },
    { label: "Failed", value: 1 },
]

const interventions = [
    {
        id: "int-142",
        agent: "worker-5",
        type: "idle",
        result: "success",
        message: "Prompted agent to update task status and proceed",
        time: "6m ago",
    },
    {
        id: "int-139",
        agent: "worker-2",
        type: "constraint_violation",
        result: "success",
        message: "Blocked external package install, suggested built-in crypto",
        time: "42m ago",
    },
    {
        id: "int-134",
        agent: "worker-3",
        type: "drifting",
        result: "warning",
        message: "Agent working on unrelated files; asked to refocus on ticket",
        time: "1h ago",
    },
    {
        id: "int-129",
        agent: "worker-1",
        type: "missed_steps",
        result: "failed",
        message: "Mandatory validation not performed; human review requested",
        time: "3h ago",
    },
]

const resultColor = (status: string) => {
    if (status === "success") return "bg-emerald-100 text-emerald-700"
    if (status === "warning") return "bg-amber-100 text-amber-700"
    return "bg-rose-100 text-rose-700"
}

const typeLabel: Record<string, string> = {
    idle: "Idle",
    constraint_violation: "Constraint",
    drifting: "Drifting",
    missed_steps: "Missed Steps",
}

export default function InterventionsPage() {
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
                    <p className="text-muted-foreground">Guardian steering and constraint enforcement</p>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-4">
                {stats.map((s) => (
                    <Card key={s.label}>
                        <CardContent className="p-4">
                            <p className="text-sm text-muted-foreground">{s.label}</p>
                            <p className="text-2xl font-bold">{s.value}</p>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Recent interventions</CardTitle>
                    <CardDescription>Root cause categorization and results</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <Tabs defaultValue="all">
                        <TabsList>
                            <TabsTrigger value="all">All</TabsTrigger>
                            <TabsTrigger value="success">Success</TabsTrigger>
                            <TabsTrigger value="warning">Warnings</TabsTrigger>
                            <TabsTrigger value="failed">Failed</TabsTrigger>
                        </TabsList>
                        <TabsContent value="all" className="space-y-3">
                            {interventions.map((item) => (
                                <div key={item.id} className="rounded-lg border p-4">
                                    <div className="flex flex-wrap items-center justify-between gap-3">
                                        <div className="flex flex-col">
                                            <div className="flex items-center gap-2">
                                                <span className="font-semibold">{item.agent}</span>
                                                <Badge variant="secondary" className="capitalize">
                                                    {typeLabel[item.type] ?? item.type}
                                                </Badge>
                                            </div>
                                            <p className="text-sm text-muted-foreground">{item.message}</p>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <Badge className={resultColor(item.result)} variant="outline">
                                                {item.result}
                                            </Badge>
                                            <span className="text-sm text-muted-foreground">{item.time}</span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </TabsContent>
                        <TabsContent value="success" className="space-y-3">
                            {interventions
                                .filter((i) => i.result === "success")
                                .map((item) => (
                                    <div key={item.id} className="rounded-lg border p-4">
                                        <div className="flex flex-wrap items-center justify-between gap-3">
                                            <div className="flex flex-col">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-semibold">{item.agent}</span>
                                                    <Badge variant="secondary" className="capitalize">
                                                        {typeLabel[item.type] ?? item.type}
                                                    </Badge>
                                                </div>
                                                <p className="text-sm text-muted-foreground">{item.message}</p>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <Badge className={resultColor(item.result)} variant="outline">
                                                    {item.result}
                                                </Badge>
                                                <span className="text-sm text-muted-foreground">{item.time}</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                        </TabsContent>
                        <TabsContent value="warning" className="space-y-3">
                            {interventions
                                .filter((i) => i.result === "warning")
                                .map((item) => (
                                    <div key={item.id} className="rounded-lg border p-4">
                                        <div className="flex flex-wrap items-center justify-between gap-3">
                                            <div className="flex flex-col">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-semibold">{item.agent}</span>
                                                    <Badge variant="secondary" className="capitalize">
                                                        {typeLabel[item.type] ?? item.type}
                                                    </Badge>
                                                </div>
                                                <p className="text-sm text-muted-foreground">{item.message}</p>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <Badge className={resultColor(item.result)} variant="outline">
                                                    {item.result}
                                                </Badge>
                                                <span className="text-sm text-muted-foreground">{item.time}</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                        </TabsContent>
                        <TabsContent value="failed" className="space-y-3">
                            {interventions
                                .filter((i) => i.result === "failed")
                                .map((item) => (
                                    <div key={item.id} className="rounded-lg border p-4">
                                        <div className="flex flex-wrap items-center justify-between gap-3">
                                            <div className="flex flex-col">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-semibold">{item.agent}</span>
                                                    <Badge variant="secondary" className="capitalize">
                                                        {typeLabel[item.type] ?? item.type}
                                                    </Badge>
                                                </div>
                                                <p className="text-sm text-muted-foreground">{item.message}</p>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <Badge className={resultColor(item.result)} variant="outline">
                                                    {item.result}
                                                </Badge>
                                                <span className="text-sm text-muted-foreground">{item.time}</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                        </TabsContent>
                    </Tabs>
                </CardContent>
            </Card>
        </div>
    )
}

