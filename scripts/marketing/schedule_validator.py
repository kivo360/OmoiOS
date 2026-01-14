#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml>=6.0",
# ]
# ///
"""
Schedule Validator for Tweet Scheduling

Validates scheduled posts against category rules to ensure appropriate
timing, spacing, and content mix.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from collections import defaultdict
import yaml
import re


# ============================================================================
# Scheduling Rules (loaded from markdown frontmatter)
# ============================================================================

@dataclass
class CategoryRules:
    """Rules for a content category"""
    category: str
    best_days: list[str] = field(default_factory=list)
    best_times: list[str] = field(default_factory=list)
    min_gap_hours: int = 24
    max_per_day: int = 2
    max_per_week: int = 7
    time_sensitive: bool = False
    max_advance_days: Optional[int] = None
    engagement_level: str = "medium"
    notes: str = ""


# Default rules for categories without metadata
DEFAULT_RULES = CategoryRules(
    category="default",
    best_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
    best_times=["09:00", "12:00", "18:00"],
    min_gap_hours=24,
    max_per_day=2,
    max_per_week=7,
)


# ============================================================================
# Validation Results
# ============================================================================

@dataclass
class ValidationIssue:
    """A single validation issue"""
    level: str  # ERROR, WARNING, INFO
    message: str
    post_index: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Complete validation result"""
    is_valid: bool
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    info: list[ValidationIssue] = field(default_factory=list)

    def add_error(self, msg: str, post_index: int = None, suggestion: str = None):
        self.errors.append(ValidationIssue("ERROR", msg, post_index, suggestion))
        self.is_valid = False

    def add_warning(self, msg: str, post_index: int = None, suggestion: str = None):
        self.warnings.append(ValidationIssue("WARNING", msg, post_index, suggestion))

    def add_info(self, msg: str, post_index: int = None, suggestion: str = None):
        self.info.append(ValidationIssue("INFO", msg, post_index, suggestion))


# ============================================================================
# Rule Loader
# ============================================================================

def load_category_rules(swipe_file_dir: Path) -> dict[str, CategoryRules]:
    """Load scheduling rules from markdown frontmatter"""
    rules = {}

    for md_file in swipe_file_dir.glob("*.md"):
        if md_file.name.startswith(("README", "GROWTH", "SCHEDULE", "RULES")):
            continue

        try:
            content = md_file.read_text()
            # Extract YAML frontmatter
            if content.startswith("---"):
                end_idx = content.find("---", 3)
                if end_idx > 0:
                    frontmatter = yaml.safe_load(content[3:end_idx])
                    if frontmatter and "scheduling" in frontmatter:
                        sched = frontmatter["scheduling"]
                        category = frontmatter.get("category", md_file.stem)
                        rules[category] = CategoryRules(
                            category=category,
                            best_days=sched.get("best_days", []),
                            best_times=sched.get("best_times", []),
                            min_gap_hours=sched.get("min_gap_hours", 24),
                            max_per_day=sched.get("max_per_day", 2),
                            max_per_week=sched.get("max_per_week", 7),
                            time_sensitive=sched.get("time_sensitive", False),
                            max_advance_days=sched.get("max_advance_days"),
                            engagement_level=sched.get("engagement_level", "medium"),
                            notes=sched.get("notes", ""),
                        )
        except Exception as e:
            print(f"Warning: Could not parse {md_file.name}: {e}")

    return rules


# ============================================================================
# Source File to Category Mapping
# ============================================================================

SOURCE_TO_CATEGORY = {
    "general_builder.md": "general-builder",
    "agent_problems.md": "agent-problems",
    "engagement_questions.md": "engagement-questions",
    "stories.md": "stories",
    "spec_driven.md": "spec-driven",
    "cto_pain_points.md": "cto-pain",
    "vision_and_product.md": "vision-product",
    "technical_education.md": "technical-education",
    "competitor_callouts.md": "competitor-callouts",
    "failure_stories.md": "failure-stories",
    "hot_takes.md": "hot-takes",
    "build_in_public.md": "build-in-public",
    "memes_analogies.md": "memes-analogies",
    "customer_avatars.md": "customer-avatars",
    "threads.md": "threads",
    "use_cases.md": "use-cases",
}


