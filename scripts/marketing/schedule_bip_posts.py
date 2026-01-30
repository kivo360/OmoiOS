#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.25.0",
#     "python-dateutil>=2.8.0",
# ]
# ///
"""
Build in Public Community Scheduler

Schedules specific high-engagement posts to the Build in Public X community.
These posts are selected for maximum engagement in the BIP community.

Usage:
    # Preview the schedule
    uv run schedule_bip_posts.py --dry-run

    # Schedule all BIP posts
    uv run schedule_bip_posts.py

    # Start from specific date
    uv run schedule_bip_posts.py --start-date 2026-02-03

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
import argparse

# ============================================================================
# Configuration
# ============================================================================

TYPEFULLY_API_BASE = "https://api.typefully.com/v2"
DEFAULT_TIMEZONE = "America/Asuncion"

# Build in Public community ID
BIP_COMMUNITY_ID = "1493446837214187523"

# Posts optimized for Build in Public community
# Selected based on: launch stories, real numbers, honest failures, lessons learned
BIP_POSTS = [
    # Launch Stories (highest engagement in BIP)
    {
        "content": """launched 10 days ago.

for weeks i was convinced people would hate it.

"it's not ready"
"they'll tear it apart"
"who do you think you are"

hit publish. braced for impact.

first response? a stranger saying "congrats on the launch."

i broke down. actual tears.

all that fear. all that mental warfare.

and the first feedback was kindness.

the fear was a liar.

if you're holding back because you think people will hate you: you're probably wrong too.""",
        "title": "The Fear Was a Liar",
        "day": 0,  # Monday
        "time": "20:00",  # Golden hour
    },
    {
        "content": """10 days post-launch. real numbers:

- mass hate received: 0
- useful feedback: 12 messages
- strangers who said congrats: 8
- people who tried it: 47
- bugs reported: 3 (all fixed)
- times i almost didn't launch: infinite

the fear was never about the product.

it was about me.""",
        "title": "Real Launch Numbers",
        "day": 1,  # Tuesday
        "time": "20:00",
    },
    {
        "content": """launch day confession:

i almost didn't hit publish.

had my finger on the button for 20 minutes.

"one more feature"
"fix that edge case"
"maybe next week"

shipped anyway.

10 days later: zero regrets.

