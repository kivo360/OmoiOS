#!/usr/bin/env python3
"""
Curate Leads for Cold Outreach

Takes raw Apollo leads and curates the best 100 based on:
1. Has verified email (required)
2. Title diversity (balance lawyers vs consultants)
3. Company size (prefer smaller = more likely to need help)
4. Score for conversion likelihood

Usage:
    python curate_leads.py input.csv --output curated_100.csv --count 100
"""

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Optional


def score_for_conversion(lead: dict) -> int:
    """
    Score lead for conversion likelihood.
    Higher = more likely to convert to OpenClaw customer.
    """
    score = 0
    title = (lead.get('title') or '').lower()
    company = (lead.get('company_name') or '').lower()

    # === TITLE SCORING ===
    # Consultants/Specialists (easier to talk to, need automation)
    if any(kw in title for kw in ['consultant', 'specialist', 'advisor']):
        score += 5

    # Founders/Owners (decision makers, feel the pain directly)
    if any(kw in title for kw in ['founder', 'owner', 'ceo', 'co-founder']):
        score += 6

    # Directors/Managers (mid-level decision makers)
    if any(kw in title for kw in ['director', 'manager', 'head of']):
        score += 4

    # Global mobility (corporate, may have budget but longer sales cycle)
    if 'global mobility' in title:
        score += 2

    # Lawyers (harder to sell to, more skeptical, but have money)
    if any(kw in title for kw in ['lawyer', 'attorney', 'abogado']):
        score += 2

    # Relocation specific (our exact target)
    if 'relocation' in title:
        score += 3

    # Immigration specific
    if 'immigration' in title:
        score += 2

    # Visa specific
    if 'visa' in title:
        score += 3

    # Expat specific
    if 'expat' in title:
        score += 4

    # === COMPANY SIZE SCORING ===
    try:
        size = int(lead.get('company_size') or 0)
        if 1 <= size <= 10:
            score += 5  # Small = owner feels pain, makes decisions fast
        elif 11 <= size <= 25:
            score += 4
        elif 26 <= size <= 50:
            score += 3
        elif 51 <= size <= 100:
            score += 2
        # Larger companies = slower, more bureaucracy
    except (ValueError, TypeError):
        score += 2  # Unknown size, assume small

    # === COMPANY NAME SIGNALS ===
    # Boutique/independent firms (more likely to need help)
    if any(kw in company for kw in ['consulting', 'consultancy', 'services', 'solutions']):
        score += 2

    # Large corporate (less likely to buy $49 product)
    if any(kw in company for kw in ['deloitte', 'pwc', 'kpmg', 'ey ', 'ernst']):
        score -= 3

    # University (probably not our customer)
    if 'university' in company or 'school' in company:
        score -= 2

    return score


def categorize_title(title: str) -> str:
    """Categorize title for balancing."""
    title = title.lower()

    if any(kw in title for kw in ['founder', 'owner', 'ceo', 'co-founder']):
        return 'founder_owner'
    elif any(kw in title for kw in ['lawyer', 'attorney', 'abogado']):
        return 'lawyer'
    elif any(kw in title for kw in ['consultant', 'advisor']):
        return 'consultant'
    elif any(kw in title for kw in ['specialist', 'officer']):
        return 'specialist'
    elif 'global mobility' in title:
        return 'global_mobility'
    elif any(kw in title for kw in ['director', 'manager', 'head']):
        return 'management'
    else:
        return 'other'