# ============================================================================
# Time-Sensitive Content Detection
# ============================================================================

TIME_SENSITIVE_PATTERNS = [
    r"\bthis week\b",
    r"\bthis month\b",
    r"\byesterday\b",
    r"\btoday\b",
    r"\blast night\b",
    r"\bjust shipped\b",
    r"\bjust launched\b",
    r"\bworking on\b",
    r"\bwoke up to\b",
]


def detect_time_sensitive_content(content: str) -> list[str]:
    """Detect time-sensitive phrases in content"""
    found = []
    content_lower = content.lower()
    for pattern in TIME_SENSITIVE_PATTERNS:
        if re.search(pattern, content_lower):
            found.append(pattern.replace(r"\b", "").strip())
    return found


# ============================================================================
# Validators
# ============================================================================

@dataclass
class ScheduledPost:
    """A post scheduled for a specific time"""
    index: int
    content: str
    source: str
    scheduled_datetime: datetime
    is_thread: bool = False

    @property
    def category(self) -> str:
        return SOURCE_TO_CATEGORY.get(self.source, "unknown")

    @property
    def day_name(self) -> str:
        return self.scheduled_datetime.strftime("%A").lower()


def validate_schedule(
    posts: list[ScheduledPost],
    rules: dict[str, CategoryRules],
    start_date: datetime,
) -> ValidationResult:
    """
    Validate a schedule against all rules.

    Checks:
    1. Category spacing (min_gap_hours)
    2. Daily limits (max_per_day)
    3. Weekly limits (max_per_week)
    4. Best day violations
    5. Time-sensitive content scheduled too far in advance
    6. Duplicate content (same source) back-to-back
    7. Content mix (not all same category in a day)
    """
    result = ValidationResult(is_valid=True)

    # Track posts by category, day, and week
    posts_by_category: dict[str, list[ScheduledPost]] = defaultdict(list)
    posts_by_day: dict[str, list[ScheduledPost]] = defaultdict(list)
    posts_by_week: dict[int, list[ScheduledPost]] = defaultdict(list)

    for post in posts:
        posts_by_category[post.category].append(post)
        day_key = post.scheduled_datetime.strftime("%Y-%m-%d")
        posts_by_day[day_key].append(post)
        week_num = post.scheduled_datetime.isocalendar()[1]
        posts_by_week[week_num].append(post)

    # 1. Check category spacing (min_gap_hours)
    for category, category_posts in posts_by_category.items():
        if len(category_posts) < 2:
            continue

        rule = rules.get(category, DEFAULT_RULES)
        sorted_posts = sorted(category_posts, key=lambda p: p.scheduled_datetime)

        for i in range(1, len(sorted_posts)):
            prev = sorted_posts[i-1]
            curr = sorted_posts[i]
            gap = (curr.scheduled_datetime - prev.scheduled_datetime).total_seconds() / 3600

            if gap < rule.min_gap_hours:
                result.add_warning(
                    f"Category '{category}' has posts too close together "
                    f"({gap:.1f}h gap, minimum is {rule.min_gap_hours}h)",
                    post_index=curr.index,
                    suggestion=f"Move post {curr.index} at least {rule.min_gap_hours - gap:.1f} hours later"
                )

    # 2. Check daily limits
    for day_key, day_posts in posts_by_day.items():
        # Count by category
        category_counts = defaultdict(int)
        for post in day_posts:
            category_counts[post.category] += 1

        for category, count in category_counts.items():
            rule = rules.get(category, DEFAULT_RULES)
            if count > rule.max_per_day:
                result.add_warning(
                    f"Day {day_key}: {count} posts from '{category}' "
                    f"(max is {rule.max_per_day})",
                    suggestion=f"Move {count - rule.max_per_day} '{category}' posts to another day"
                )

    # 3. Check weekly limits
    for week_num, week_posts in posts_by_week.items():
        category_counts = defaultdict(int)
        for post in week_posts:
            category_counts[post.category] += 1

        for category, count in category_counts.items():
            rule = rules.get(category, DEFAULT_RULES)
            if count > rule.max_per_week:
                result.add_error(
                    f"Week {week_num}: {count} posts from '{category}' "
                    f"(max is {rule.max_per_week})",
                    suggestion=f"Remove {count - rule.max_per_week} '{category}' posts"
                )

    # 4. Check best day violations
    for post in posts:
        rule = rules.get(post.category, DEFAULT_RULES)
        if rule.best_days and post.day_name not in rule.best_days:
            result.add_info(
                f"Post {post.index} ({post.category}) scheduled on {post.day_name}, "
                f"but best days are {rule.best_days}",
                post_index=post.index,
                suggestion=f"Consider moving to {rule.best_days[0].title()}"
            )

    # 5. Check time-sensitive content
    for post in posts:
        rule = rules.get(post.category, DEFAULT_RULES)
        days_in_advance = (post.scheduled_datetime - start_date).days

        # Check category-level time sensitivity
        if rule.time_sensitive and rule.max_advance_days:
            if days_in_advance > rule.max_advance_days:
                result.add_warning(
                    f"Post {post.index} ({post.category}) is time-sensitive "
                    f"but scheduled {days_in_advance} days in advance "
                    f"(max is {rule.max_advance_days})",
                    post_index=post.index,
                    suggestion=f"Schedule within {rule.max_advance_days} days"
                )

        # Check content-level time sensitivity
        sensitive_phrases = detect_time_sensitive_content(post.content)
        if sensitive_phrases and days_in_advance > 7:
            result.add_warning(
                f"Post {post.index} contains time-sensitive phrases "
                f"({', '.join(sensitive_phrases)}) but is scheduled "
                f"{days_in_advance} days in advance",
                post_index=post.index,
                suggestion="Schedule within 7 days or remove time references"
            )

    # 6. Check for back-to-back same source
    sorted_all = sorted(posts, key=lambda p: p.scheduled_datetime)
    for i in range(1, len(sorted_all)):
        prev = sorted_all[i-1]
        curr = sorted_all[i]
        if prev.source == curr.source:
            result.add_info(
                f"Back-to-back posts from same source ({curr.source}): "
                f"posts {prev.index} and {curr.index}",
                post_index=curr.index,
                suggestion="Mix in content from different sources"
            )

    # 7. Check content mix per day
    for day_key, day_posts in posts_by_day.items():
        categories = set(p.category for p in day_posts)
        if len(day_posts) >= 3 and len(categories) < 2:
            result.add_warning(
                f"Day {day_key} has {len(day_posts)} posts but only "
                f"{len(categories)} category - mix it up",
                suggestion="Add posts from different categories"
            )

    return result


