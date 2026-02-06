#!/usr/bin/env python3
"""
Email Outreach System for OpenClaw

Sends cold emails from lead list with A/B testing and tracks performance.

Features:
- Sends emails via SMTP (Gmail/custom)
- A/B test variants
- Tracks sends, opens (via pixel), replies
- Heartbeat monitoring for periodic analysis
- Conversion analysis by metadata

Usage:
    # Send emails
    python email_outreach.py send --leads final_100_leads.csv --limit 10 --dry-run

    # Check performance
    python email_outreach.py analyze --campaign campaign_001

    # Run heartbeat check
    python email_outreach.py heartbeat --campaign campaign_001
"""

import argparse
import csv
import json
import os
import smtplib
import sqlite3
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from pathlib import Path


# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "outreach.db"

# Email templates
TEMPLATES = {
    "A": {
        "subject": "Quick question about your WhatsApp inbox",
        "body": """Hi {first_name},

I noticed you help people relocate — quick question:

How many times a day do you answer "What documents do I need?" on WhatsApp?

I built a tool that handles those repetitive questions automatically, so you can focus on the clients who are actually ready to move forward.

It sounds exactly like you. Clients don't know the difference.

Want me to show you how it works? Takes 15 minutes.

— Kevin

P.S. If this isn't relevant, just reply "remove" and I won't email again.""",
    },
    "B": {
        "subject": "Losing leads while you sleep?",
        "body": """Hi {first_name},

What if your WhatsApp replied instantly at 3am while you slept?

One relocation consultant I worked with closed 3 extra clients in her first month — just from faster response times.

I build custom AI assistants for relocation professionals. $49 one-time setup. Handles FAQs, qualifies leads, books consultations.

Worth a quick look?

— Kevin

P.S. If this isn't relevant, just reply "remove" and I won't email again.""",
    },
}


# =============================================================================
# Database
# =============================================================================

def init_db():
    """Initialize SQLite database for tracking."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Campaigns table
    c.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY,
            name TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'active',
            notes TEXT
        )
    """)

    # Emails sent
    c.execute("""
        CREATE TABLE IF NOT EXISTS emails_sent (
            id TEXT PRIMARY KEY,
            campaign_id TEXT,
            lead_email TEXT,
            lead_name TEXT,
            lead_title TEXT,
            lead_company TEXT,
            lead_location TEXT,
            title_category TEXT,
            variant TEXT,
            subject TEXT,
            sent_at TEXT,
            tracking_pixel_id TEXT,
            opened_at TEXT,
            replied_at TEXT,
            converted_at TEXT,
            unsubscribed INTEGER DEFAULT 0,
            conversion_score REAL,
            notes TEXT,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        )
    """)

    # Heartbeat logs
    c.execute("""
        CREATE TABLE IF NOT EXISTS heartbeat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id TEXT,
            checked_at TEXT,
            total_sent INTEGER,
            total_opened INTEGER,
            total_replied INTEGER,
            total_converted INTEGER,
            open_rate REAL,
            reply_rate REAL,
            conversion_rate REAL,
            variant_a_stats TEXT,
            variant_b_stats TEXT,
            insights TEXT
        )
    """)

    conn.commit()
    conn.close()


def get_db():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


# =============================================================================
# Email Sending
# =============================================================================

@dataclass
class EmailConfig:
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    from_email: str
    from_name: str


def get_email_config() -> EmailConfig:
    """Load email config from environment."""
    return EmailConfig(
        smtp_server=os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        username=os.environ.get("SMTP_USERNAME", ""),
        password=os.environ.get("SMTP_PASSWORD", ""),
        from_email=os.environ.get("FROM_EMAIL", "kevin@omoios.dev"),
        from_name=os.environ.get("FROM_NAME", "Kevin"),
    )


def render_email(template: dict, lead: dict) -> tuple[str, str]:
    """Render email template with lead data."""
    subject = template["subject"]
    body = template["body"].format(
        first_name=lead.get("first_name", "there"),
        last_name=lead.get("last_name", ""),
        company=lead.get("company_name", "your company"),
        title=lead.get("title", ""),
        location=lead.get("location", ""),
    )
    return subject, body


def send_email(
    config: EmailConfig,
    to_email: str,
    subject: str,
    body: str,
    tracking_id: str,
    dry_run: bool = False,
) -> bool:
    """Send an email via SMTP."""
    if dry_run:
        print(f"  [DRY RUN] Would send to: {to_email}")
        print(f"  Subject: {subject}")
        print(f"  Body preview: {body[:100]}...")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{config.from_name} <{config.from_email}>"
        msg["To"] = to_email

        # Plain text
        msg.attach(MIMEText(body, "plain"))

        # HTML with tracking pixel (optional)
        # html_body = f"{body.replace(chr(10), '<br>')}<img src='https://yourtracker.com/pixel/{tracking_id}' width='1' height='1'>"
        # msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
            server.starttls()
            server.login(config.username, config.password)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"  Error sending to {to_email}: {e}")
        return False


