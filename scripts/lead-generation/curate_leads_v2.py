#!/usr/bin/env python3
"""
Curate Leads v2 - Filter out big corps, prioritize small firms

Excludes: Deloitte, EY, PwC, KPMG, Chevron, big corps, universities
Prioritizes: Small consulting firms, independent practitioners, founders
"""

import argparse
import csv
from collections import Counter
from pathlib import Path


# Big corps to exclude - they won't buy a $49 product
EXCLUDE_COMPANIES = [
    # Big 4 / Consulting
    "deloitte", "ey ", "ernst & young", "pwc", "pricewaterhouse", "kpmg",
    "accenture", "mckinsey", "bcg", "bain",
    # Oil/Energy
    "chevron", "shell", "exxon", "bp ", "aramco", "total",
    # Tech giants
    "google", "microsoft", "amazon", "meta", "apple", "ibm",
    # Universities
    "university", "college", "school", "instituto", "universidad",
    # Large relocation corps (they have internal solutions)
    "santa fe relocation", "sirva", "cartus", "bgrs",
    # Other large corps
    "primark", "amdocs", "sterling lexicon", "vialto",
]

# Good signals - small firms likely to buy
GOOD_SIGNALS = [
    "consulting", "consultancy", "services", "solutions", "partners",
    "associates", "group", "global", "immigration", "relocation",
    "visa", "expat", "mobility",
    # Simplo-profile: international moving/logistics
    "moving", "movers", "removals", "logistics", "freight",
    "cargo", "transport", "groupage", "destination",
]


def is_excluded(company: str) -> bool:
    """Check if company should be excluded."""
    company_lower = company.lower()
    for exc in EXCLUDE_COMPANIES:
        if exc in company_lower:
            return True
    return False


def score_for_conversion(lead: dict) -> int:
    """Score lead for conversion - updated to penalize big corps."""
    score = 0
    title = (lead.get('title') or '').lower()
    company = (lead.get('company_name') or '').lower()

    # HARD EXCLUDE - big corps
    if is_excluded(company):
        return -100

    # === TITLE SCORING ===
    # Founders/Owners (decision makers)
    if any(kw in title for kw in ['founder', 'owner', 'ceo', 'co-founder']):
        score += 8

    # Consultants (our sweet spot)
    if 'consultant' in title or 'advisor' in title:
        score += 6

    # Specialists
    if 'specialist' in title:
        score += 4

    # Directors at small firms
    if 'director' in title or 'manager' in title:
        score += 3

    # Lawyers (still ok but harder sell)
    if 'lawyer' in title or 'attorney' in title:
        score += 2

    # Relocation/Immigration specific
    if 'relocation' in title:
        score += 3
    if 'immigration' in title:
        score += 2
    if 'visa' in title:
        score += 3
    if 'expat' in title:
        score += 4

    # Simplo-profile: operations/logistics leaders (coordination pain)
    if any(kw in title for kw in ['operations', 'logistics', 'supply chain']):
        score += 4
    if any(kw in title for kw in ['moving', 'movers', 'move manager']):
        score += 5

    # === COMPANY SIGNALS ===
    # Small firm signals
    if any(sig in company for sig in GOOD_SIGNALS):
        score += 3

    # Company size - Simplo sweet spot is 25-100
    try:
        size = int(lead.get('company_size') or 0)
        if 25 <= size <= 100:
            score += 6  # Simplo sweet spot - big enough pain, small enough to buy
        elif 10 <= size < 25:
            score += 5
        elif 1 <= size < 10:
            score += 3  # Very small, may not have budget
        elif 101 <= size <= 200:
            score += 2  # Still possible
        elif size > 200:
            score -= 2  # Too big
    except (ValueError, TypeError):
        score += 2  # Unknown = assume small

    return score


