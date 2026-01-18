#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.25.0",
#     "python-dateutil>=2.8.0",
#     "pyyaml>=6.0",
# ]
# ///
"""
Typefully Dynamic Scheduler

Reads posts dynamically from swipe_file/*.md and creates drafts in Typefully.
This is the new, more flexible version of the scheduler.

Usage:
    # Generate and schedule a 2-week mix (includes ragebait from raw_unclean_posts.md)
    uv run typefully_dynamic.py --weeks 2

    # Dry run to preview
    uv run typefully_dynamic.py --weeks 2 --dry-run

    # Prioritize ragebait posts
    uv run typefully_dynamic.py --weeks 2 --prioritize raw-unclean

    # Only schedule ragebait posts
    uv run typefully_dynamic.py --weeks 2 --only raw-unclean

    # Custom start date
    uv run typefully_dynamic.py --weeks 2 --start-date 2026-01-20

    # Create as drafts only (no scheduled time)
    uv run typefully_dynamic.py --weeks 2 --draft-only

Environment:
    TYPEFULLY_API_KEY - Your Typefully API key (required)
"""

import os
import sys
import time
import argparse
import httpx
from datetime import datetime, timedelta
from dateutil.tz import gettz
from dateutil import parser as date_parser
from pathlib import Path

# Import our modules
from schedule_generator import generate_schedule, GeneratedSchedule, ScheduledPost
from swipe_file_parser import get_swipe_file_dir


# ============================================================================
# Configuration
# ============================================================================

TYPEFULLY_API_BASE = "https://api.typefully.com/v2"
DEFAULT_TIMEZONE = "America/Asuncion"


# ============================================================================
# Typefully Client (simplified from original)
# ============================================================================

class TypefullyClient:
    """Client for Typefully API v2"""

    def __init__(self, api_key: str, timezone: str = DEFAULT_TIMEZONE):
        self.api_key = api_key
        self.base_url = TYPEFULLY_API_BASE
        self.timezone = timezone

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_me(self) -> dict:
        """Get authenticated user info"""
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{self.base_url}/me", headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    def get_social_sets(self) -> list[dict]:
        """Get all connected social accounts"""
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{self.base_url}/social-sets", headers=self._headers())
            resp.raise_for_status()
            return resp.json().get("results", [])

    def get_drafts(self, social_set_id: str, limit: int = 50) -> list[dict]:
        """Get existing drafts"""
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{self.base_url}/social-sets/{social_set_id}/drafts",
                headers=self._headers(),
                params={"limit": limit}
            )
            resp.raise_for_status()
            return resp.json().get("results", [])

    def create_draft(
        self,
        social_set_id: str,
        posts: list[str],
        publish_at: str | None = None,
        draft_title: str | None = None,
    ) -> tuple[dict, dict]:
        """Create a new draft"""
        x_posts = [{"text": text, "media_ids": []} for text in posts]

        payload = {
            "platforms": {
                "x": {
                    "enabled": True,
                    "posts": x_posts,
                    "settings": {}
                }
            }
        }

        if publish_at:
            payload["publish_at"] = publish_at

        if draft_title:
            payload["draft_title"] = draft_title

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.base_url}/social-sets/{social_set_id}/drafts",
                headers=self._headers(),
                json=payload
            )

            rate_limit_info = {
                "user_remaining": resp.headers.get("X-RateLimit-User-Remaining"),
                "user_reset": resp.headers.get("X-RateLimit-User-Reset"),
                "socialset_remaining": resp.headers.get("X-RateLimit-SocialSet-Remaining"),
                "socialset_reset": resp.headers.get("X-RateLimit-SocialSet-Reset"),
            }

            resp.raise_for_status()
            return resp.json(), rate_limit_info


# ============================================================================
# Scheduling Logic
# ============================================================================

