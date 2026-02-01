#!/usr/bin/env python3
"""
Apollo Lead Finder

Pull engineering leader leads from Apollo.io API based on ICP criteria.

Usage:
    # Set your API key
    export APOLLO_API_KEY="your-api-key-here"

    # Run the script
    python apollo_lead_finder.py --output leads.csv --max-leads 1000

    # With enrichment (costs credits)
    python apollo_lead_finder.py --output leads.csv --max-leads 500 --enrich
"""

import os
import sys
import json
import time
import argparse
import csv
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    sys.exit(1)


# =============================================================================
# Configuration
# =============================================================================

APOLLO_BASE_URL = "https://api.apollo.io/v1"

# Primary ICP: Engineering Leaders at Funded Startups
PRIMARY_ICP = {
    "person_titles": [
        "VP Engineering",
        "VP of Engineering",
        "Engineering Manager",
        "Senior Engineering Manager",
        "CTO",
        "Chief Technology Officer",
        "Head of Engineering",
        "Director of Engineering",
        "Director, Engineering",
        "Head of Product Engineering",
        "Principal Engineering Manager",
        "SVP Engineering",
    ],
    "organization_num_employees_ranges": [
        "51,100",
        "101,200",
        "201,500",
    ],
    "organization_latest_funding_stage_cd": [
        "series_a",
        "series_b",
        "series_c",
    ],
    "person_locations": [
        "United States",
        "Canada",
        "United Kingdom",
    ],
}

