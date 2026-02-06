#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml>=6.0",
# ]
# ///
"""
Post Tracker

Tracks which posts have been scheduled/published to prevent duplicates
and provide history of what's been posted.

Usage:
    # As a module
    from post_tracker import PostTracker

    tracker = PostTracker()

    # Check if post was already used
    if not tracker.is_used(post_content):
        # Schedule post...
        tracker.mark_used(post_content, platform="typefully", scheduled_date="2026-02-10")

    # Get unused posts from a category
    unused = tracker.get_unused_posts(category="engagement-optimized")

    # As a script
    uv run post_tracker.py --stats
    uv run post_tracker.py --unused --category engagement-optimized
    uv run post_tracker.py --history --limit 20
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PostRecord:
    """Record of a scheduled/published post"""
    signature: str  # Hash of content for matching
    preview: str  # First 80 chars for human readability
    category: str
    source_file: str
    scheduled_date: Optional[str] = None
    published_date: Optional[str] = None
    platform: str = "typefully"
    typefully_draft_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PostRecord":
        return cls(**data)


# ============================================================================
# Tracker
# ============================================================================

class PostTracker:
    """
    Tracks post usage to prevent duplicates and maintain history.

    Storage: JSON file at scripts/marketing/data/post_history.json
    """

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"

        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)

        self.history_file = self.data_dir / "post_history.json"
        self.records: list[PostRecord] = []
        self.signatures: set[str] = set()

        self._load()

    def _load(self):
        """Load existing history from disk"""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    data = json.load(f)
                    self.records = [PostRecord.from_dict(r) for r in data.get("records", [])]
                    self.signatures = set(data.get("signatures", []))
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not load history: {e}")
                self.records = []
                self.signatures = set()
        else:
            self.records = []
            self.signatures = set()

    def _save(self):
        """Save history to disk"""
        data = {
            "updated_at": datetime.utcnow().isoformat(),
            "total_posts": len(self.records),
            "signatures": list(self.signatures),
            "records": [r.to_dict() for r in self.records],
        }
        with open(self.history_file, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def get_signature(content: str) -> str:
        """
        Generate a signature for content matching.
        Uses first 100 chars normalized + hash for collision resistance.
        """
        # Normalize: lowercase, strip whitespace, remove newlines
        normalized = content[:100].lower().strip().replace("\n", " ")
        # Add hash for uniqueness
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{normalized[:60]}|{content_hash}"

    def is_used(self, content: str) -> bool:
        """Check if this content has already been scheduled/published"""
        sig = self.get_signature(content)
        return sig in self.signatures

    def mark_used(
        self,
        content: str,
        category: str,
        source_file: str,
        platform: str = "typefully",
        scheduled_date: Optional[str] = None,
        typefully_draft_id: Optional[str] = None,
    ) -> PostRecord:
        """Mark a post as used (scheduled or published)"""
        sig = self.get_signature(content)

        # Don't duplicate
        if sig in self.signatures:
            # Update existing record if we have new info
            for r in self.records:
                if r.signature == sig:
                    if scheduled_date and not r.scheduled_date:
                        r.scheduled_date = scheduled_date
                    if typefully_draft_id and not r.typefully_draft_id:
                        r.typefully_draft_id = typefully_draft_id
                    self._save()
                    return r

        # Create new record
        record = PostRecord(
            signature=sig,
            preview=content[:80].replace("\n", " "),
            category=category,
            source_file=source_file,
            platform=platform,
            scheduled_date=scheduled_date,
            typefully_draft_id=typefully_draft_id,
        )

        self.records.append(record)
        self.signatures.add(sig)
        self._save()

        return record

    def mark_published(self, content: str, published_date: Optional[str] = None):
        """Mark a post as actually published (not just scheduled)"""
        sig = self.get_signature(content)
        pub_date = published_date or datetime.utcnow().isoformat()

        for r in self.records:
            if r.signature == sig:
                r.published_date = pub_date
                self._save()
                return r

        return None

    def get_unused_signatures(self) -> set[str]:
        """Get all signatures that have been used"""
        return self.signatures.copy()

    def get_history(self, limit: int = 50, category: Optional[str] = None) -> list[PostRecord]:
        """Get recent post history"""
        records = self.records
        if category:
            records = [r for r in records if r.category == category]

        # Sort by created_at descending
        records = sorted(records, key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    def get_stats(self) -> dict:
        """Get statistics about tracked posts"""
        by_category: dict[str, int] = {}
        by_platform: dict[str, int] = {}
        scheduled = 0
        published = 0

        for r in self.records:
            by_category[r.category] = by_category.get(r.category, 0) + 1
            by_platform[r.platform] = by_platform.get(r.platform, 0) + 1
            if r.scheduled_date:
                scheduled += 1
            if r.published_date:
                published += 1

        return {
            "total_tracked": len(self.records),
            "scheduled": scheduled,
            "published": published,
            "by_category": by_category,
            "by_platform": by_platform,
        }

    def clear(self):
        """Clear all tracking data (use with caution)"""
        self.records = []
        self.signatures = set()
        self._save()


# ============================================================================
# Integration helpers
# ============================================================================

def filter_unused_posts(posts: list, tracker: Optional[PostTracker] = None) -> list:
    """
    Filter a list of posts to only those that haven't been used.

    Args:
        posts: List of SwipeFilePost objects (or anything with .content attribute)
        tracker: PostTracker instance (creates new one if None)

    Returns:
        List of unused posts
    """
    if tracker is None:
        tracker = PostTracker()

    return [p for p in posts if not tracker.is_used(p.content)]


def get_unused_by_category(tracker: Optional[PostTracker] = None) -> dict[str, list]:
    """
    Get all unused posts organized by category.

    Returns dict like:
        {
            "engagement-optimized": [post1, post2, ...],
            "agent-problems": [post3, post4, ...],
        }
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from swipe_file_parser import get_posts_by_category

    if tracker is None:
        tracker = PostTracker()

    all_posts = get_posts_by_category()
    unused_by_category = {}

    for category, posts in all_posts.items():
        unused = [p for p in posts if not tracker.is_used(p.content)]
        if unused:
            unused_by_category[category] = unused

    return unused_by_category


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Track post scheduling history")
    parser.add_argument("--stats", action="store_true", help="Show tracking statistics")
    parser.add_argument("--history", action="store_true", help="Show recent history")
    parser.add_argument("--unused", action="store_true", help="Show unused posts")
    parser.add_argument("--category", "-c", help="Filter by category")
    parser.add_argument("--limit", type=int, default=20, help="Limit results")
    parser.add_argument("--clear", action="store_true", help="Clear all tracking data")

    args = parser.parse_args()

    tracker = PostTracker()

    if args.clear:
        confirm = input("Are you sure you want to clear all tracking data? (yes/no): ")
        if confirm.lower() == "yes":
            tracker.clear()
            print("✓ Tracking data cleared")
        else:
            print("Cancelled")
        return 0

    if args.stats:
        stats = tracker.get_stats()
        print("📊 Post Tracking Statistics")
        print(f"   Total tracked: {stats['total_tracked']}")
        print(f"   Scheduled: {stats['scheduled']}")
        print(f"   Published: {stats['published']}")
        print("\n   By category:")
        for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
            print(f"     {cat}: {count}")
        return 0

    if args.history:
        records = tracker.get_history(limit=args.limit, category=args.category)
        print(f"📜 Recent History ({len(records)} posts)")
        for r in records:
            status = "✓ published" if r.published_date else "📅 scheduled" if r.scheduled_date else "📝 tracked"
            print(f"  [{r.category}] {status}: {r.preview[:50]}...")
        return 0

    if args.unused:
        unused = get_unused_by_category(tracker)

        if args.category:
            if args.category in unused:
                posts = unused[args.category][:args.limit]
                print(f"📝 Unused posts in {args.category}: {len(posts)}")
                for p in posts:
                    print(f"  - {p.content[:60].replace(chr(10), ' ')}...")
            else:
                print(f"No unused posts in category: {args.category}")
        else:
            total = sum(len(posts) for posts in unused.values())
            print(f"📝 Unused posts by category (total: {total})")
            for cat, posts in sorted(unused.items(), key=lambda x: -len(x[1])):
                print(f"  {cat}: {len(posts)} unused")
        return 0

    # Default: show summary
    stats = tracker.get_stats()
    unused = get_unused_by_category(tracker)
    total_unused = sum(len(posts) for posts in unused.values())

    print("📊 Post Tracker Summary")
    print(f"   Tracked: {stats['total_tracked']}")
    print(f"   Unused: {total_unused}")
    print(f"   Engagement-optimized unused: {len(unused.get('engagement-optimized', []))}")
    print("\n   Run with --help for more options")

    return 0


if __name__ == "__main__":
    exit(main())
