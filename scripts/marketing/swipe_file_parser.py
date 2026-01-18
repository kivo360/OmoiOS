#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml>=6.0",
# ]
# ///
"""
Swipe File Parser

Parses posts from markdown files in the swipe_file directory.
Each file has YAML frontmatter with scheduling rules and posts in code blocks.

Usage:
    # As a module
    from swipe_file_parser import parse_all_posts, SwipeFilePost

    posts = parse_all_posts()
    for post in posts:
        print(f"{post.category}: {post.content[:50]}...")

    # As a script (for testing)
    uv run swipe_file_parser.py
    uv run swipe_file_parser.py --category raw-unclean
    uv run swipe_file_parser.py --stats
"""

import re
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SchedulingRules:
    """Scheduling rules from frontmatter"""
    best_days: list[str] = field(default_factory=lambda: ["monday", "tuesday", "wednesday", "thursday", "friday"])
    best_times: list[str] = field(default_factory=lambda: ["09:00", "12:00", "18:00"])
    min_gap_hours: int = 24
    max_per_day: int = 2
    max_per_week: int = 7
    time_sensitive: bool = False
    max_advance_days: Optional[int] = None
    engagement_level: str = "medium"
    notes: str = ""


@dataclass
class SwipeFilePost:
    """A single post extracted from a swipe file"""
    content: str
    category: str
    source_file: str
    title: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    is_thread: bool = False
    thread_parts: list[str] = field(default_factory=list)
    scheduling: SchedulingRules = field(default_factory=SchedulingRules)

    def get_preview(self, max_length: int = 60) -> str:
        """Get a preview of the post content"""
        text = self.content if not self.is_thread else self.thread_parts[0]
        preview = text[:max_length].replace("\n", " ")
        if len(text) > max_length:
            preview += "..."
        return preview

    def get_all_content(self) -> list[str]:
        """Get content as a list (single item for regular posts, multiple for threads)"""
        if self.is_thread:
            return self.thread_parts
        return [self.content]


@dataclass
class SwipeFile:
    """A parsed swipe file with metadata and posts"""
    path: Path
    title: str
    category: str
    description: str
    tags: list[str]
    scheduling: SchedulingRules
    posts: list[SwipeFilePost]
    post_count: int = 0
    last_updated: Optional[str] = None