def curate_leads(leads: list[dict], target_count: int = 100) -> list[dict]:
    """
    Curate leads for best conversion potential with title diversity.
    """
    # Only consider leads with emails
    leads_with_email = [l for l in leads if l.get('email')]

    if len(leads_with_email) < target_count:
        print(f"Warning: Only {len(leads_with_email)} leads have emails (target: {target_count})")

    # Score all leads
    for lead in leads_with_email:
        lead['conversion_score'] = score_for_conversion(lead)
        lead['title_category'] = categorize_title(lead.get('title', ''))

    # Sort by score
    leads_with_email.sort(key=lambda x: x['conversion_score'], reverse=True)

    # === BALANCED SELECTION ===
    # Target distribution for 100 leads:
    # - 30% consultants/advisors (easier to convert)
    # - 25% founders/owners (decision makers)
    # - 20% specialists
    # - 15% lawyers (still include some)
    # - 10% other (management, global mobility)

    targets = {
        'consultant': 30,
        'founder_owner': 25,
        'specialist': 20,
        'lawyer': 15,
        'management': 5,
        'global_mobility': 3,
        'other': 2,
    }

    selected = []
    by_category = {cat: [] for cat in targets.keys()}

    # Group by category
    for lead in leads_with_email:
        cat = lead['title_category']
        if cat in by_category:
            by_category[cat].append(lead)
        else:
            by_category['other'].append(lead)

    # Select from each category
    for category, target in targets.items():
        available = by_category.get(category, [])
        # Take up to target, sorted by score
        to_take = min(target, len(available))
        selected.extend(available[:to_take])

    # If we need more, fill from highest scoring remaining
    if len(selected) < target_count:
        selected_ids = {l.get('id') for l in selected}
        remaining = [l for l in leads_with_email if l.get('id') not in selected_ids]
        remaining.sort(key=lambda x: x['conversion_score'], reverse=True)
        needed = target_count - len(selected)
        selected.extend(remaining[:needed])

    # Final sort by score
    selected.sort(key=lambda x: x['conversion_score'], reverse=True)

    return selected[:target_count]


def assign_ab_variants(leads: list[dict]) -> list[dict]:
    """Assign A/B test variants evenly."""
    for i, lead in enumerate(leads):
        lead['email_variant'] = 'A' if i % 2 == 0 else 'B'
    return leads


def print_summary(leads: list[dict]):
    """Print summary of curated leads."""
    print("\n" + "="*60)
    print("CURATED LEADS SUMMARY")
    print("="*60)

    print(f"\nTotal leads: {len(leads)}")

    # By category
    categories = Counter(l.get('title_category', 'unknown') for l in leads)
    print("\n=== BY TITLE CATEGORY ===")
    for cat, count in categories.most_common():
        pct = count / len(leads) * 100
        print(f"  {cat}: {count} ({pct:.0f}%)")

    # Score distribution
    scores = [l.get('conversion_score', 0) for l in leads]
    avg_score = sum(scores) / len(scores) if scores else 0
    print(f"\n=== CONVERSION SCORES ===")
    print(f"  Average: {avg_score:.1f}")
    print(f"  Top 10 avg: {sum(scores[:10])/10:.1f}")
    print(f"  Range: {min(scores)} - {max(scores)}")

    # A/B split
    variant_a = [l for l in leads if l.get('email_variant') == 'A']
    variant_b = [l for l in leads if l.get('email_variant') == 'B']
    print(f"\n=== A/B SPLIT ===")
    print(f"  Variant A: {len(variant_a)}")
    print(f"  Variant B: {len(variant_b)}")

    # Top companies
    companies = Counter(l.get('company_name', 'Unknown') for l in leads)
    print(f"\n=== TOP COMPANIES ===")
    for company, count in companies.most_common(10):
        print(f"  {company}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Curate leads for cold outreach")
    parser.add_argument("input", help="Input CSV file")
    parser.add_argument("--output", "-o", default="curated_leads.csv", help="Output CSV file")
    parser.add_argument("--count", "-n", type=int, default=100, help="Number of leads to select")

    args = parser.parse_args()

    # Read input
    print(f"Reading {args.input}...")
    with open(args.input, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        leads = list(reader)

    print(f"Found {len(leads)} total leads")

    # Curate
    curated = curate_leads(leads, args.count)
    curated = assign_ab_variants(curated)

    # Save
    if curated:
        # Add our new fields to output
        fieldnames = list(curated[0].keys())

        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for lead in curated:
                writer.writerow(lead)

        print(f"\nSaved {len(curated)} curated leads to {args.output}")

    print_summary(curated)


if __name__ == "__main__":
    main()
