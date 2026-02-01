# Lead Generation Scripts

Scripts for pulling and processing leads from Apollo.io.

## Setup

1. Install dependencies:

```bash
pip install requests
```

2. Get your Apollo API key from: https://app.apollo.io/#/settings/integrations/api

3. Set the environment variable:

```bash
export APOLLO_API_KEY="your-api-key-here"
```

## Usage

### Basic: Pull 500 leads (no enrichment)

```bash
python apollo_lead_finder.py --output leads.csv --max-leads 500
```

This is FREE - the search endpoint doesn't cost credits.

### Pull and enrich top 100 (costs credits)

```bash
python apollo_lead_finder.py --output leads.csv --max-leads 500 --enrich --max-enrich 100
```

### Pull both ICPs

```bash
python apollo_lead_finder.py --output leads.csv --icp both --max-leads 1000
```

### Full command with all options

```bash
python apollo_lead_finder.py \
    --output engineering_leaders.csv \
    --max-leads 2000 \
    --icp both \
    --enrich \
    --max-enrich 200
```

## Output

The script outputs a CSV with these columns:

| Column | Description |
|--------|-------------|
| id | Apollo ID (for enrichment) |
| first_name | First name |
| last_name | Last name |
| full_name | Full name |
| title | Job title |
| email | Email (if enriched) |
| email_status | verified/guessed/etc |
| linkedin_url | LinkedIn profile |
| company_name | Company name |
| company_website | Company website |
| company_size | Employee count |
| company_funding_stage | Series A/B/C etc |
| company_industry | Industry |
| company_linkedin_url | Company LinkedIn |
| location | City/State/Country |
| score | Lead score (0-15) |
| pulled_at | Timestamp |

## Lead Scoring

Leads are scored 0-15 based on:

- **Funding stage**: Series B (+3), Series A/C (+2)
- **Company size**: 100-300 (+3), 50-100 (+2), 300-500 (+1)
- **Title**: CTO (+3), VP/Director/Head (+2), Manager (+1)
- **Has verified email**: +2
- **Has email**: +1
- **Has LinkedIn**: +1

**Tiers:**
- Tier 1 (8+): Reach out first, personalize heavily
- Tier 2 (5-7): Second wave, semi-personalized
- Tier 3 (<5): Automated sequences only

## ICP Definitions

### Primary: Engineering Leaders at Funded Startups

- VP/Director/Head of Engineering, CTO, Engineering Manager
- 50-500 employees
- Series A, B, or C funded
- US, Canada, UK

### Secondary: Agency Technical Leadership

- CTO, Technical Director, Head of Engineering
- 20-200 employees
- Digital agencies, software consultancies

## Cost

- **Search**: FREE (unlimited)
- **Enrichment**: 1 credit per person

With Apollo's basic plan ($49/mo), you get ~500 enrichment credits/month.

## Next Steps After Pulling Leads

1. Review the CSV, check quality
2. Verify emails with NeverBounce or ZeroBounce
3. Score and prioritize (Tier 1 first)
4. Load into your sending tool (Instantly, Smartlead)
5. Start outreach sequences