# =============================================================================
# Campaign Management
# =============================================================================

def create_campaign(name: str) -> str:
    """Create a new campaign."""
    campaign_id = f"campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO campaigns (id, name, created_at) VALUES (?, ?, ?)",
        (campaign_id, name, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    return campaign_id


def send_campaign_emails(
    leads_file: str,
    campaign_id: str,
    limit: int = 10,
    dry_run: bool = False,
    delay_seconds: int = 30,
):
    """Send emails to leads from CSV."""
    config = get_email_config()

    if not dry_run and not config.username:
        print("Error: SMTP credentials not configured.")
        print("Set SMTP_USERNAME and SMTP_PASSWORD environment variables.")
        return

    # Load leads
    with open(leads_file, 'r') as f:
        reader = csv.DictReader(f)
        leads = list(reader)

    print(f"Loaded {len(leads)} leads from {leads_file}")

    # Get already sent emails for this campaign
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT lead_email FROM emails_sent WHERE campaign_id = ?", (campaign_id,))
    already_sent = {row[0] for row in c.fetchall()}

    # Filter to unsent leads with emails
    to_send = [
        l for l in leads
        if l.get('email') and l['email'] not in already_sent
    ][:limit]

    print(f"Sending to {len(to_send)} new leads (limit: {limit})")

    sent_count = 0
    for i, lead in enumerate(to_send, 1):
        variant = lead.get('email_variant', 'A')
        template = TEMPLATES.get(variant, TEMPLATES['A'])

        subject, body = render_email(template, lead)
        tracking_id = str(uuid.uuid4())

        print(f"\n[{i}/{len(to_send)}] {lead['email']} (Variant {variant})")

        success = send_email(
            config=config,
            to_email=lead['email'],
            subject=subject,
            body=body,
            tracking_id=tracking_id,
            dry_run=dry_run,
        )

        if success:
            # Record in database
            c.execute("""
                INSERT INTO emails_sent (
                    id, campaign_id, lead_email, lead_name, lead_title,
                    lead_company, lead_location, title_category, variant,
                    subject, sent_at, tracking_pixel_id, conversion_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tracking_id,
                campaign_id,
                lead['email'],
                f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
                lead.get('title', ''),
                lead.get('company_name', ''),
                lead.get('location', ''),
                lead.get('title_category', ''),
                variant,
                subject,
                datetime.now().isoformat(),
                tracking_id,
                float(lead.get('conversion_score', 0)),
            ))
            conn.commit()
            sent_count += 1

        # Delay between sends (avoid spam filters)
        if not dry_run and i < len(to_send):
            print(f"  Waiting {delay_seconds}s before next send...")
            time.sleep(delay_seconds)

    conn.close()
    print(f"\n✓ Sent {sent_count} emails for campaign {campaign_id}")


# =============================================================================
# Performance Analysis
# =============================================================================

def analyze_campaign(campaign_id: str):
    """Analyze campaign performance."""
    conn = get_db()
    c = conn.cursor()

    # Get all emails for campaign
    c.execute("""
        SELECT * FROM emails_sent WHERE campaign_id = ?
    """, (campaign_id,))

    columns = [d[0] for d in c.description]
    emails = [dict(zip(columns, row)) for row in c.fetchall()]

    if not emails:
        print(f"No emails found for campaign {campaign_id}")
        return

    # Overall stats
    total = len(emails)
    opened = sum(1 for e in emails if e['opened_at'])
    replied = sum(1 for e in emails if e['replied_at'])
    converted = sum(1 for e in emails if e['converted_at'])
    unsubscribed = sum(1 for e in emails if e['unsubscribed'])

    print("="*60)
    print(f"CAMPAIGN ANALYSIS: {campaign_id}")
    print("="*60)

    print(f"\n📊 OVERALL PERFORMANCE")
    print(f"  Total sent:     {total}")
    print(f"  Opened:         {opened} ({opened/total*100:.1f}%)")
    print(f"  Replied:        {replied} ({replied/total*100:.1f}%)")
    print(f"  Converted:      {converted} ({converted/total*100:.1f}%)")
    print(f"  Unsubscribed:   {unsubscribed} ({unsubscribed/total*100:.1f}%)")

    # A/B comparison
    variant_a = [e for e in emails if e['variant'] == 'A']
    variant_b = [e for e in emails if e['variant'] == 'B']

    print(f"\n🔬 A/B TEST RESULTS")
    print("-"*40)

    for name, group in [("Variant A", variant_a), ("Variant B", variant_b)]:
        if not group:
            continue
        g_total = len(group)
        g_opened = sum(1 for e in group if e['opened_at'])
        g_replied = sum(1 for e in group if e['replied_at'])
        g_converted = sum(1 for e in group if e['converted_at'])

        print(f"\n  {name} (n={g_total})")
        print(f"    Open rate:    {g_opened/g_total*100:.1f}%")
        print(f"    Reply rate:   {g_replied/g_total*100:.1f}%")
        print(f"    Convert rate: {g_converted/g_total*100:.1f}%")

    # By title category
    print(f"\n📋 BY TITLE CATEGORY")
    print("-"*40)

    from collections import defaultdict
    by_category = defaultdict(list)
    for e in emails:
        by_category[e['title_category'] or 'unknown'].append(e)

    for cat, group in sorted(by_category.items(), key=lambda x: -len(x[1])):
        g_total = len(group)
        g_replied = sum(1 for e in group if e['replied_at'])
        g_converted = sum(1 for e in group if e['converted_at'])

        print(f"  {cat}: {g_total} sent, {g_replied} replied ({g_replied/g_total*100:.1f}%), {g_converted} converted")

    # By conversion score buckets
    print(f"\n📈 BY CONVERSION SCORE")
    print("-"*40)

    score_buckets = {"high (10+)": [], "medium (5-9)": [], "low (<5)": []}
    for e in emails:
        score = e['conversion_score'] or 0
        if score >= 10:
            score_buckets["high (10+)"].append(e)
        elif score >= 5:
            score_buckets["medium (5-9)"].append(e)
        else:
            score_buckets["low (<5)"].append(e)

    for bucket, group in score_buckets.items():
        if not group:
            continue
        g_total = len(group)
        g_replied = sum(1 for e in group if e['replied_at'])
        g_converted = sum(1 for e in group if e['converted_at'])

        print(f"  {bucket}: {g_total} sent, {g_replied} replied, {g_converted} converted")

    # Top performers
    print(f"\n⭐ TOP PERFORMERS (replied or converted)")
    print("-"*40)

    top = [e for e in emails if e['replied_at'] or e['converted_at']]
    for e in top[:10]:
        status = "💰 CONVERTED" if e['converted_at'] else "💬 REPLIED"
        print(f"  {status} {e['lead_name']} @ {e['lead_company']}")
        print(f"           {e['lead_title']} | Variant {e['variant']} | Score {e['conversion_score']}")

    conn.close()


def run_heartbeat(campaign_id: str):
    """Run periodic heartbeat check and log results."""
    conn = get_db()
    c = conn.cursor()

    # Get stats
    c.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
            SUM(CASE WHEN replied_at IS NOT NULL THEN 1 ELSE 0 END) as replied,
            SUM(CASE WHEN converted_at IS NOT NULL THEN 1 ELSE 0 END) as converted
        FROM emails_sent WHERE campaign_id = ?
    """, (campaign_id,))

    row = c.fetchone()
    total, opened, replied, converted = row

    if total == 0:
        print("No emails sent yet.")
        return

    open_rate = opened / total * 100
    reply_rate = replied / total * 100
    conversion_rate = converted / total * 100

    # Get variant stats
    variant_stats = {}
    for variant in ['A', 'B']:
        c.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
                SUM(CASE WHEN replied_at IS NOT NULL THEN 1 ELSE 0 END) as replied,
                SUM(CASE WHEN converted_at IS NOT NULL THEN 1 ELSE 0 END) as converted
            FROM emails_sent WHERE campaign_id = ? AND variant = ?
        """, (campaign_id, variant))
        v_row = c.fetchone()
        variant_stats[variant] = {
            "total": v_row[0],
            "opened": v_row[1],
            "replied": v_row[2],
            "converted": v_row[3],
        }

    # Generate insights
    insights = []

    if variant_stats['A']['total'] > 0 and variant_stats['B']['total'] > 0:
        a_reply = variant_stats['A']['replied'] / variant_stats['A']['total'] if variant_stats['A']['total'] else 0
        b_reply = variant_stats['B']['replied'] / variant_stats['B']['total'] if variant_stats['B']['total'] else 0

        if a_reply > b_reply * 1.2:
            insights.append("Variant A (Pain Focus) is outperforming B by 20%+")
        elif b_reply > a_reply * 1.2:
            insights.append("Variant B (Benefit Focus) is outperforming A by 20%+")
        else:
            insights.append("A/B variants performing similarly - need more data")

    if reply_rate < 2:
        insights.append("Low reply rate - consider testing new subject lines")
    elif reply_rate > 10:
        insights.append("Strong reply rate - scale up sending volume")

    # Log heartbeat
    c.execute("""
        INSERT INTO heartbeat_logs (
            campaign_id, checked_at, total_sent, total_opened, total_replied,
            total_converted, open_rate, reply_rate, conversion_rate,
            variant_a_stats, variant_b_stats, insights
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        campaign_id,
        datetime.now().isoformat(),
        total, opened, replied, converted,
        open_rate, reply_rate, conversion_rate,
        json.dumps(variant_stats['A']),
        json.dumps(variant_stats['B']),
        json.dumps(insights),
    ))
    conn.commit()

    # Print heartbeat report
    print("="*60)
    print(f"💓 HEARTBEAT: {campaign_id}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    print(f"\n📊 Current Stats:")
    print(f"   Sent: {total} | Opened: {opened} ({open_rate:.1f}%) | Replied: {replied} ({reply_rate:.1f}%) | Converted: {converted}")

    print(f"\n🔬 A/B Performance:")
    print(f"   Variant A: {variant_stats['A']['replied']}/{variant_stats['A']['total']} replied")
    print(f"   Variant B: {variant_stats['B']['replied']}/{variant_stats['B']['total']} replied")

    print(f"\n💡 Insights:")
    for insight in insights:
        print(f"   • {insight}")

    conn.close()


def mark_reply(campaign_id: str, email: str):
    """Mark an email as replied."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE emails_sent
        SET replied_at = ?
        WHERE campaign_id = ? AND lead_email = ?
    """, (datetime.now().isoformat(), campaign_id, email))
    conn.commit()
    print(f"✓ Marked {email} as replied")
    conn.close()


