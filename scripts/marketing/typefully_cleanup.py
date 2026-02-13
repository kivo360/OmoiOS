#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.25.0",
# ]
# ///
"""
Typefully Duplicate Cleanup Script

Detects and removes duplicate drafts from Typefully.
Uses the v2 API to list all scheduled/draft posts and identifies duplicates
by comparing content signatures.
"""

import argparse
import os
import sys
from collections import defaultdict
from dataclasses import dataclass

import httpx

# Typefully API v2 base URL
API_BASE = "https://api.typefully.com/v2"


@dataclass
class Draft:
    """Represents a Typefully draft"""
    id: int
    preview: str
    status: str
    scheduled_date: str | None
    created_at: str

    @property
    def content_signature(self) -> str:
        """Generate a signature for duplicate detection"""
        # Normalize: lowercase, strip whitespace, remove common variations
        text = self.preview.lower().strip()
        # Remove trailing ellipsis that Typefully adds to previews
        if text.endswith("..."):
            text = text[:-3]
        return text[:100]  # First 100 chars is usually enough


def get_api_key() -> str:
    """Get API key from environment"""
    key = os.environ.get("TYPEFULLY_API_KEY")
    if not key:
        print("❌ TYPEFULLY_API_KEY environment variable not set")
        print("   Set it with: export TYPEFULLY_API_KEY=your_key_here")
        sys.exit(1)
    return key


def get_social_set_id(client: httpx.Client, headers: dict) -> int:
    """Get the first social set ID"""
    response = client.get(f"{API_BASE}/social-sets", headers=headers)
    response.raise_for_status()
    data = response.json()

    if not data.get("results"):
        print("❌ No social sets found")
        sys.exit(1)

    social_set = data["results"][0]
    print(f"📱 Using social set: @{social_set['username']}")
    return social_set["id"]


