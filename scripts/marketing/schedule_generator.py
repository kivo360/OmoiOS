#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml>=6.0",
#     "python-dateutil>=2.8.0",
# ]
# ///
"""
Schedule Generator

Generates a mixed schedule from swipe file posts, respecting scheduling rules
and ensuring good content variety.

Usage:
    # Generate a 2-week schedule
    uv run schedule_generator.py --weeks 2

    # Generate starting from a specific date
    uv run schedule_generator.py --weeks 2 --start-date 2026-01-20

    # Include specific categories
    uv run schedule_generator.py --weeks 2 --include raw-unclean --include hot-takes

    # Prioritize certain categories (more posts from these)
    uv run schedule_generator.py --weeks 2 --prioritize raw-unclean

    # Output as JSON for the scheduler
    uv run schedule_generator.py --weeks 2 --output schedule.json
"""

import json
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dateutil.tz import gettz

from swipe_file_parser import (
    parse_all_posts,
    get_posts_by_category,
    SwipeFilePost,
    get_swipe_file_dir,
)


# ============================================================================
# Schedule Slot Configuration
# ============================================================================

# Default posting schedule based on actual engagement data (America/Asuncion timezone)
# Peak hours: 8pm-10pm (highest), 5pm-7pm (strong), 9am-10am (morning), 12pm-1pm (lunch)
# Dead zones: 2am-6am, 11am, 2pm-4pm
WEEKDAY_SLOTS = ["09:00", "12:00", "17:00", "19:00", "20:00"]  # 3 posts in peak evening window
WEEKEND_SLOTS = ["10:00", "12:00", "18:00", "20:00"]

# Category priority for each time slot (preferred categories)
# Niche: Navigating the Singularity — AI, institutional collapse, positioning, consciousness
SLOT_PREFERENCES = {
    "09:00": ["practical-moves", "ai-reality-check", "stories-and-experiences"],  # Morning: actionable + credibility
    "10:00": ["hot-takes", "consciousness-and-meaning", "stories-and-experiences"],  # Weekend morning
    "11:00": ["threads"],  # Sunday threads
    "12:00": ["ai-reality-check", "economic-reality", "practical-moves", "engagement-questions"],  # Lunch: meaty content
    "17:00": ["engagement-questions", "hot-takes", "institutional-collapse", "practical-moves"],  # Start of peak: conversation starters
    "18:00": ["hot-takes", "stories-and-experiences", "geopolitics-decoded"],  # Weekend evening start
    "19:00": ["institutional-collapse", "hot-takes", "economic-reality", "stories-and-experiences"],  # Building to peak
    "20:00": ["hot-takes", "stories-and-experiences", "consciousness-and-meaning", "practical-moves"],  # GOLDEN HOUR
}

# Day preferences for categories
DAY_PREFERENCES = {
    "monday": ["practical-moves", "ai-reality-check", "engagement-questions"],  # Start week with action + AI insider
    "tuesday": ["stories-and-experiences", "institutional-collapse", "economic-reality"],  # Stories + hard truths
    "wednesday": ["ai-reality-check", "geopolitics-decoded", "engagement-questions"],  # Tech + geopolitics
    "thursday": ["hot-takes", "economic-reality", "institutional-collapse"],  # Opinions + economics
    "friday": ["stories-and-experiences", "practical-moves", "consciousness-and-meaning"],  # Stories + meaning
    "saturday": ["hot-takes", "consciousness-and-meaning", "geopolitics-decoded"],  # Weekend: bigger ideas
    "sunday": ["threads", "consciousness-and-meaning", "hot-takes"],  # Deep dives + reflection
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ScheduleSlot:
    """A single slot in the schedule"""
    datetime: datetime
    day_name: str
    time: str
    preferred_categories: list[str]


@dataclass
class ScheduledPost:
    """A post assigned to a schedule slot"""
    post: SwipeFilePost
    slot: ScheduleSlot

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "day_offset": (self.slot.datetime - self.slot.datetime.replace(hour=0, minute=0, second=0, microsecond=0)).days,
            "time": self.slot.time,
            "content": self.post.get_all_content() if self.post.is_thread else self.post.content,
            "source": self.post.source_file,
            "is_thread": self.post.is_thread,
            "category": self.post.category,
            "title": self.post.title,
        }


@dataclass
class GeneratedSchedule:
    """A complete generated schedule"""
    start_date: datetime
    end_date: datetime
    slots: list[ScheduledPost]
    stats: dict = field(default_factory=dict)

    def to_json(self) -> str:
        """Export as JSON"""
        return json.dumps({
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_posts": len(self.slots),
            "stats": self.stats,
            "posts": [s.to_dict() for s in self.slots],
        }, indent=2)


# ============================================================================
# Schedule Generation
# ============================================================================