# ============================================================================
# Parser Functions
# ============================================================================

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and remaining content from markdown"""
    if not content.startswith("---"):
        return {}, content

    end_idx = content.find("---", 3)
    if end_idx < 0:
        return {}, content

    frontmatter_str = content[3:end_idx].strip()
    remaining = content[end_idx + 3:].strip()

    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError:
        frontmatter = {}

    return frontmatter, remaining


def parse_scheduling_rules(sched_dict: dict) -> SchedulingRules:
    """Parse scheduling rules from frontmatter"""
    if not sched_dict:
        return SchedulingRules()

    return SchedulingRules(
        best_days=sched_dict.get("best_days", ["monday", "tuesday", "wednesday", "thursday", "friday"]),
        best_times=sched_dict.get("best_times", ["09:00", "12:00", "18:00"]),
        min_gap_hours=sched_dict.get("min_gap_hours", 24),
        max_per_day=sched_dict.get("max_per_day", 2),
        max_per_week=sched_dict.get("max_per_week", 7),
        time_sensitive=sched_dict.get("time_sensitive", False),
        max_advance_days=sched_dict.get("max_advance_days"),
        engagement_level=sched_dict.get("engagement_level", "medium"),
        notes=sched_dict.get("notes", ""),
    )


def extract_posts_from_content(content: str, category: str, source_file: str, scheduling: SchedulingRules) -> list[SwipeFilePost]:
    """Extract individual posts from markdown content"""
    posts = []

    # Find all code blocks (posts are in ``` blocks)
    # Pattern: ### Title (optional) followed by ``` content ```
    sections = re.split(r'\n---\n', content)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Skip non-post sections (like headers, strategy notes, templates)
        if section.startswith("## Additional") or section.startswith("## Comment Reply") or section.startswith("## Organic"):
            continue
        if "Template" in section and "###" not in section:
            continue

        # Extract title if present (### Title format)
        title_match = re.search(r'^###\s+(.+?)$', section, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else None

        # Skip template sections
        if title and ("Template" in title or "Strategy" in title or "Framework" in title):
            continue

        # Extract code block content
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', section, re.DOTALL)

        for block in code_blocks:
            content_text = block.strip()
            if not content_text:
                continue

            # Skip very short content (probably examples or fragments)
            if len(content_text) < 30:
                continue

            # Check if it's a thread (has numbered sections or multiple distinct parts)
            is_thread = False
            thread_parts = []

            # Detect threads: content with "1/ " or "🧵" pattern followed by numbered sections
            if re.search(r'🧵|^\d+/', content_text, re.MULTILINE):
                # Split by numbered sections
                parts = re.split(r'\n(?=\d+/)', content_text)
                if len(parts) > 1:
                    is_thread = True
                    # First part might be intro without number
                    for part in parts:
                        part = part.strip()
                        if part:
                            thread_parts.append(part)

            posts.append(SwipeFilePost(
                content=content_text,
                category=category,
                source_file=source_file,
                title=title,
                is_thread=is_thread,
                thread_parts=thread_parts if is_thread else [],
                scheduling=scheduling,
            ))

    return posts


def parse_swipe_file(file_path: Path) -> Optional[SwipeFile]:
    """Parse a single swipe file markdown document"""
    try:
        content = file_path.read_text()
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return None

    frontmatter, body = parse_frontmatter(content)

    # Skip non-content files
    if not frontmatter:
        return None

    category = frontmatter.get("category", file_path.stem.replace("_", "-"))

    # Skip meta files
    if category in ("rules", "schedule", "growth", "readme"):
        return None

    scheduling = parse_scheduling_rules(frontmatter.get("scheduling", {}))

    posts = extract_posts_from_content(
        body,
        category=category,
        source_file=file_path.name,
        scheduling=scheduling,
    )

    return SwipeFile(
        path=file_path,
        title=frontmatter.get("title", file_path.stem),
        category=category,
        description=frontmatter.get("description", ""),
        tags=frontmatter.get("tags", []),
        scheduling=scheduling,
        posts=posts,
        post_count=frontmatter.get("post_count", len(posts)),
        last_updated=frontmatter.get("last_updated"),
    )


def get_swipe_file_dir() -> Path:
    """Get the swipe file directory"""
    # Try relative to this script first
    script_dir = Path(__file__).parent
    swipe_dir = script_dir.parent.parent / "docs" / "marketing" / "swipe_file"

    if swipe_dir.exists():
        return swipe_dir

    # Try current working directory
    cwd_swipe = Path.cwd() / "docs" / "marketing" / "swipe_file"
    if cwd_swipe.exists():
        return cwd_swipe

    raise FileNotFoundError(
        f"Could not find swipe_file directory. Tried:\n"
        f"  - {swipe_dir}\n"
        f"  - {cwd_swipe}"
    )


def parse_all_files(swipe_dir: Optional[Path] = None) -> list[SwipeFile]:
    """Parse all swipe files in the directory"""
    if swipe_dir is None:
        swipe_dir = get_swipe_file_dir()

    swipe_files = []

    for md_file in sorted(swipe_dir.glob("*.md")):
        # Skip meta files
        if md_file.name.upper().startswith(("README", "GROWTH", "SCHEDULE", "RULES")):
            continue

        parsed = parse_swipe_file(md_file)
        if parsed and parsed.posts:
            swipe_files.append(parsed)

    return swipe_files


def parse_all_posts(
    swipe_dir: Optional[Path] = None,
    categories: Optional[list[str]] = None,
) -> list[SwipeFilePost]:
    """
    Parse all posts from all swipe files.

    Args:
        swipe_dir: Path to swipe file directory (auto-detected if None)
        categories: Filter to only these categories (all if None)

    Returns:
        List of all posts
    """
    swipe_files = parse_all_files(swipe_dir)
    all_posts = []

    for sf in swipe_files:
        if categories and sf.category not in categories:
            continue
        all_posts.extend(sf.posts)

    return all_posts


def get_posts_by_category(swipe_dir: Optional[Path] = None) -> dict[str, list[SwipeFilePost]]:
    """Get all posts organized by category"""
    posts = parse_all_posts(swipe_dir)
    by_category: dict[str, list[SwipeFilePost]] = {}

    for post in posts:
        if post.category not in by_category:
            by_category[post.category] = []
        by_category[post.category].append(post)

    return by_category


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parse and inspect swipe file posts")
    parser.add_argument("--category", "-c", help="Filter to specific category")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    parser.add_argument("--list-categories", action="store_true", help="List all categories")
    parser.add_argument("--full", action="store_true", help="Show full post content")
    parser.add_argument("--swipe-dir", type=Path, help="Path to swipe_file directory")

    args = parser.parse_args()

    try:
        swipe_dir = args.swipe_dir or get_swipe_file_dir()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    print(f"📁 Parsing: {swipe_dir}\n")

    swipe_files = parse_all_files(swipe_dir)

    if args.list_categories:
        print("Categories:")
        for sf in swipe_files:
            print(f"  - {sf.category}: {len(sf.posts)} posts ({sf.path.name})")
        return 0

    if args.stats:
        total_posts = sum(len(sf.posts) for sf in swipe_files)
        threads = sum(1 for sf in swipe_files for p in sf.posts if p.is_thread)

        print("📊 Statistics:")
        print(f"  Files: {len(swipe_files)}")
        print(f"  Total posts: {total_posts}")
        print(f"  Threads: {threads}")
        print(f"  Regular posts: {total_posts - threads}")
        print("\nBy category:")
        for sf in sorted(swipe_files, key=lambda x: len(x.posts), reverse=True):
            thread_count = sum(1 for p in sf.posts if p.is_thread)
            print(f"  {sf.category}: {len(sf.posts)} posts ({thread_count} threads)")
        return 0

    # Filter by category if specified
    if args.category:
        swipe_files = [sf for sf in swipe_files if sf.category == args.category]
        if not swipe_files:
            print(f"No files found for category: {args.category}")
            return 1

    # Show posts
    for sf in swipe_files:
        print(f"\n{'='*60}")
        print(f"📄 {sf.title} ({sf.category})")
        print(f"   Source: {sf.path.name}")
        print(f"   Posts: {len(sf.posts)}")
        print(f"   Best days: {sf.scheduling.best_days}")
        print(f"   Engagement: {sf.scheduling.engagement_level}")
        print(f"{'='*60}")

        for i, post in enumerate(sf.posts, 1):
            thread_marker = "🧵 " if post.is_thread else ""
            if args.full:
                print(f"\n--- Post {i} {thread_marker}---")
                if post.title:
                    print(f"Title: {post.title}")
                print(post.content)
            else:
                print(f"  {i}. {thread_marker}{post.get_preview(70)}")

    return 0


if __name__ == "__main__":
    exit(main())
