"use client";

import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Copy, Linkedin, Twitter } from "lucide-react";
import { trackEvent } from "@/lib/analytics/track";

interface ShareButtonsProps {
  specTitle: string;
  shareUrl: string;
  specId: string;
  stats: {
    requirements: number;
    tasks: number;
    coverage: number;
  };
}

export function ShareButtons({
  specTitle,
  shareUrl,
  specId,
  stats,
}: ShareButtonsProps) {
  const tweetText = [
    `Just shipped "${specTitle}" with @TheGeodexes's OmoiOS`,
    "",
    `✅ ${stats.tasks} tasks automated`,
    "✅ PR created automatically",
    "",
    shareUrl,
  ].join("\n");

  const handleShareTwitter = () => {
    trackEvent("spec_shared", { platform: "twitter", spec_id: specId });
    window.open(
      `https://twitter.com/intent/tweet?text=${encodeURIComponent(tweetText)}`,
      "_blank",
      "noopener,noreferrer",
    );
  };

  const handleShareLinkedIn = () => {
    trackEvent("spec_shared", { platform: "linkedin", spec_id: specId });
    window.open(
      `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
      "_blank",
      "noopener,noreferrer",
    );
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      toast.success("Link copied!");
      trackEvent("spec_shared", { platform: "copy_link", spec_id: specId });
    } catch {
      toast.error("Failed to copy link");
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="sm" onClick={handleShareTwitter}>
        <Twitter className="mr-2 h-4 w-4" />
        Share on X
      </Button>
      <Button variant="outline" size="sm" onClick={handleShareLinkedIn}>
        <Linkedin className="mr-2 h-4 w-4" />
        LinkedIn
      </Button>
      <Button variant="outline" size="sm" onClick={handleCopyLink}>
        <Copy className="mr-2 h-4 w-4" />
        Copy Link
      </Button>
    </div>
  );
}