def schedule_posts(
    schedule: GeneratedSchedule,
    client: TypefullyClient,
    social_set_id: str,
    dry_run: bool = False,
    draft_only: bool = False,
    reschedule_past: bool = False,
) -> dict:
    """
    Schedule posts to Typefully.

    Returns:
        Stats dict with created, skipped, failed counts
    """
    stats = {"created": 0, "skipped": 0, "failed": 0}

    # Get existing drafts for duplicate detection
    existing_drafts = []
    if not dry_run:
        try:
            existing_drafts = client.get_drafts(social_set_id, limit=50)
            print(f"  Found {len(existing_drafts)} existing drafts")
        except Exception as e:
            print(f"  Could not fetch existing drafts: {e}")

    # Build signatures for duplicate detection
    existing_signatures = set()
    for draft in existing_drafts:
        preview = draft.get("preview", "")
        if preview:
            existing_signatures.add(preview[:100].strip().lower())

    print(f"\n📅 Scheduling {len(schedule.slots)} posts...")
    print("=" * 60)

    tz = gettz(client.timezone)

    for sp in schedule.slots:
        day_name = sp.slot.datetime.strftime("%A")
        time_str = sp.slot.datetime.strftime("%I:%M %p")
        date_str = sp.slot.datetime.strftime("%b %d")

        # Get content
        content_list = sp.post.get_all_content()
        first_content = content_list[0]

        if sp.post.is_thread:
            preview = f"🧵 Thread ({len(content_list)} tweets)"
        else:
            preview = first_content[:60].replace("\n", " ") + "..."

        content_signature = first_content[:100].strip().lower()

        print(f"\n{day_name}, {date_str} @ {time_str}")
        print(f"  [{sp.post.category}] {preview}")
        print(f"  Source: {sp.post.source_file}")

        # Check for duplicate
        if content_signature in existing_signatures:
            print(f"  ⏭️  SKIPPED: Similar content already exists")
            stats["skipped"] += 1
            continue

        if dry_run:
            print(f"  📝 Would create draft")
            stats["created"] += 1
            existing_signatures.add(content_signature)
            continue

        # Determine publish_at
        if draft_only:
            publish_at = None
            print(f"  📝 Creating as draft (no schedule)")
        else:
            now = datetime.now(tz)
            if sp.slot.datetime < now:
                if reschedule_past:
                    publish_at = "next-free-slot"
                    print(f"  📅 Rescheduling to next free slot (original time was in past)")
                else:
                    publish_at = sp.slot.datetime.isoformat()
            else:
                publish_at = sp.slot.datetime.isoformat()

        # Create draft with retry logic
        max_retries = 5
        for attempt in range(max_retries):
            try:
                result, rate_info = client.create_draft(
                    social_set_id=social_set_id,
                    posts=content_list,
                    publish_at=publish_at,
                    draft_title=f"[Auto] {day_name} {time_str} - {sp.post.category}"
                )

                print(f"  ✓ Created draft: {result.get('id', 'unknown')}")

                remaining = rate_info.get("socialset_remaining") or rate_info.get("user_remaining")
                if remaining:
                    print(f"  [RATE] {remaining} requests remaining")

                stats["created"] += 1
                existing_signatures.add(content_signature)

                # Rate limiting
                if remaining and int(remaining) <= 2:
                    reset_ts = rate_info.get("socialset_reset") or rate_info.get("user_reset")
                    if reset_ts:
                        wait_time = max(int(reset_ts) - int(time.time()) + 5, 60)
                        print(f"  [RATE] Near limit, waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        time.sleep(60)
                else:
                    time.sleep(3)

                break

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    reset_ts = e.response.headers.get("X-RateLimit-SocialSet-Reset") or e.response.headers.get("X-RateLimit-User-Reset")
                    if reset_ts:
                        wait_time = max(int(reset_ts) - int(time.time()) + 5, 30)
                    else:
                        wait_time = (attempt + 1) * 60

                    print(f"  ⏳ Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)

                    if attempt == max_retries - 1:
                        print(f"  ✗ Failed after {max_retries} retries")
                        stats["failed"] += 1
                else:
                    print(f"  ✗ Failed: {e.response.status_code}")
                    stats["failed"] += 1
                    break
            except Exception as e:
                print(f"  ✗ Error: {e}")
                stats["failed"] += 1
                break

    return stats


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Schedule tweets to Typefully from swipe file posts"
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=2,
        help="Number of weeks to schedule (default: 2)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD). Defaults to next Monday."
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default=DEFAULT_TIMEZONE,
        help=f"Timezone (default: {DEFAULT_TIMEZONE})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without creating drafts"
    )
    parser.add_argument(
        "--draft-only",
        action="store_true",
        help="Create as drafts only (no scheduled time)"
    )
    parser.add_argument(
        "--reschedule-past",
        action="store_true",
        help="Use next-free-slot for posts scheduled in the past"
    )
    parser.add_argument(
        "--only",
        action="append",
        dest="include_categories",
        metavar="CATEGORY",
        help="Only include these categories (can be repeated)"
    )
    parser.add_argument(
        "--exclude",
        action="append",
        dest="exclude_categories",
        metavar="CATEGORY",
        help="Exclude these categories (can be repeated)"
    )
    parser.add_argument(
        "--prioritize",
        action="append",
        dest="prioritize_categories",
        metavar="CATEGORY",
        help="Prioritize these categories (can be repeated)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible schedules"
    )
    parser.add_argument(
        "--list-accounts",
        action="store_true",
        help="List connected social accounts and exit"
    )
    parser.add_argument(
        "--social-set-id",
        type=str,
        help="Specific social set ID to use"
    )
    parser.add_argument(
        "--show-categories",
        action="store_true",
        help="Show available categories and exit"
    )

    args = parser.parse_args()

    # Show categories if requested
    if args.show_categories:
        from swipe_file_parser import get_posts_by_category
        posts_by_cat = get_posts_by_category()
        print("📁 Available categories:")
        for cat, posts in sorted(posts_by_cat.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  {cat}: {len(posts)} posts")
        return 0

    # Get API key
    api_key = os.environ.get("TYPEFULLY_API_KEY")
    if not api_key:
        print("ERROR: TYPEFULLY_API_KEY environment variable not set")
        print("\nTo get your API key:")
        print("1. Go to https://typefully.com/settings")
        print("2. Navigate to API section")
        print("3. Generate a new API key")
        print("\nThen run:")
        print('  export TYPEFULLY_API_KEY="your_key_here"')
        return 1

    # Initialize client
    client = TypefullyClient(api_key=api_key, timezone=args.timezone)

    # Test connection
    try:
        user = client.get_me()
        print(f"✓ Connected as: {user.get('name', user.get('email', 'Unknown'))}")
    except httpx.HTTPStatusError as e:
        print(f"ERROR: Failed to authenticate: {e}")
        return 1

    # Get social sets
    social_sets = client.get_social_sets()
    if not social_sets:
        print("ERROR: No connected social accounts found")
        return 1

    # List accounts mode
    if args.list_accounts:
        print("\n📱 Connected Social Accounts:")
        print("-" * 60)
        for ss in social_sets:
            print(f"  ID: {ss['id']}")
            print(f"  Name: {ss.get('name', 'Unknown')}")
            if ss.get('username'):
                print(f"  X Handle: @{ss.get('username')}")
            print()
        return 0

    # Determine social set
    social_set_id = args.social_set_id
    if not social_set_id:
        ss = social_sets[0]
        social_set_id = str(ss["id"])
        x_handle = ss.get('username', 'unknown')
        print(f"✓ Using X account: @{x_handle}")

    # Parse start date
    start_date = None
    if args.start_date:
        start_date = date_parser.parse(args.start_date)
        tz = gettz(args.timezone)
        start_date = start_date.replace(tzinfo=tz)

    # Generate schedule
    print(f"\n🗓️  Generating {args.weeks}-week schedule...")

    schedule = generate_schedule(
        num_weeks=args.weeks,
        start_date=start_date,
        timezone_str=args.timezone,
        include_categories=args.include_categories,
        exclude_categories=args.exclude_categories,
        prioritize_categories=args.prioritize_categories,
        seed=args.seed,
    )

    print(f"✓ Schedule: {schedule.start_date.strftime('%b %d')} - {schedule.end_date.strftime('%b %d, %Y')}")
    print(f"✓ Posts: {schedule.stats['total_posts']} ({schedule.stats['threads']} threads)")
    print(f"✓ Categories: {', '.join(schedule.stats['by_category'].keys())}")

    # Schedule posts
    stats = schedule_posts(
        schedule=schedule,
        client=client,
        social_set_id=social_set_id,
        dry_run=args.dry_run,
        draft_only=args.draft_only,
        reschedule_past=args.reschedule_past,
    )

    # Summary
    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN COMPLETE")
        print(f"  Would create: {stats['created']} drafts")
    else:
        print("SCHEDULING COMPLETE")
        print(f"  Created: {stats['created']} drafts")
        if stats["skipped"] > 0:
            print(f"  Skipped: {stats['skipped']} (already exist)")
        if stats["failed"] > 0:
            print(f"  Failed: {stats['failed']}")

    print(f"\nView your drafts at: https://typefully.com/drafts")

    return 0


if __name__ == "__main__":
    sys.exit(main())