def generate_slots(
    start_date: datetime,
    num_weeks: int,
    timezone_str: str = "America/Asuncion",
) -> list[ScheduleSlot]:
    """Generate all schedule slots for the given period"""
    tz = gettz(timezone_str)
    slots = []

    for day_offset in range(num_weeks * 7):
        current_date = start_date + timedelta(days=day_offset)
        day_name = current_date.strftime("%A").lower()

        # Choose time slots based on weekday/weekend
        if day_name in ("saturday", "sunday"):
            time_slots = WEEKEND_SLOTS.copy()
            # Add thread slot on Sunday
            if day_name == "sunday":
                time_slots = ["11:00"] + time_slots  # Thread slot first
        else:
            time_slots = WEEKDAY_SLOTS.copy()

        for time_str in time_slots:
            hour, minute = map(int, time_str.split(":"))
            slot_datetime = current_date.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
                tzinfo=tz,
            )

            # Get preferred categories for this slot
            time_prefs = SLOT_PREFERENCES.get(time_str, [])
            day_prefs = DAY_PREFERENCES.get(day_name, [])

            # Combine preferences (time prefs first, then day prefs)
            preferred = []
            for cat in time_prefs:
                if cat not in preferred:
                    preferred.append(cat)
            for cat in day_prefs:
                if cat not in preferred:
                    preferred.append(cat)

            slots.append(ScheduleSlot(
                datetime=slot_datetime,
                day_name=day_name,
                time=time_str,
                preferred_categories=preferred,
            ))

    return slots


def select_post_for_slot(
    slot: ScheduleSlot,
    available_posts: dict[str, list[SwipeFilePost]],
    used_posts: set[str],
    recent_categories: list[str],
    category_counts: dict[str, int],
    prioritize_categories: Optional[list[str]] = None,
) -> Optional[SwipeFilePost]:
    """
    Select the best post for a given slot.

    Considers:
    - Slot preferences (time/day)
    - Category scheduling rules
    - Avoiding back-to-back same category
    - Not reusing posts
    - Priority categories get more slots
    """
    # Build candidate list with scores
    candidates: list[tuple[SwipeFilePost, float]] = []

    for category, posts in available_posts.items():
        for post in posts:
            # Skip already used posts
            post_id = f"{post.source_file}:{post.content[:50]}"
            if post_id in used_posts:
                continue

            # Calculate score
            score = 1.0

            # Prefer posts from preferred categories for this slot
            if category in slot.preferred_categories:
                pref_idx = slot.preferred_categories.index(category)
                score += (10 - pref_idx) * 0.5  # Higher score for earlier in preference list

            # Check if category is good for this day
            sched = post.scheduling
            if sched.best_days:
                if slot.day_name in sched.best_days:
                    score += 3.0
                else:
                    score -= 2.0  # Penalty for wrong day

            # Check if time is good for this category
            if sched.best_times:
                if slot.time in sched.best_times:
                    score += 2.0

            # Penalty for back-to-back same category
            if recent_categories and category == recent_categories[-1]:
                score -= 5.0
            if len(recent_categories) >= 2 and category == recent_categories[-2]:
                score -= 2.0

            # Bonus for prioritized categories
            if prioritize_categories and category in prioritize_categories:
                score += 4.0

            # Penalty if we've used too many from this category already
            max_per_week = sched.max_per_week
            week_num = slot.datetime.isocalendar()[1]
            weekly_key = f"{category}:week{week_num}"
            if category_counts.get(weekly_key, 0) >= max_per_week:
                score -= 10.0  # Strong penalty

            # Thread slots (11:00 Sunday) should strongly prefer threads
            if slot.time == "11:00" and slot.day_name == "sunday":
                if post.is_thread:
                    score += 10.0
                else:
                    score -= 5.0

            # Non-thread slots should avoid threads
            if slot.time != "11:00" and post.is_thread:
                score -= 8.0

            candidates.append((post, score))

    if not candidates:
        return None

    # Sort by score (highest first) and pick from top candidates with some randomness
    candidates.sort(key=lambda x: x[1], reverse=True)

    # Take top 3 candidates and randomly pick one (adds variety)
    top_candidates = candidates[:3]
    if len(top_candidates) == 1:
        return top_candidates[0][0]

    # Weight by score
    total_score = sum(max(0.1, c[1]) for c in top_candidates)
    r = random.random() * total_score
    cumulative = 0
    for post, score in top_candidates:
        cumulative += max(0.1, score)
        if r <= cumulative:
            return post

    return top_candidates[0][0]


