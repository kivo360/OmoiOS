#!/usr/bin/env python3
"""
Company Research Enrichment

For each lead, researches their company via Exa web search and uses an LLM
to identify likely pain points and generate a personalized outreach hook.

Usage:
    # Research batch 1
    python research_companies.py simplo_batch1_100.csv -o simplo_batch1_researched.csv

    # Dry run (first 5 only)
    python research_companies.py simplo_batch1_100.csv --limit 5 --dry-run

    # Resume from where you left off (skip already-researched)
    python research_companies.py simplo_batch1_100.csv -o simplo_batch1_researched.csv --resume

Environment:
    EXA_API_KEY - Exa.ai API key for web search
    FIREWORKS_API_KEY - Fireworks.ai API key for LLM analysis
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    sys.exit(1)


# =============================================================================
# Configuration
# =============================================================================

EXA_BASE_URL = "https://api.exa.ai"
FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
FIREWORKS_MODEL = "accounts/fireworks/models/llama-v3p3-70b-instruct"

# Rate limiting
EXA_DELAY = 0.5       # seconds between Exa requests
LLM_DELAY = 0.3       # seconds between LLM requests

SYSTEM_PROMPT = """You are a B2B sales researcher who outputs ONLY valid JSON. Never include markdown, explanations, or anything besides the JSON object."""

ANALYSIS_PROMPT = """Analyze this company and generate a cold email hook.

COMPANY: {company_name}
INDUSTRY: {industry}
EMPLOYEES: {company_size}
CONTACT: {contact_name}, {contact_title}
LOCATION: {location}
WEBSITE: {website}

WEB RESEARCH:
{research_context}

Return a JSON object with exactly these fields:

"company_type": One of: "international_mover", "relocation_consultant", "destination_services", "corporate_relocation", "freight_logistics", "immigration_services", "visa_services", "expat_services", "other"

"pain_points": Array of 2-3 SPECIFIC operational pain points. Not generic — concrete daily frustrations:
- Movers: shipment tracking gaps, vendor coordination across borders, customs delays, slow quote turnaround
- Relocation consultants: client comms across time zones, document collection bottlenecks, status update requests flooding inbox, manually relaying vendor info
- Immigration/visa: case tracking across government portals, document expiry monitoring, client follow-up loops
- Corporate relocation: employee experience tracking, multi-vendor coordination, policy compliance paperwork

"hook": A punchy cold email opening line (max 20 words) that hits their specific pain. Best hooks reference a concrete moment of frustration they'd recognize instantly. Examples of good hooks:
- "Losing leads to other movers because your quote took 6 hours instead of 6 minutes?"
- "How many hours did your team spend this week copy-pasting shipment updates into emails?"
- "Your clients are checking WhatsApp at 3am wondering where their container is."
The hook should make them think "this person gets my world."