def fetch_all_drafts(client: httpx.Client, headers: dict, social_set_id: int, status: str = "scheduled") -> list[Draft]:
    """Fetch all drafts with pagination"""
    drafts = []
    offset = 0
    limit = 50

    while True:
        response = client.get(
            f"{API_BASE}/social-sets/{social_set_id}/drafts",
            headers=headers,
            params={"status": status, "limit": limit, "offset": offset}
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if not results:
            break

        for item in results:
            drafts.append(Draft(
                id=item["id"],
                preview=item.get("preview", ""),
                status=item.get("status", ""),
                scheduled_date=item.get("scheduled_date"),
                created_at=item.get("created_at", ""),
            ))

        offset += limit
        if offset >= data.get("count", 0):
            break

    return drafts


def find_duplicates(drafts: list[Draft]) -> dict[str, list[Draft]]:
    """Group drafts by content signature to find duplicates"""
    by_signature: dict[str, list[Draft]] = defaultdict(list)

    for draft in drafts:
        sig = draft.content_signature
        if sig:  # Skip empty content
            by_signature[sig].append(draft)

    # Filter to only groups with duplicates
    return {sig: items for sig, items in by_signature.items() if len(items) > 1}


def delete_draft(client: httpx.Client, headers: dict, social_set_id: int, draft_id: int) -> bool:
    """Delete a single draft"""
    try:
        response = client.delete(
            f"{API_BASE}/social-sets/{social_set_id}/drafts/{draft_id}",
            headers=headers
        )
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        print(f"    ⚠️  Failed to delete draft {draft_id}: {e.response.status_code}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Clean up duplicate Typefully drafts")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be deleted without actually deleting")
    parser.add_argument("--status", default="scheduled", choices=["scheduled", "draft", "published"],
                       help="Status of drafts to check (default: scheduled)")
    parser.add_argument("--keep", default="oldest", choices=["oldest", "newest"],
                       help="Which duplicate to keep (default: oldest)")
    parser.add_argument("--purge-all", action="store_true",
                       help="Delete ALL drafts with the given status (not just duplicates)")
    args = parser.parse_args()

    api_key = get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print("=" * 60)
    print("TYPEFULLY DUPLICATE CLEANUP")
    print("=" * 60)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")

    with httpx.Client(timeout=30.0) as client:
        # Get social set
        social_set_id = get_social_set_id(client, headers)

        # Fetch all drafts
        print(f"\n📥 Fetching {args.status} drafts...")
        drafts = fetch_all_drafts(client, headers, social_set_id, args.status)
        print(f"   Found {len(drafts)} total drafts")

        # Purge all mode
        if args.purge_all:
            print(f"\n🗑️  PURGE ALL MODE - Deleting all {len(drafts)} {args.status} drafts")
            print("-" * 60)

            deleted_count = 0
            failed_count = 0

            for draft in drafts:
                preview = draft.preview[:60] + "..." if len(draft.preview) > 60 else draft.preview
                sched = f" (scheduled: {draft.scheduled_date[:10]})" if draft.scheduled_date else ""
                print(f"  ✗ {preview}{sched}", end="")

                if args.dry_run:
                    print(" [DRY RUN]")
                    deleted_count += 1
                else:
                    import time
                    if delete_draft(client, headers, social_set_id, draft.id):
                        print(" ✅")
                        deleted_count += 1
                        time.sleep(1)  # Rate limit safety
                    else:
                        print(" ❌")
                        failed_count += 1

            print("\n" + "=" * 60)
            print("PURGE SUMMARY")
            print("=" * 60)
            if args.dry_run:
                print(f"Would delete: {deleted_count} of {len(drafts)} {args.status} drafts")
                print(f"\nRun without --dry-run to actually delete these drafts.")
            else:
                print(f"Deleted: {deleted_count} of {len(drafts)} {args.status} drafts")
                if failed_count:
                    print(f"Failed: {failed_count}")
            print("=" * 60)
            return

        # Find duplicates
        print("\n🔍 Analyzing for duplicates...")
        duplicate_groups = find_duplicates(drafts)

        if not duplicate_groups:
            print("✅ No duplicates found!")
            return

        # Calculate totals
        total_duplicates = sum(len(items) - 1 for items in duplicate_groups.values())
        print(f"   Found {len(duplicate_groups)} duplicate groups ({total_duplicates} extra posts to remove)")

        # Process each group
        print("\n" + "-" * 60)
        deleted_count = 0
        failed_count = 0

        for sig, items in duplicate_groups.items():
            # Sort by created_at to determine which to keep
            sorted_items = sorted(items, key=lambda d: d.created_at)

            if args.keep == "oldest":
                keep = sorted_items[0]
                remove = sorted_items[1:]
            else:
                keep = sorted_items[-1]
                remove = sorted_items[:-1]

            preview = sig[:50] + "..." if len(sig) > 50 else sig
            print(f"\n📝 \"{preview}\"")
            print(f"   Found {len(items)} copies")
            print(f"   ✓ Keeping: ID {keep.id} (created: {keep.created_at[:10]})")

            for draft in remove:
                print(f"   ✗ Removing: ID {draft.id} (created: {draft.created_at[:10]})", end="")

                if args.dry_run:
                    print(" [DRY RUN]")
                    deleted_count += 1
                else:
                    if delete_draft(client, headers, social_set_id, draft.id):
                        print(" ✅")
                        deleted_count += 1
                    else:
                        print(" ❌")
                        failed_count += 1

        # Summary
        print("\n" + "=" * 60)
        print("CLEANUP SUMMARY")
        print("=" * 60)
        if args.dry_run:
            print(f"Would delete: {deleted_count} duplicates")
            print("\nRun without --dry-run to actually delete these drafts.")
        else:
            print(f"Deleted: {deleted_count} duplicates")
            if failed_count:
                print(f"Failed: {failed_count}")
        print("=" * 60)


if __name__ == "__main__":
    main()