def generate_schedule(
    num_weeks: int = 2,
    start_date: Optional[datetime] = None,
    timezone_str: str = "America/Asuncion",
    include_categories: Optional[list[str]] = None,
    exclude_categories: Optional[list[str]] = None,
    prioritize_categories: Optional[list[str]] = None,
    seed: Optional[int] = None,
) -> GeneratedSchedule:
    """
    Generate a complete schedule for the given period.

    Args:
        num_weeks: Number of weeks to generate
        start_date: Start date (defaults to next Monday)
        timezone_str: Timezone for scheduling
        include_categories: Only use these categories (None = all)
        exclude_categories: Exclude these categories
        prioritize_categories: Give these categories more slots
        seed: Random seed for reproducibility

    Returns:
        GeneratedSchedule with all assigned posts
    """
    if seed is not None:
        random.seed(seed)

    tz = gettz(timezone_str)

    # Determine start date (next Monday if not specified)
    if start_date is None:
        today = datetime.now(tz)
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        start_date = today + timedelta(days=days_until_monday)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Generate all slots
    slots = generate_slots(start_date, num_weeks, timezone_str)

    # Get all posts by category
    posts_by_category = get_posts_by_category()

    # Apply category filters
    if include_categories:
        posts_by_category = {k: v for k, v in posts_by_category.items() if k in include_categories}
    if exclude_categories:
        posts_by_category = {k: v for k, v in posts_by_category.items() if k not in exclude_categories}

    # Track state
    used_posts: set[str] = set()
    recent_categories: list[str] = []
    category_counts: dict[str, int] = defaultdict(int)
    scheduled_posts: list[ScheduledPost] = []

    # Fill each slot
    for slot in slots:
        post = select_post_for_slot(
            slot=slot,
            available_posts=posts_by_category,
            used_posts=used_posts,
            recent_categories=recent_categories,
            category_counts=category_counts,
            prioritize_categories=prioritize_categories,
        )

        if post is None:
            print(f"Warning: No suitable post found for {slot.day_name} {slot.time}")
            continue

        # Mark as used
        post_id = f"{post.source_file}:{post.content[:50]}"
        used_posts.add(post_id)

        # Update tracking
        recent_categories.append(post.category)
        if len(recent_categories) > 5:
            recent_categories.pop(0)

        week_num = slot.datetime.isocalendar()[1]
        category_counts[f"{post.category}:week{week_num}"] += 1
        category_counts[post.category] += 1

        scheduled_posts.append(ScheduledPost(post=post, slot=slot))

    # Calculate stats
    stats = {
        "total_posts": len(scheduled_posts),
        "by_category": defaultdict(int),
        "threads": 0,
        "by_day": defaultdict(int),
    }
    for sp in scheduled_posts:
        stats["by_category"][sp.post.category] += 1
        stats["by_day"][sp.slot.day_name] += 1
        if sp.post.is_thread:
            stats["threads"] += 1

    stats["by_category"] = dict(stats["by_category"])
    stats["by_day"] = dict(stats["by_day"])

    return GeneratedSchedule(
        start_date=start_date,
        end_date=start_date + timedelta(days=num_weeks * 7 - 1),
        slots=scheduled_posts,
        stats=stats,
    )


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate a mixed schedule from swipe file posts")
    parser.add_argument("--weeks", type=int, default=2, help="Number of weeks to generate (default: 2)")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD, defaults to next Monday)")
    parser.add_argument("--timezone", type=str, default="America/Asuncion", help="Timezone")
    parser.add_argument("--include", action="append", dest="include_categories", help="Only include these categories")
    parser.add_argument("--exclude", action="append", dest="exclude_categories", help="Exclude these categories")
    parser.add_argument("--prioritize", action="append", dest="prioritize_categories", help="Prioritize these categories")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--output", "-o", type=Path, help="Output JSON file")
    parser.add_argument("--stats-only", action="store_true", help="Only show statistics")

    args = parser.parse_args()

    # Parse start date if provided
    start_date = None
    if args.start_date:
        from dateutil import parser as date_parser
        start_date = date_parser.parse(args.start_date)
        tz = gettz(args.timezone)
        start_date = start_date.replace(tzinfo=tz)

    print(f"🗓️  Generating {args.weeks}-week schedule...\n")

    schedule = generate_schedule(
        num_weeks=args.weeks,
        start_date=start_date,
        timezone_str=args.timezone,
        include_categories=args.include_categories,
        exclude_categories=args.exclude_categories,
        prioritize_categories=args.prioritize_categories,
        seed=args.seed,
    )

    # Show stats
    print(f"📅 Schedule: {schedule.start_date.strftime('%b %d')} - {schedule.end_date.strftime('%b %d, %Y')}")
    print(f"📊 Total posts: {schedule.stats['total_posts']}")
    print(f"🧵 Threads: {schedule.stats['threads']}")
    print(f"\nBy category:")
    for cat, count in sorted(schedule.stats['by_category'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")

    if args.stats_only:
        return 0

    # Output to file if requested
    if args.output:
        args.output.write_text(schedule.to_json())
        print(f"\n✅ Written to {args.output}")
        return 0

    # Otherwise, print the schedule
    print(f"\n{'='*70}")
    print("GENERATED SCHEDULE")
    print(f"{'='*70}")

    current_day = None
    for sp in schedule.slots:
        day_str = sp.slot.datetime.strftime("%A, %b %d")
        if day_str != current_day:
            current_day = day_str
            print(f"\n📅 {day_str}")
            print("-" * 40)

        time_str = sp.slot.datetime.strftime("%I:%M %p")
        thread_marker = "🧵 " if sp.post.is_thread else ""
        preview = sp.post.get_preview(50)

        print(f"  {time_str} | [{sp.post.category}] {thread_marker}{preview}")

    return 0


if __name__ == "__main__":
    exit(main())