def print_validation_result(result: ValidationResult):
    """Print validation results in a readable format"""
    print("\n" + "=" * 60)
    print("SCHEDULE VALIDATION RESULTS")
    print("=" * 60)

    if result.errors:
        print(f"\n❌ ERRORS ({len(result.errors)}):")
        for issue in result.errors:
            print(f"  • {issue.message}")
            if issue.suggestion:
                print(f"    → Suggestion: {issue.suggestion}")

    if result.warnings:
        print(f"\n⚠️  WARNINGS ({len(result.warnings)}):")
        for issue in result.warnings:
            print(f"  • {issue.message}")
            if issue.suggestion:
                print(f"    → Suggestion: {issue.suggestion}")

    if result.info:
        print(f"\nℹ️  INFO ({len(result.info)}):")
        for issue in result.info:
            print(f"  • {issue.message}")
            if issue.suggestion:
                print(f"    → Suggestion: {issue.suggestion}")

    print("\n" + "-" * 60)
    if result.is_valid:
        print("✅ Schedule is VALID (no errors)")
    else:
        print("❌ Schedule has ERRORS - fix before posting")

    print(f"   {len(result.errors)} errors, {len(result.warnings)} warnings, {len(result.info)} info")
    print("=" * 60)


# ============================================================================
# Main (for standalone testing)
# ============================================================================

if __name__ == "__main__":
    # Test loading rules
    swipe_dir = Path(__file__).parent.parent.parent / "docs" / "marketing" / "swipe_file"
    rules = load_category_rules(swipe_dir)

    print(f"Loaded rules for {len(rules)} categories:")
    for cat, rule in rules.items():
        print(f"  - {cat}: best_days={rule.best_days}, max_per_day={rule.max_per_day}")