# Secondary ICP: Agency Technical Leadership
AGENCY_ICP = {
    "person_titles": [
        "CTO",
        "Technical Director",
        "Head of Engineering",
        "Development Lead",
        "Director of Technology",
        "VP Engineering",
        "Chief Technology Officer",
    ],
    "organization_num_employees_ranges": [
        "21,50",
        "51,100",
        "101,200",
    ],
    "q_organization_keyword_tags": [
        "digital agency",
        "software development",
        "software consultancy",
        "web development",
    ],
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Lead:
    """Represents a lead from Apollo."""
    id: str
    first_name: str
    last_name: str
    full_name: str
    title: str
    email: Optional[str]
    email_status: Optional[str]
    linkedin_url: Optional[str]
    company_name: str
    company_website: Optional[str]
    company_size: Optional[str]
    company_funding_stage: Optional[str]
    company_industry: Optional[str]
    company_linkedin_url: Optional[str]
    location: Optional[str]
    score: int = 0
    pulled_at: str = ""

    def to_dict(self):
        return asdict(self)


# =============================================================================
# Apollo API Client
# =============================================================================

class ApolloClient:
    """Client for interacting with Apollo.io API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        })

    def search_people(
        self,
        filters: dict,
        page: int = 1,
        per_page: int = 100,
    ) -> dict:
        """
        Search for people using filters.

        This endpoint is FREE and doesn't consume credits.
        It returns basic info but NOT emails.
        """
        url = f"{APOLLO_BASE_URL}/mixed_people/search"

        payload = {
            "api_key": self.api_key,
            "page": page,
            "per_page": per_page,
            **filters,
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        return response.json()

    def enrich_person(self, person_id: str) -> dict:
        """
        Enrich a person to get their email.

        WARNING: This COSTS CREDITS.
        """
        url = f"{APOLLO_BASE_URL}/people/match"

        payload = {
            "api_key": self.api_key,
            "id": person_id,
            "reveal_personal_emails": False,
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        return response.json()

    def bulk_enrich(self, person_ids: list[str]) -> list[dict]:
        """
        Bulk enrich multiple people.

        WARNING: This COSTS CREDITS (1 per person).
        Max 10 per request.
        """
        url = f"{APOLLO_BASE_URL}/people/bulk_match"

        results = []

        # Process in batches of 10
        for i in range(0, len(person_ids), 10):
            batch = person_ids[i:i+10]

            payload = {
                "api_key": self.api_key,
                "ids": batch,
                "reveal_personal_emails": False,
            }

            response = self.session.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            results.extend(data.get("matches", []))

            # Rate limiting
            time.sleep(0.5)

        return results


# =============================================================================
# Lead Processing
# =============================================================================

def parse_person(person: dict) -> Lead:
    """Parse Apollo person data into a Lead object."""
    org = person.get("organization", {}) or {}

    return Lead(
        id=person.get("id", ""),
        first_name=person.get("first_name", ""),
        last_name=person.get("last_name", ""),
        full_name=person.get("name", ""),
        title=person.get("title", ""),
        email=person.get("email"),
        email_status=person.get("email_status"),
        linkedin_url=person.get("linkedin_url"),
        company_name=org.get("name", ""),
        company_website=org.get("website_url"),
        company_size=org.get("estimated_num_employees"),
        company_funding_stage=org.get("latest_funding_stage"),
        company_industry=org.get("industry"),
        company_linkedin_url=org.get("linkedin_url"),
        location=person.get("city") or person.get("state") or person.get("country"),
        pulled_at=datetime.now().isoformat(),
    )


def score_lead(lead: Lead) -> int:
    """Score a lead based on fit signals."""
    score = 0

    # Funding stage scoring
    funding = (lead.company_funding_stage or "").lower()
    if "series_b" in funding or "series b" in funding:
        score += 3  # Sweet spot
    elif "series_a" in funding or "series a" in funding:
        score += 2
    elif "series_c" in funding or "series c" in funding:
        score += 2

    # Company size scoring
    try:
        size = int(lead.company_size or 0)
        if 100 <= size <= 300:
            score += 3  # Sweet spot
        elif 50 <= size < 100:
            score += 2
        elif 300 < size <= 500:
            score += 1
    except (ValueError, TypeError):
        pass

    # Title scoring
    title = (lead.title or "").lower()
    if "vp" in title or "vice president" in title:
        score += 2
    elif "director" in title:
        score += 2
    elif "head" in title:
        score += 2
    elif "cto" in title:
        score += 3  # Direct decision maker
    elif "manager" in title:
        score += 1

    # Has email
    if lead.email and lead.email_status == "verified":
        score += 2
    elif lead.email:
        score += 1

    # Has LinkedIn (for backup outreach)
    if lead.linkedin_url:
        score += 1

    return score


# =============================================================================
# Main Functions
# =============================================================================

def pull_leads(
    client: ApolloClient,
    icp_type: str = "primary",
    max_leads: int = 1000,
    verbose: bool = True,
) -> list[Lead]:
    """Pull leads from Apollo based on ICP criteria."""

    filters = PRIMARY_ICP if icp_type == "primary" else AGENCY_ICP

    leads = []
    page = 1
    per_page = 100

    if verbose:
        print(f"Pulling {icp_type} ICP leads (max {max_leads})...")

    while len(leads) < max_leads:
        if verbose:
            print(f"  Page {page}... ", end="", flush=True)

        try:
            response = client.search_people(filters, page=page, per_page=per_page)
        except requests.exceptions.HTTPError as e:
            print(f"Error: {e}")
            break

        people = response.get("people", [])

        if not people:
            if verbose:
                print("No more results.")
            break

        for person in people:
            lead = parse_person(person)
            lead.score = score_lead(lead)
            leads.append(lead)

            if len(leads) >= max_leads:
                break

        if verbose:
            print(f"Got {len(people)} leads (total: {len(leads)})")

        # Check if we've hit the end
        pagination = response.get("pagination", {})
        total_pages = pagination.get("total_pages", 1)

        if page >= total_pages:
            break

        page += 1

        # Rate limiting - be nice to the API
        time.sleep(0.3)

    return leads


def enrich_leads(
    client: ApolloClient,
    leads: list[Lead],
    max_enrich: int = 100,
    verbose: bool = True,
) -> list[Lead]:
    """Enrich leads to get emails (COSTS CREDITS)."""

    # Only enrich leads without emails, sorted by score
    to_enrich = [l for l in leads if not l.email]
    to_enrich.sort(key=lambda x: x.score, reverse=True)
    to_enrich = to_enrich[:max_enrich]

    if not to_enrich:
        if verbose:
            print("No leads to enrich.")
        return leads

    if verbose:
        print(f"Enriching top {len(to_enrich)} leads (this costs credits!)...")

    person_ids = [l.id for l in to_enrich]
    enriched_data = client.bulk_enrich(person_ids)

    # Create lookup by ID
    enriched_map = {e.get("id"): e for e in enriched_data}

    # Update leads with enriched data
    for lead in leads:
        if lead.id in enriched_map:
            enriched = enriched_map[lead.id]
            lead.email = enriched.get("email")
            lead.email_status = enriched.get("email_status")
            lead.score = score_lead(lead)  # Re-score with email

    return leads


def save_to_csv(leads: list[Lead], output_path: str, verbose: bool = True):
    """Save leads to CSV file."""

    if not leads:
        print("No leads to save.")
        return

    # Sort by score descending
    leads.sort(key=lambda x: x.score, reverse=True)

    fieldnames = list(leads[0].to_dict().keys())

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for lead in leads:
            writer.writerow(lead.to_dict())

    if verbose:
        print(f"Saved {len(leads)} leads to {output_path}")


def print_summary(leads: list[Lead]):
    """Print summary statistics about the leads."""

    print("\n" + "="*50)
    print("LEAD SUMMARY")
    print("="*50)

    print(f"\nTotal leads: {len(leads)}")

    # With emails
    with_email = [l for l in leads if l.email]
    print(f"With email: {len(with_email)} ({len(with_email)/len(leads)*100:.1f}%)")

    # Score distribution
    tier1 = [l for l in leads if l.score >= 8]
    tier2 = [l for l in leads if 5 <= l.score < 8]
    tier3 = [l for l in leads if l.score < 5]

    print(f"\nScore tiers:")
    print(f"  Tier 1 (8+):  {len(tier1)} leads - reach out first")
    print(f"  Tier 2 (5-7): {len(tier2)} leads - second wave")
    print(f"  Tier 3 (<5):  {len(tier3)} leads - automated only")

    # Top titles
    from collections import Counter
    titles = Counter(l.title for l in leads)
    print(f"\nTop titles:")
    for title, count in titles.most_common(5):
        print(f"  {title}: {count}")

    # Top companies
    companies = Counter(l.company_name for l in leads)
    print(f"\nTop companies:")
    for company, count in companies.most_common(5):
        print(f"  {company}: {count}")

    # Funding stages
    funding = Counter(l.company_funding_stage for l in leads if l.company_funding_stage)
    print(f"\nFunding stages:")
    for stage, count in funding.most_common():
        print(f"  {stage}: {count}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Pull engineering leader leads from Apollo.io"
    )

    parser.add_argument(
        "--output", "-o",
        default="leads.csv",
        help="Output CSV file path (default: leads.csv)"
    )

    parser.add_argument(
        "--max-leads", "-n",
        type=int,
        default=500,
        help="Maximum number of leads to pull (default: 500)"
    )

    parser.add_argument(
        "--icp",
        choices=["primary", "agency", "both"],
        default="primary",
        help="Which ICP to search (default: primary)"
    )

    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Enrich leads to get emails (COSTS CREDITS)"
    )

    parser.add_argument(
        "--max-enrich",
        type=int,
        default=100,
        help="Max leads to enrich (default: 100)"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress verbose output"
    )

    args = parser.parse_args()

    # Get API key
    api_key = os.environ.get("APOLLO_API_KEY")

    if not api_key:
        print("Error: APOLLO_API_KEY environment variable not set.")
        print("\nSet it with:")
        print("  export APOLLO_API_KEY='your-api-key-here'")
        sys.exit(1)

    verbose = not args.quiet
    client = ApolloClient(api_key)

    all_leads = []

    # Pull primary ICP
    if args.icp in ["primary", "both"]:
        leads = pull_leads(
            client,
            icp_type="primary",
            max_leads=args.max_leads,
            verbose=verbose,
        )
        all_leads.extend(leads)

    # Pull agency ICP
    if args.icp in ["agency", "both"]:
        leads = pull_leads(
            client,
            icp_type="agency",
            max_leads=args.max_leads,
            verbose=verbose,
        )
        all_leads.extend(leads)

    # Dedupe by ID
    seen_ids = set()
    unique_leads = []
    for lead in all_leads:
        if lead.id not in seen_ids:
            seen_ids.add(lead.id)
            unique_leads.append(lead)

    if verbose and len(unique_leads) < len(all_leads):
        print(f"\nRemoved {len(all_leads) - len(unique_leads)} duplicates.")

    # Enrich if requested
    if args.enrich:
        unique_leads = enrich_leads(
            client,
            unique_leads,
            max_enrich=args.max_enrich,
            verbose=verbose,
        )

    # Save results
    save_to_csv(unique_leads, args.output, verbose=verbose)

    # Print summary
    if verbose:
        print_summary(unique_leads)


if __name__ == "__main__":
    main()