def mark_converted(campaign_id: str, email: str):
    """Mark an email as converted."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE emails_sent
        SET converted_at = ?
        WHERE campaign_id = ? AND lead_email = ?
    """, (datetime.now().isoformat(), campaign_id, email))
    conn.commit()
    print(f"✓ Marked {email} as converted")
    conn.close()


# =============================================================================
# CLI
# =============================================================================

def main():
    init_db()

    parser = argparse.ArgumentParser(description="Email Outreach System")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Send command
    send_parser = subparsers.add_parser("send", help="Send campaign emails")
    send_parser.add_argument("--leads", required=True, help="Leads CSV file")
    send_parser.add_argument("--campaign", help="Campaign ID (creates new if not provided)")
    send_parser.add_argument("--name", default="OpenClaw Outreach", help="Campaign name")
    send_parser.add_argument("--limit", type=int, default=10, help="Max emails to send")
    send_parser.add_argument("--delay", type=int, default=30, help="Seconds between emails")
    send_parser.add_argument("--dry-run", action="store_true", help="Don't actually send")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze campaign performance")
    analyze_parser.add_argument("--campaign", required=True, help="Campaign ID")

    # Heartbeat command
    hb_parser = subparsers.add_parser("heartbeat", help="Run heartbeat check")
    hb_parser.add_argument("--campaign", required=True, help="Campaign ID")

    # Mark reply command
    reply_parser = subparsers.add_parser("mark-reply", help="Mark email as replied")
    reply_parser.add_argument("--campaign", required=True, help="Campaign ID")
    reply_parser.add_argument("--email", required=True, help="Lead email")

    # Mark converted command
    convert_parser = subparsers.add_parser("mark-converted", help="Mark email as converted")
    convert_parser.add_argument("--campaign", required=True, help="Campaign ID")
    convert_parser.add_argument("--email", required=True, help="Lead email")

    # List campaigns command
    list_parser = subparsers.add_parser("list", help="List campaigns")

    args = parser.parse_args()

    if args.command == "send":
        campaign_id = args.campaign or create_campaign(args.name)
        print(f"Campaign ID: {campaign_id}")
        send_campaign_emails(
            leads_file=args.leads,
            campaign_id=campaign_id,
            limit=args.limit,
            dry_run=args.dry_run,
            delay_seconds=args.delay,
        )

    elif args.command == "analyze":
        analyze_campaign(args.campaign)

    elif args.command == "heartbeat":
        run_heartbeat(args.campaign)

    elif args.command == "mark-reply":
        mark_reply(args.campaign, args.email)

    elif args.command == "mark-converted":
        mark_converted(args.campaign, args.email)

    elif args.command == "list":
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, name, created_at, status FROM campaigns ORDER BY created_at DESC")
        campaigns = c.fetchall()
        print("\nCampaigns:")
        for cid, name, created, status in campaigns:
            print(f"  {cid} | {name} | {created} | {status}")
        conn.close()


if __name__ == "__main__":
    main()