def categorize_title(title: str) -> str:
    """Categorize title."""
    title = title.lower()
    if any(kw in title for kw in ['founder', 'owner', 'ceo', 'co-founder']):
        return 'founder_owner'
    elif any(kw in title for kw in ['operations', 'logistics', 'supply chain', 'moving']):
        return 'operations'
    elif any(kw in title for kw in ['lawyer', 'attorney']):
        return 'lawyer'
    elif any(kw in title for kw in ['consultant', 'advisor']):
        return 'consultant'
    elif 'specialist' in title:
        return 'specialist'
    elif any(kw in title for kw in ['director', 'manager', 'head']):
        return 'management'
    else:
        return 'other'


def curate_leads(input_file: str, output_file: str, count: int, exclude_file: str = None):
    """Curate best leads, excluding big corps and already-contacted."""

    # Load already contacted emails if provided
    already_contacted = set()
    if exclude_file and Path(exclude_file).exists():
        with open(exclude_file) as f:
            reader = csv.DictReader(f)
            already_contacted = {r.get('email', '').lower() for r in reader}
        print(f"Excluding {len(already_contacted)} already-contacted emails")

    # Load leads
    with open(input_file) as f:
        reader = csv.DictReader(f)
        leads = list(reader)

    print(f"Loaded {len(leads)} total leads")

    # Filter: must have email, not already contacted, not excluded company
    valid = []
    excluded_corps = []
    no_email = 0
    already_sent = 0

    for lead in leads:
        email = lead.get('email', '').strip()
        company = lead.get('company_name', '')

        if not email:
            no_email += 1
            continue

        if email.lower() in already_contacted:
            already_sent += 1
            continue

        if is_excluded(company):
            excluded_corps.append(company)
            continue

        lead['conversion_score'] = score_for_conversion(lead)
        lead['title_category'] = categorize_title(lead.get('title', ''))
        valid.append(lead)

    print(f"Filtered: {no_email} no email, {already_sent} already contacted, {len(excluded_corps)} big corps")

    if excluded_corps:
        corp_counts = Counter(excluded_corps)
        print(f"Excluded companies: {dict(corp_counts.most_common(10))}")

    print(f"Valid leads: {len(valid)}")

    # Sort by score and take top N
    valid.sort(key=lambda x: x['conversion_score'], reverse=True)
    selected = valid[:count]

    # Assign A/B variants
    for i, lead in enumerate(selected):
        lead['email_variant'] = 'A' if i % 2 == 0 else 'B'

    # Save
    if selected:
        fieldnames = list(selected[0].keys())
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(selected)

        print(f"\nSaved {len(selected)} leads to {output_file}")

    # Summary
    print("\n" + "="*60)
    print("CURATED LEADS SUMMARY")
    print("="*60)

    print(f"\nTotal: {len(selected)}")

    categories = Counter(l['title_category'] for l in selected)
    print("\nBy category:")
    for cat, cnt in categories.most_common():
        print(f"  {cat}: {cnt} ({cnt/len(selected)*100:.0f}%)")

    scores = [l['conversion_score'] for l in selected]
    print(f"\nConversion scores: avg={sum(scores)/len(scores):.1f}, range={min(scores)}-{max(scores)}")

    companies = Counter(l['company_name'] for l in selected)
    print("\nTop companies:")
    for comp, cnt in companies.most_common(10):
        print(f"  {comp}: {cnt}")

    variant_a = sum(1 for l in selected if l['email_variant'] == 'A')
    variant_b = sum(1 for l in selected if l['email_variant'] == 'B')
    print(f"\nA/B split: A={variant_a}, B={variant_b}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input CSV")
    parser.add_argument("--output", "-o", default="curated_leads.csv")
    parser.add_argument("--count", "-n", type=int, default=100)
    parser.add_argument("--exclude", "-e", help="CSV of already-contacted leads to exclude")

    args = parser.parse_args()
    curate_leads(args.input, args.output, args.count, args.exclude)


if __name__ == "__main__":
    main()