"personalization_notes": 1-2 sentences about what makes this company unique — specific services, markets, certifications, or specialties to reference in the email body."""


# =============================================================================
# Exa Search
# =============================================================================

def search_company(company_name: str, industry: str, api_key: str) -> str:
    """Search for company info via Exa."""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }

    # Search for the company
    query = f"{company_name} {industry} services about".strip()
    payload = {
        "query": query,
        "numResults": 3,
        "type": "auto",
        "contents": {
            "text": {
                "maxCharacters": 2000,
            }
        },
    }

    try:
        resp = requests.post(
            f"{EXA_BASE_URL}/search",
            headers=headers,
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if not results:
            return "No web results found."

        context_parts = []
        for r in results:
            title = r.get("title", "")
            url = r.get("url", "")
            text = r.get("text", "")
            if text:
                context_parts.append(f"Source: {title} ({url})\n{text[:1500]}")

        return "\n\n---\n\n".join(context_parts) if context_parts else "No relevant content found."

    except requests.exceptions.RequestException as e:
        return f"Search failed: {e}"


# =============================================================================
# LLM Analysis
# =============================================================================

def analyze_company(
    company_name: str,
    industry: str,
    company_size: str,
    contact_name: str,
    contact_title: str,
    location: str,
    website: str,
    research_context: str,
    api_key: str,
) -> dict:
    """Use Fireworks LLM to analyze company and generate hook."""

    prompt = ANALYSIS_PROMPT.format(
        company_name=company_name,
        industry=industry or "relocation/moving services",
        company_size=company_size or "unknown",
        contact_name=contact_name,
        contact_title=contact_title,
        location=location or "unknown",
        website=website or "not available",
        research_context=research_context,
    )

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": FIREWORKS_MODEL,
        "max_tokens": 1024,
        "temperature": 0.4,
        "top_p": 1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }

    try:
        resp = requests.post(
            FIREWORKS_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"].strip()

        # Clean up potential markdown wrapping
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        result = json.loads(content)
        return result

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        return {
            "company_type": "unknown",
            "pain_points": ["Could not analyze"],
            "hook": "",
            "personalization_notes": f"LLM parse error: {e}",
        }
    except requests.exceptions.RequestException as e:
        return {
            "company_type": "unknown",
            "pain_points": ["Could not analyze"],
            "hook": "",
            "personalization_notes": f"LLM request error: {e}",
        }


# =============================================================================
# Main Pipeline
# =============================================================================

def load_already_researched(output_file: str) -> set:
    """Load emails already researched from output file (for resume)."""
    if not Path(output_file).exists():
        return set()
    with open(output_file) as f:
        reader = csv.DictReader(f)
        return {r.get("email", "").lower() for r in reader}


def research_leads(
    input_file: str,
    output_file: str,
    limit: int = 0,
    dry_run: bool = False,
    resume: bool = False,
    verbose: bool = True,
):
    """Research companies for each lead and enrich with pain points + hooks."""

    exa_key = os.environ.get("EXA_API_KEY")
    fireworks_key = os.environ.get("FIREWORKS_API_KEY")

    if not exa_key:
        print("Error: EXA_API_KEY not set. Export it or add to .env")
        sys.exit(1)
    if not fireworks_key:
        print("Error: FIREWORKS_API_KEY not set. Export it or add to .env")
        sys.exit(1)

    # Load leads
    with open(input_file) as f:
        reader = csv.DictReader(f)
        leads = list(reader)

    if verbose:
        print(f"Loaded {len(leads)} leads from {input_file}")

    # Resume support
    already_done = set()
    existing_rows = []
    if resume and Path(output_file).exists():
        with open(output_file) as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)
            already_done = {r.get("email", "").lower() for r in existing_rows}
        if verbose:
            print(f"Resuming: {len(already_done)} already researched")

    # Limit
    if limit > 0:
        leads = leads[:limit]

    # De-duplicate by company name (don't research same company twice)
    company_cache = {}

    # New fields to add
    new_fields = ["company_type", "pain_points", "hook", "personalization_notes"]

    # Process each lead
    results = list(existing_rows) if resume else []
    processed = 0
    skipped = 0
    errors = 0

    for i, lead in enumerate(leads):
        email = lead.get("email", "").lower()
        company = lead.get("company_name", "").strip()
        name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()

        # Skip if already done (resume mode)
        if email in already_done:
            skipped += 1
            continue

        if verbose:
            print(f"  [{i+1}/{len(leads)}] {company} ({name})...", end=" ", flush=True)

        if dry_run:
            lead["company_type"] = "dry_run"
            lead["pain_points"] = "dry_run"
            lead["hook"] = "dry_run"
            lead["personalization_notes"] = "dry_run"
            results.append(lead)
            if verbose:
                print("(dry run)")
            continue

        # Check company cache
        if company in company_cache:
            analysis = company_cache[company]
            if verbose:
                print("(cached)", end=" ")
        else:
            # Step 1: Exa search
            research_context = search_company(
                company,
                lead.get("company_industry", ""),
                exa_key,
            )
            time.sleep(EXA_DELAY)

            # Step 2: LLM analysis
            analysis = analyze_company(
                company_name=company,
                industry=lead.get("company_industry", ""),
                company_size=lead.get("company_size", ""),
                contact_name=name,
                contact_title=lead.get("title", ""),
                location=lead.get("location", ""),
                website=lead.get("company_website", ""),
                research_context=research_context,
                api_key=fireworks_key,
            )
            time.sleep(LLM_DELAY)

            company_cache[company] = analysis

        # Enrich lead with analysis
        lead["company_type"] = analysis.get("company_type", "unknown")
        pain_points = analysis.get("pain_points", [])
        lead["pain_points"] = " | ".join(pain_points) if isinstance(pain_points, list) else str(pain_points)
        lead["hook"] = analysis.get("hook", "")
        lead["personalization_notes"] = analysis.get("personalization_notes", "")

        results.append(lead)
        processed += 1

        if verbose:
            hook = lead["hook"][:60] + "..." if len(lead.get("hook", "")) > 60 else lead.get("hook", "")
            print(f"✓ [{analysis.get('company_type', '?')}] {hook}")

        # Save checkpoint every 10 leads
        if processed % 10 == 0 and not dry_run:
            _save_results(results, output_file, new_fields)
            if verbose:
                print(f"    [checkpoint: {processed} researched, {len(results)} total saved]")

    # Final save
    if not dry_run:
        _save_results(results, output_file, new_fields)

    # Summary
    print(f"\n{'='*60}")
    print("RESEARCH SUMMARY")
    print(f"{'='*60}")
    print(f"Total leads: {len(leads)}")
    print(f"Researched: {processed}")
    print(f"Skipped (already done): {skipped}")
    print(f"Errors: {errors}")
    print(f"Unique companies researched: {len(company_cache)}")
    print(f"Output: {output_file}")

    if results:
        from collections import Counter
        types = Counter(r.get("company_type", "unknown") for r in results)
        print(f"\nCompany types:")
        for t, c in types.most_common():
            print(f"  {t}: {c}")


def _save_results(results: list, output_file: str, new_fields: list):
    """Save results to CSV."""
    if not results:
        return

    # Get all fieldnames (original + new)
    fieldnames = list(results[0].keys())
    for f in new_fields:
        if f not in fieldnames:
            fieldnames.append(f)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Research companies and generate personalized outreach hooks"
    )

    parser.add_argument("input", help="Input CSV with leads")
    parser.add_argument("--output", "-o", default=None, help="Output CSV (default: input_researched.csv)")
    parser.add_argument("--limit", "-n", type=int, default=0, help="Limit to first N leads (0=all)")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually call APIs")
    parser.add_argument("--resume", action="store_true", help="Skip already-researched leads in output file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress verbose output")

    args = parser.parse_args()

    # Default output file
    if args.output is None:
        stem = Path(args.input).stem
        args.output = f"{stem}_researched.csv"

    research_leads(
        input_file=args.input,
        output_file=args.output,
        limit=args.limit,
        dry_run=args.dry_run,
        resume=args.resume,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