the version that exists beats the perfect version that doesn't.""",
        "title": "Launch Day Confession",
        "day": 2,  # Wednesday
        "time": "20:00",
    },

    # Failure Stories with Numbers (BIP loves honest metrics)
    {
        "content": """woke up to a $340 API bill

one agent, one night, one rabbit hole

it kept calling the LLM asking "is this right?"
the LLM kept saying "try this instead"
loop continued for 8 hours

now we have budget limits per task

expensive lessons are the ones you remember""",
        "title": "$340 API Bill Story",
        "day": 3,  # Thursday
        "time": "20:00",
    },
    {
        "content": """did the math on our ai coding experiment.

3 months. 4 engineers using cursor daily.

actual results:
- individual coding: 1.4x faster
- pr review time: 2.3x longer
- bugs caught in staging: up 47%
- net velocity: roughly flat

we didn't get 10x. we got different.

nobody talks about this because it's not a good headline.""",
        "title": "Real AI Coding Numbers",
        "day": 4,  # Friday
        "time": "20:00",
    },

    # Lessons Learned (classic BIP format)
    {
        "content": """what i learned from launching 10 days ago:

1. nobody cares as much as you think (liberating)
2. the critics in your head are louder than real ones
3. "not ready" is a feeling, not a fact
4. shipping is a skill separate from building
5. the first person to support you hits different

stop waiting. start learning.""",
        "title": "Launch Lessons",
        "day": 5,  # Saturday
        "time": "12:00",
    },
    {
        "content": """agent started a "small refactor" yesterday.

14 files changed.
3 "temporary" workarounds.
tests disabled with TODO comments.
build broken for 2 hours.

the original task was adding a button.

i don't blame the agent.
i blame myself for not constraining it.""",
        "title": "Small Refactor Disaster",
        "day": 6,  # Sunday
        "time": "12:00",
    },

    # Engagement Questions for Builders
    {
        "content": """builders who've launched:

how long did you delay because of fear?

1 week? 1 month? 1 year?

trying to normalize that we all do this.

i delayed 3 weeks. shipped 10 days ago. wish i'd done it sooner.""",
        "title": "Launch Fear Question",
        "day": 2,  # Wednesday
        "time": "12:00",
    },
    {
        "content": """why most builders don't ship:

10% - technical blockers
10% - time constraints
80% - fear of judgment

the code is ready.
the product works.
the finger hovers over publish.

and then... "maybe one more feature."

recognize this? yeah. me too.""",
        "title": "Why Builders Don't Ship",
        "day": 4,  # Friday
        "time": "12:00",
    },
    {
        "content": """what's stopping you from shipping right now?

not the excuse. the real reason.

for me it was fear of looking stupid.

shipped anyway. 10 days ago.

nobody called me stupid. a few people said thanks.

your turn. what's actually stopping you?""",
        "title": "Ship It Question",
        "day": 6,  # Sunday
        "time": "18:00",
    },
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
        posts: list[str],
        publish_at: str | None = None,
        draft_title: str | None = None,
        community_id: str | None = None,
        share_with_followers: bool = True,
    ) -> tuple[dict, dict]:
        """Create a new draft, optionally posting to an X community"""
        x_posts = [{"text": text, "media_ids": []} for text in posts]

        x_settings = {}
        if community_id:
            x_settings["community_id"] = community_id
            x_settings["share_with_followers"] = share_with_followers

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

            rate_limit_info = {
                "remaining": resp.headers.get("X-RateLimit-SocialSet-Remaining") or resp.headers.get("X-RateLimit-User-Remaining"),
                "reset": resp.headers.get("X-RateLimit-SocialSet-Reset") or resp.headers.get("X-RateLimit-User-Reset"),
            }

            resp.raise_for_status()
            return resp.json(), rate_limit_info


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Schedule Build in Public community posts")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--timezone", type=str, default=DEFAULT_TIMEZONE)
    parser.add_argument("--draft-only", action="store_true", help="Create as drafts only")
    parser.add_argument("--no-community", action="store_true", help="Post without community (regular posts)")
    args = parser.parse_args()

    # Get API key
    api_key = os.environ.get("TYPEFULLY_API_KEY")
    if not api_key:
        print("ERROR: TYPEFULLY_API_KEY not set")
        sys.exit(1)

    client = TypefullyClient(api_key=api_key, timezone=args.timezone)

    # Test connection
    try:
        user = client.get_me()
        print(f"Connected as: {user.get('name', user.get('email', 'Unknown'))}")
    except httpx.HTTPStatusError as e:
        print(f"ERROR: Auth failed: {e}")
        sys.exit(1)

    # Get social set
    social_sets = client.get_social_sets()
    if not social_sets:
        print("ERROR: No social accounts")
        sys.exit(1)

    social_set_id = str(social_sets[0]["id"])
    x_handle = social_sets[0].get('username', 'unknown')
    print(f"Using: @{x_handle}")

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

    print(f"Schedule starts: {start_date.strftime('%A, %B %d, %Y')}")

    community_id = None if args.no_community else BIP_COMMUNITY_ID
    if community_id:
        print(f"Posting to Build in Public community: {community_id}")

    print(f"\nScheduling {len(BIP_POSTS)} Build in Public posts...")
    print("=" * 60)

    # Get existing drafts for duplicate detection
    existing_signatures = set()
    if not args.dry_run:
        try:
            drafts = client.get_drafts(social_set_id, limit=50)
            for d in drafts:
                preview = d.get("preview", "")
                if preview:
                    existing_signatures.add(preview[:100].strip().lower())
            print(f"Found {len(drafts)} existing drafts")
        except Exception as e:
            print(f"Could not fetch drafts: {e}")

    created = 0
    skipped = 0
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for post in BIP_POSTS:
        post_date = start_date + timedelta(days=post["day"])
        hour, minute = map(int, post["time"].split(":"))
        post_datetime = post_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

        day_name = days[post["day"]]
        time_str = post_datetime.strftime("%I:%M %p")
        date_str = post_datetime.strftime("%b %d")
        preview = post["content"][:60].replace("\n", " ") + "..."

        print(f"\n{day_name}, {date_str} @ {time_str}")
        print(f"  [{post['title']}] {preview}")
        if community_id:
            print(f"  -> Build in Public community")

        # Check duplicate
        sig = post["content"][:100].strip().lower()
        if sig in existing_signatures:
            print(f"  SKIPPED: Already exists")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  [DRY RUN] Would create")
            created += 1
            continue

        # Create draft
        try:
            if args.draft_only:
                publish_at = None
            else:
                now = datetime.now(tz)
                publish_at = "next-free-slot" if post_datetime < now else post_datetime.isoformat()

            result, rate_info = client.create_draft(
                social_set_id=social_set_id,
                posts=[post["content"]],
                publish_at=publish_at,
                draft_title=f"[BIP] {post['title']}",
                community_id=community_id,
                share_with_followers=True,
            )

            print(f"  Created: {result.get('id', 'OK')}")
            created += 1
            existing_signatures.add(sig)

            # Rate limiting
            remaining = rate_info.get("remaining")
            if remaining:
                remaining = int(remaining)
                if remaining <= 2:
                    reset_ts = rate_info.get("reset")
                    wait_time = max(int(reset_ts) - int(time.time()) + 5, 60) if reset_ts else 60
                    print(f"  Waiting {wait_time}s for rate limit...")
                    time.sleep(wait_time)
                else:
                    time.sleep(3)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                print(f"  Rate limited! Try again later.")
                break
            else:
                print(f"  ERROR: {e.response.status_code}")

    print("\n" + "=" * 60)
    if args.dry_run:
        print(f"DRY RUN: Would create {created} posts")
    else:
        print(f"Created: {created}, Skipped: {skipped}")
    print(f"\nView drafts: https://typefully.com/drafts")


if __name__ == "__main__":
    main()
