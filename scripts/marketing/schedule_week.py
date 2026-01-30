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
Unified Weekly Tweet Scheduler

Reads posts from swipe_file/*.md and schedules them:
- Regular feed posts (all content types)
- Build in Public community posts (launch stories, failures, builder content)

No overlap - each post goes to exactly one destination.

Usage:
    # Preview 1 week
    uv run schedule_week.py --dry-run

    # Preview 2 weeks
    uv run schedule_week.py --weeks 2 --dry-run

    # Schedule 1 week for real
    uv run schedule_week.py

    # Schedule 2 weeks
    uv run schedule_week.py --weeks 2

    # Custom start date
    uv run schedule_week.py --start-date 2026-02-03

    # Skip BIP community (regular posts only)
    uv run schedule_week.py --no-bip

Environment:
    TYPEFULLY_API_KEY - Your Typefully API key (required)
"""

import os
import sys
import time
import httpx
from datetime import datetime, timedelta
from dateutil.tz import gettz
from dateutil import parser as date_parser
from pathlib import Path
import argparse

# Import swipe file parser
sys.path.insert(0, str(Path(__file__).parent))
from swipe_file_parser import get_posts_by_category, SwipeFilePost

# ============================================================================
# Configuration
# ============================================================================

TYPEFULLY_API_BASE = "https://api.typefully.com/v2"
DEFAULT_TIMEZONE = "America/Asuncion"
BIP_COMMUNITY_ID = "1493446837214187523"

# Time slots based on engagement data
# Peak: 8pm-10pm, 5pm-7pm | Good: 9am-10am, 12pm-1pm
WEEKDAY_SLOTS = ["09:00", "12:00", "17:00", "19:00", "20:00"]
WEEKEND_SLOTS = ["10:00", "12:00", "18:00", "20:00"]

# Categories that go to Build in Public community (at 8pm golden hour)
BIP_CATEGORIES = {
    "engagement-optimized",  # Launch stories, failures with numbers
    "build-in-public",
    "failure-stories",
    "stories",
}

# Keywords in content that indicate BIP-worthy posts
BIP_KEYWORDS = [
    "launched", "launch", "shipped", "shipping",
    "10 days", "post-launch", "fear was",
    "builders who", "why most builders",
    "what i learned", "lessons",
]


# ============================================================================
# Typefully Client
# ============================================================================

class TypefullyClient:
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
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{self.base_url}/me", headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    def get_social_sets(self) -> list[dict]:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{self.base_url}/social-sets", headers=self._headers())
            resp.raise_for_status()
            return resp.json().get("results", [])

    def get_drafts(self, social_set_id: str, limit: int = 50) -> list[dict]:
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
        content: str | list[str],
        publish_at: str | None = None,
        draft_title: str | None = None,
        community_id: str | None = None,
    ) -> tuple[dict, dict]:
        # Handle threads (list of strings) vs single posts
        if isinstance(content, list):
            x_posts = [{"text": text, "media_ids": []} for text in content]
        else:
            x_posts = [{"text": content, "media_ids": []}]

        x_settings = {}
        if community_id:
            x_settings["community_id"] = community_id
            x_settings["share_with_followers"] = True

        payload = {
            "platforms": {
                "x": {
                    "enabled": True,
                    "posts": x_posts,
                    "settings": x_settings
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

            rate_info = {
                "remaining": resp.headers.get("X-RateLimit-SocialSet-Remaining") or resp.headers.get("X-RateLimit-User-Remaining"),
                "reset": resp.headers.get("X-RateLimit-SocialSet-Reset") or resp.headers.get("X-RateLimit-User-Reset"),
            }

            resp.raise_for_status()
            return resp.json(), rate_info


# ============================================================================
# Post Classification
# ============================================================================

def is_bip_post(post: SwipeFilePost) -> bool:
    """Determine if a post should go to Build in Public community"""
    # Check category
    if post.category in BIP_CATEGORIES:
        # Check for BIP keywords in content
        content_lower = post.content.lower()
        for keyword in BIP_KEYWORDS:
            if keyword in content_lower:
                return True
    return False


def load_posts_from_swipe_files(prioritize_engagement: bool = True) -> tuple[list[SwipeFilePost], list[SwipeFilePost]]:
    """
    Load posts from swipe files and separate into BIP and regular.

    Returns:
        (bip_posts, regular_posts)
    """
    posts_by_category = get_posts_by_category()

    bip_posts = []
    regular_posts = []

    # Prioritize engagement-optimized if requested
    if prioritize_engagement and "engagement-optimized" in posts_by_category:
        for post in posts_by_category["engagement-optimized"]:
            if is_bip_post(post):
                bip_posts.append(post)
            else:
                regular_posts.append(post)
        # Remove from dict so we don't double-add
        del posts_by_category["engagement-optimized"]

    # Process remaining categories
    for category, posts in posts_by_category.items():
        for post in posts:
            if is_bip_post(post):
                bip_posts.append(post)
            else:
                regular_posts.append(post)

    return bip_posts, regular_posts


# ============================================================================
# Schedule Builder
# ============================================================================

def build_schedule(
    start_date: datetime,
    num_weeks: int = 1,
    include_bip: bool = True,
    prioritize_engagement: bool = True,
) -> list[dict]:
    """
    Build a unified schedule for the specified number of weeks.

    Strategy:
    - BIP posts go at 8pm (golden hour) - best engagement time
    - Regular posts fill remaining slots
    - No overlap - each slot has exactly one post
    """
    # Load posts from markdown files
    bip_posts, regular_posts = load_posts_from_swipe_files(prioritize_engagement)

    print(f"✓ Loaded {len(bip_posts)} BIP posts, {len(regular_posts)} regular posts from swipe files")

    schedule = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # Build all time slots for the weeks
    all_slots = []
    total_days = num_weeks * 7

    for day_idx in range(total_days):
        day_date = start_date + timedelta(days=day_idx)
        day_of_week = day_idx % 7
        slots = WEEKEND_SLOTS if day_of_week >= 5 else WEEKDAY_SLOTS

        for time_str in slots:
            hour, minute = map(int, time_str.split(":"))
            slot_dt = day_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            all_slots.append({
                "datetime": slot_dt,
                "day_idx": day_idx,
                "day_of_week": day_of_week,
                "day_name": days[day_of_week],
                "time": time_str,
            })

    # Sort slots by datetime
    all_slots.sort(key=lambda x: x["datetime"])

    # Create queues (copy so we don't modify originals)
    bip_queue = list(bip_posts) if include_bip else []
    regular_queue = list(regular_posts)

    # Track used content to avoid duplicates
    used_content = set()

    for slot in all_slots:
        if not bip_queue and not regular_queue:
            break

        post = None
        community_id = None
        destination = "Feed"

        # 8pm slots get BIP posts (if available and BIP enabled)
        if slot["time"] == "20:00" and bip_queue and include_bip:
            post = bip_queue.pop(0)
            community_id = BIP_COMMUNITY_ID
            destination = "BIP"
        # All other slots get regular posts
        elif regular_queue:
            post = regular_queue.pop(0)
        # If out of regular posts, use remaining BIP posts for feed
        elif bip_queue:
            post = bip_queue.pop(0)
            if include_bip:
                community_id = BIP_COMMUNITY_ID
                destination = "BIP"

        if post:
            # Skip if we've already used this content
            content_sig = post.content[:100].lower()
            if content_sig in used_content:
                continue
            used_content.add(content_sig)

            # Get content (handle threads)
            if post.is_thread:
                content = post.get_all_content()
            else:
                content = post.content

            schedule.append({
                **slot,
                "content": content,
                "title": post.title or post.content[:30].replace("\n", " ") + "...",
                "category": post.category,
                "community_id": community_id,
                "destination": destination,
                "is_thread": post.is_thread,
            })

    return schedule


# ============================================================================
# Main
# ============================================================================

def log(msg: str, flush: bool = True):
    """Print with immediate flush for real-time output"""
    print(msg, flush=flush)


def main():
    parser = argparse.ArgumentParser(description="Schedule posts from swipe files")
    parser.add_argument("--weeks", type=int, default=1, help="Number of weeks to schedule (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD), defaults to next Monday")
    parser.add_argument("--timezone", type=str, default=DEFAULT_TIMEZONE)
    parser.add_argument("--draft-only", action="store_true", help="Create as drafts only (no schedule)")
    parser.add_argument("--no-bip", action="store_true", help="Skip Build in Public community posts")
    parser.add_argument("--no-engagement-priority", action="store_true", help="Don't prioritize engagement-optimized posts")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    log("🚀 Starting scheduler...")

    # Get API key
    log("📋 Checking API key...")
    api_key = os.environ.get("TYPEFULLY_API_KEY")
    if not api_key:
        log("ERROR: TYPEFULLY_API_KEY not set")
        log("  export TYPEFULLY_API_KEY='your_key_here'")
        sys.exit(1)
    log("✓ API key found")

    log("🔌 Connecting to Typefully API...")
    client = TypefullyClient(api_key=api_key, timezone=args.timezone)

    # Test connection
    try:
        log("  → Calling /me endpoint...")
        user = client.get_me()
        log(f"✓ Connected as: {user.get('name', user.get('email', 'Unknown'))}")
    except httpx.HTTPStatusError as e:
        log(f"ERROR: Auth failed: {e}")
        sys.exit(1)

    # Get social set
    log("📱 Fetching social accounts...")
    social_sets = client.get_social_sets()
    if not social_sets:
        log("ERROR: No social accounts connected")
        sys.exit(1)

    social_set_id = str(social_sets[0]["id"])
    x_handle = social_sets[0].get('username', 'unknown')
    log(f"✓ Using: @{x_handle} (ID: {social_set_id})")

    # Determine start date
    tz = gettz(args.timezone)
    if args.start_date:
        start_date = date_parser.parse(args.start_date).replace(tzinfo=tz)
    else:
        today = datetime.now(tz)
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        start_date = today + timedelta(days=days_until_monday)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    end_date = start_date + timedelta(days=args.weeks * 7 - 1)
    log(f"✓ Schedule: {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')} ({args.weeks} week{'s' if args.weeks > 1 else ''})")
    log(f"✓ Timezone: {args.timezone}")

    # Build schedule
    log("\n📚 Loading posts from swipe files...")
    include_bip = not args.no_bip
    prioritize_engagement = not args.no_engagement_priority

    schedule = build_schedule(
        start_date,
        num_weeks=args.weeks,
        include_bip=include_bip,
        prioritize_engagement=prioritize_engagement,
    )

    bip_count = sum(1 for s in schedule if s["destination"] == "BIP")
    feed_count = sum(1 for s in schedule if s["destination"] == "Feed")
    thread_count = sum(1 for s in schedule if s.get("is_thread"))

    log(f"\n📅 Schedule: {len(schedule)} posts total")
    log(f"   - Regular feed: {feed_count}")
    log(f"   - Build in Public: {bip_count}")
    log(f"   - Threads: {thread_count}")
    log("=" * 70)

    # Get existing drafts for duplicate detection
    log("\n🔍 Checking for existing drafts...")
    existing_signatures = set()
    if not args.dry_run:
        try:
            drafts = client.get_drafts(social_set_id, limit=50)
            for d in drafts:
                preview = d.get("preview", "")
                if preview:
                    existing_signatures.add(preview[:80].strip().lower())
            log(f"✓ Found {len(drafts)} existing drafts")
        except Exception as e:
            log(f"  Could not fetch drafts: {e}")

    # Schedule posts
    log("\n🚀 Starting to create drafts...")
    created = 0
    skipped = 0
    failed = 0
    current_day = None
    total_posts = len(schedule)

    for idx, item in enumerate(schedule, 1):
        # Print day header
        day_str = item["datetime"].strftime("%A, %b %d")
        if day_str != current_day:
            current_day = day_str
            log(f"\n📆 {day_str}")

        time_str = item["datetime"].strftime("%I:%M %p")

        # Get preview text
        content = item["content"]
        if isinstance(content, list):
            preview = f"🧵 Thread ({len(content)} parts): {content[0][:40]}..."
        else:
            preview = content[:50].replace("\n", " ") + "..."

        dest_marker = "🏠" if item["destination"] == "BIP" else "📢"

        log(f"  [{idx}/{total_posts}] {time_str} {dest_marker} [{item['category']}] {preview}")

        # Check duplicate
        if isinstance(content, list):
            sig = content[0][:80].strip().lower()
        else:
            sig = content[:80].strip().lower()

        if sig in existing_signatures:
            log(f"           ⏭️  SKIPPED (duplicate)")
            skipped += 1
            continue

        if args.dry_run:
            log(f"           ✓ Would create")
            created += 1
            continue

        # Create draft
        try:
            if args.draft_only:
                publish_at = None
            else:
                now = datetime.now(tz)
                publish_at = "next-free-slot" if item["datetime"] < now else item["datetime"].isoformat()

            prefix = "[BIP]" if item["community_id"] else "[Feed]"
            log(f"           → Creating draft...")

            result, rate_info = client.create_draft(
                social_set_id=social_set_id,
                content=item["content"],
                publish_at=publish_at,
                draft_title=f"{prefix} {item['title'][:40]}",
                community_id=item["community_id"],
            )

            draft_id = result.get('id', 'OK')
            log(f"           ✓ Created: {draft_id}")
            created += 1
            existing_signatures.add(sig)

            # Rate limiting
            remaining = rate_info.get("remaining")
            if remaining:
                remaining = int(remaining)
                log(f"           📊 Rate limit: {remaining} remaining")
                if remaining <= 2:
                    reset_ts = rate_info.get("reset")
                    wait_time = max(int(reset_ts) - int(time.time()) + 5, 60) if reset_ts else 60
                    log(f"           ⏳ Near rate limit, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    time.sleep(2)  # Small delay between requests

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                log(f"           ❌ Rate limited! Status: 429")
                log(f"           Headers: {dict(e.response.headers)}")
                failed += 1
                break
            else:
                log(f"           ❌ ERROR: {e.response.status_code}")
                log(f"           Response: {e.response.text[:200]}")
                failed += 1
        except Exception as e:
            log(f"           ❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
            failed += 1

    # Summary
    log("\n" + "=" * 70)
    if args.dry_run:
        log(f"🔍 DRY RUN COMPLETE")
        log(f"   Would create: {created} posts ({feed_count} feed, {bip_count} BIP)")
    else:
        log(f"✅ SCHEDULING COMPLETE")
        log(f"   Created: {created}")
        log(f"   Skipped: {skipped} (duplicates)")
        if failed:
            log(f"   Failed: {failed}")

    log(f"\n🔗 View drafts: https://typefully.com/drafts")
    log(f"🏁 Done!")


if __name__ == "__main__":
    main()
