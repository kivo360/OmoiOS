"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { ConnectedAccounts } from "@/components/settings/ConnectedAccounts";

export default function IntegrationsSettingsPage() {
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
        <h1 className="text-2xl font-bold">Integrations</h1>
        <p className="text-muted-foreground">
          Connect third-party services to enhance your workflow
        </p>
      </div>

      <div className="space-y-6">
        <ConnectedAccounts />
      </div>
    </div>
  );
}
