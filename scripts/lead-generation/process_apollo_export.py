#!/usr/bin/env python3
"""
Process Apollo Export

Takes a CSV export from Apollo's web interface and formats it for cold email outreach.
Use this when you don't have API access (free plan).

Steps:
1. Go to Apollo.io web app
2. Search for immigration lawyers in your target countries
3. Export the results as CSV
4. Run this script to format for outreach

Usage:
    python process_apollo_export.py input.csv --output formatted_leads.csv
"""

import argparse
import csv
import sys
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Lead:
    """Formatted lead for cold outreach."""
    first_name: str
    last_name: str
    full_name: str
    email: Optional[str]
    title: str
    company_name: str
    company_website: Optional[str]
    linkedin_url: Optional[str]
    location: Optional[str]
    email_variant: str  # A or B for A/B testing
    processed_at: str = ""

    def to_dict(self):
        return asdict(self)


def process_apollo_csv(input_path: str) -> list[Lead]:
    """Process Apollo CSV export into formatted leads."""
    leads = []

    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            # Apollo export column names (may vary slightly)
            first_name = row.get('First Name', row.get('first_name', ''))
            last_name = row.get('Last Name', row.get('last_name', ''))
            email = row.get('Email', row.get('email', ''))
            title = row.get('Title', row.get('title', ''))
            company = row.get('Company', row.get('company', row.get('Organization Name', '')))
            website = row.get('Website', row.get('website', row.get('Company Website', '')))
            linkedin = row.get('LinkedIn', row.get('linkedin_url', row.get('Person Linkedin Url', '')))
            location = row.get('Location', row.get('location', row.get('City', '')))

            # Skip if no email
            if not email:
                continue

            lead = Lead(
                first_name=first_name,
                last_name=last_name,
                full_name=f"{first_name} {last_name}".strip(),
                email=email,
                title=title,
                company_name=company,
                company_website=website,
                linkedin_url=linkedin,
                location=location,
                email_variant='A' if i % 2 == 0 else 'B',  # Alternate A/B
                processed_at=datetime.now().isoformat(),
            )
            leads.append(lead)

    return leads


def save_leads(leads: list[Lead], output_path: str):
    """Save leads to CSV."""
    if not leads:
        print("No leads to save.")
        return

    fieldnames = list(leads[0].to_dict().keys())

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead.to_dict())

    print(f"Saved {len(leads)} leads to {output_path}")


def print_summary(leads: list[Lead]):
    """Print summary of processed leads."""
    print("\n" + "="*50)
    print("LEAD SUMMARY")
    print("="*50)

    print(f"\nTotal leads: {len(leads)}")

    # A/B split
    variant_a = [l for l in leads if l.email_variant == 'A']
    variant_b = [l for l in leads if l.email_variant == 'B']
    print(f"Variant A: {len(variant_a)} leads")
    print(f"Variant B: {len(variant_b)} leads")

    # By location
    from collections import Counter
    locations = Counter(l.location for l in leads if l.location)
    if locations:
        print(f"\nBy location:")
        for loc, count in locations.most_common(10):
            print(f"  {loc}: {count}")

    # By title
    titles = Counter(l.title for l in leads if l.title)
    if titles:
        print(f"\nBy title:")
        for title, count in titles.most_common(5):
            print(f"  {title}: {count}")


def main():
    parser = argparse.ArgumentParser(
        description="Process Apollo CSV export for cold outreach"
    )

    parser.add_argument(
        "input",
        help="Path to Apollo CSV export"
    )

    parser.add_argument(
        "--output", "-o",
        default="formatted_leads.csv",
        help="Output CSV path (default: formatted_leads.csv)"
    )

    args = parser.parse_args()

    print(f"Processing {args.input}...")
    leads = process_apollo_csv(args.input)

    if not leads:
        print("No leads with emails found in the export.")
        sys.exit(1)

    save_leads(leads, args.output)
    print_summary(leads)

    print("\n" + "="*50)
    print("NEXT STEPS")
    print("="*50)
    print("""
1. Import formatted_leads.csv into your email tool
2. Send Variant A email to leads with email_variant='A'
3. Send Variant B email to leads with email_variant='B'
4. Track open rates and replies for each variant
""")


if __name__ == "__main__":
    main()
