#!/usr/bin/env python3
"""
Heartbeat Monitor for Email Campaigns

Runs periodic checks on campaign performance and generates insights.
Can be run via cron or manually.

Usage:
    # One-time check
    python heartbeat_monitor.py --campaign campaign_001

    # Continuous monitoring (checks every N minutes)
    python heartbeat_monitor.py --campaign campaign_001 --watch --interval 60

    # Generate report
    python heartbeat_monitor.py --campaign campaign_001 --report
"""

import argparse
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "outreach.db"


def get_db():
    return sqlite3.connect(DB_PATH)


def get_campaign_stats(campaign_id: str) -> dict:
    """Get comprehensive campaign statistics."""
    conn = get_db()
    c = conn.cursor()

    # Overall stats
    c.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
            SUM(CASE WHEN replied_at IS NOT NULL THEN 1 ELSE 0 END) as replied,
            SUM(CASE WHEN converted_at IS NOT NULL THEN 1 ELSE 0 END) as converted,
            SUM(CASE WHEN unsubscribed = 1 THEN 1 ELSE 0 END) as unsubscribed
        FROM emails_sent WHERE campaign_id = ?
    """, (campaign_id,))

    row = c.fetchone()
    total, opened, replied, converted, unsubscribed = row

    if total == 0:
        return {"error": "No emails sent"}

    # By variant
    variants = {}
    for v in ['A', 'B']:
        c.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
                SUM(CASE WHEN replied_at IS NOT NULL THEN 1 ELSE 0 END) as replied,
                SUM(CASE WHEN converted_at IS NOT NULL THEN 1 ELSE 0 END) as converted
            FROM emails_sent WHERE campaign_id = ? AND variant = ?
        """, (campaign_id, v))
        vrow = c.fetchone()
        if vrow[0] > 0:
            variants[v] = {
                "total": vrow[0],
                "opened": vrow[1],
                "replied": vrow[2],
                "converted": vrow[3],
                "reply_rate": vrow[2] / vrow[0] * 100,
                "convert_rate": vrow[3] / vrow[0] * 100,
            }

    # By title category
    c.execute("""
        SELECT
            title_category,
            COUNT(*) as total,
            SUM(CASE WHEN replied_at IS NOT NULL THEN 1 ELSE 0 END) as replied,
            SUM(CASE WHEN converted_at IS NOT NULL THEN 1 ELSE 0 END) as converted
        FROM emails_sent
        WHERE campaign_id = ?
        GROUP BY title_category
    """, (campaign_id,))

    by_category = {}
    for cat, cat_total, cat_replied, cat_converted in c.fetchall():
        by_category[cat or 'unknown'] = {
            "total": cat_total,
            "replied": cat_replied,
            "converted": cat_converted,
            "reply_rate": cat_replied / cat_total * 100 if cat_total > 0 else 0,
        }

    # By conversion score bucket
    c.execute("""
        SELECT
            CASE
                WHEN conversion_score >= 10 THEN 'high'
                WHEN conversion_score >= 5 THEN 'medium'
                ELSE 'low'
            END as bucket,
            COUNT(*) as total,
            SUM(CASE WHEN replied_at IS NOT NULL THEN 1 ELSE 0 END) as replied,
            SUM(CASE WHEN converted_at IS NOT NULL THEN 1 ELSE 0 END) as converted
        FROM emails_sent
        WHERE campaign_id = ?
        GROUP BY bucket
    """, (campaign_id,))

    by_score = {}
    for bucket, b_total, b_replied, b_converted in c.fetchall():
        by_score[bucket] = {
            "total": b_total,
            "replied": b_replied,
            "converted": b_converted,
            "reply_rate": b_replied / b_total * 100 if b_total > 0 else 0,
        }

    conn.close()

    return {
        "timestamp": datetime.now().isoformat(),
        "campaign_id": campaign_id,
        "overall": {
            "total": total,
            "opened": opened,
            "replied": replied,
            "converted": converted,
            "unsubscribed": unsubscribed,
            "open_rate": opened / total * 100,
            "reply_rate": replied / total * 100,
            "convert_rate": converted / total * 100,
        },
        "by_variant": variants,
        "by_category": by_category,
        "by_score": by_score,
    }


def generate_insights(stats: dict) -> list[str]:
    """Generate actionable insights from campaign stats."""
    insights = []
    overall = stats.get("overall", {})
    variants = stats.get("by_variant", {})
    by_category = stats.get("by_category", {})
    by_score = stats.get("by_score", {})

    # Sample size check
    if overall.get("total", 0) < 20:
        insights.append("⚠️ Small sample size - results may not be statistically significant")

    # Overall performance
    reply_rate = overall.get("reply_rate", 0)
    if reply_rate >= 10:
        insights.append("🔥 Excellent reply rate (10%+) - this offer is resonating!")
    elif reply_rate >= 5:
        insights.append("✅ Good reply rate (5-10%) - keep optimizing")
    elif reply_rate >= 2:
        insights.append("📊 Average reply rate (2-5%) - test new angles")
    else:
        insights.append("⚠️ Low reply rate (<2%) - major changes needed")

    # A/B test winner
    if 'A' in variants and 'B' in variants:
        a_rate = variants['A'].get('reply_rate', 0)
        b_rate = variants['B'].get('reply_rate', 0)

        if a_rate > b_rate * 1.5 and variants['A']['total'] >= 10:
            insights.append(f"🏆 WINNER: Variant A (Pain Focus) - {a_rate:.1f}% vs {b_rate:.1f}%")
            insights.append("   → Scale up Variant A, pause Variant B")
        elif b_rate > a_rate * 1.5 and variants['B']['total'] >= 10:
            insights.append(f"🏆 WINNER: Variant B (Benefit Focus) - {b_rate:.1f}% vs {a_rate:.1f}%")
            insights.append("   → Scale up Variant B, pause Variant A")
        elif abs(a_rate - b_rate) < 1:
            insights.append("🔄 A/B test inconclusive - try more differentiated variants")

    # Best performing segments
    if by_category:
        best_cat = max(by_category.items(), key=lambda x: x[1].get('reply_rate', 0))
        if best_cat[1].get('reply_rate', 0) > reply_rate * 1.5:
            insights.append(f"🎯 Best segment: {best_cat[0]} ({best_cat[1]['reply_rate']:.1f}% reply rate)")
            insights.append(f"   → Double down on {best_cat[0]} leads")

    # Score correlation
    if by_score:
        high = by_score.get('high', {}).get('reply_rate', 0)
        low = by_score.get('low', {}).get('reply_rate', 0)

        if high > low * 2:
            insights.append("📈 High-score leads convert 2x+ better - prioritize them")
        elif low > high:
            insights.append("🤔 Scoring model may need adjustment - low scores outperforming")

    # Conversion funnel
    if overall.get('replied', 0) > 0 and overall.get('converted', 0) == 0:
        insights.append("💬 Getting replies but no conversions - improve follow-up sequence")
    elif overall.get('converted', 0) > 0:
        convert_from_reply = overall['converted'] / overall['replied'] * 100 if overall['replied'] else 0
        insights.append(f"💰 Reply→Conversion rate: {convert_from_reply:.0f}%")

    return insights


def print_heartbeat(stats: dict, insights: list[str]):
    """Print formatted heartbeat report."""
    overall = stats.get("overall", {})
    variants = stats.get("by_variant", {})

    print("\n" + "="*70)
    print(f"💓 HEARTBEAT REPORT - {stats.get('campaign_id', 'Unknown')}")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    print(f"""
📊 OVERALL METRICS
   ┌─────────────┬─────────┬─────────┐
   │ Metric      │ Count   │ Rate    │
   ├─────────────┼─────────┼─────────┤
   │ Sent        │ {overall.get('total', 0):>7} │         │
   │ Opened      │ {overall.get('opened', 0):>7} │ {overall.get('open_rate', 0):>6.1f}% │
   │ Replied     │ {overall.get('replied', 0):>7} │ {overall.get('reply_rate', 0):>6.1f}% │
   │ Converted   │ {overall.get('converted', 0):>7} │ {overall.get('convert_rate', 0):>6.1f}% │
   │ Unsub       │ {overall.get('unsubscribed', 0):>7} │         │
   └─────────────┴─────────┴─────────┘
""")

    if variants:
        print("🔬 A/B TEST COMPARISON")
        print("   ┌──────────┬───────┬─────────┬──────────┬───────────┐")
        print("   │ Variant  │ Sent  │ Replied │ Reply %  │ Converted │")
        print("   ├──────────┼───────┼─────────┼──────────┼───────────┤")
        for v, data in sorted(variants.items()):
            name = "A (Pain)" if v == 'A' else "B (Benefit)"
            print(f"   │ {name:<8} │ {data['total']:>5} │ {data['replied']:>7} │ {data['reply_rate']:>7.1f}% │ {data['converted']:>9} │")
        print("   └──────────┴───────┴─────────┴──────────┴───────────┘")

    by_cat = stats.get("by_category", {})
    if by_cat:
        print("\n📋 BY TITLE CATEGORY")
        sorted_cats = sorted(by_cat.items(), key=lambda x: -x[1].get('reply_rate', 0))
        for cat, data in sorted_cats[:5]:
            bar = "█" * int(data['reply_rate'] / 2)
            print(f"   {cat:<15} {data['replied']:>2}/{data['total']:<3} replied ({data['reply_rate']:>5.1f}%) {bar}")

    print("\n💡 INSIGHTS & RECOMMENDATIONS")
    print("   " + "-"*50)
    for insight in insights:
        print(f"   {insight}")

    print("\n" + "="*70 + "\n")


def watch_campaign(campaign_id: str, interval_minutes: int = 60):
    """Continuously monitor campaign."""
    print(f"👀 Watching campaign {campaign_id} (checking every {interval_minutes} min)")
    print("   Press Ctrl+C to stop\n")

    while True:
        stats = get_campaign_stats(campaign_id)
        if "error" not in stats:
            insights = generate_insights(stats)
            print_heartbeat(stats, insights)
        else:
            print(f"   {stats['error']}")

        time.sleep(interval_minutes * 60)


def generate_report(campaign_id: str, output_file: str = None):
    """Generate detailed JSON report."""
    stats = get_campaign_stats(campaign_id)
    if "error" in stats:
        print(stats["error"])
        return

    insights = generate_insights(stats)
    stats["insights"] = insights

    # Get individual email details
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT lead_email, lead_name, lead_title, lead_company, title_category,
               variant, conversion_score, sent_at, replied_at, converted_at
        FROM emails_sent
        WHERE campaign_id = ?
        ORDER BY conversion_score DESC
    """, (campaign_id,))

    columns = ['email', 'name', 'title', 'company', 'category', 'variant', 'score', 'sent', 'replied', 'converted']
    stats["emails"] = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"Report saved to {output_file}")
    else:
        print(json.dumps(stats, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Campaign Heartbeat Monitor")
    parser.add_argument("--campaign", required=True, help="Campaign ID")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring mode")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in minutes")
    parser.add_argument("--report", action="store_true", help="Generate detailed JSON report")
    parser.add_argument("--output", help="Output file for report")

    args = parser.parse_args()

    if args.report:
        generate_report(args.campaign, args.output)
    elif args.watch:
        watch_campaign(args.campaign, args.interval)
    else:
        stats = get_campaign_stats(args.campaign)
        if "error" not in stats:
            insights = generate_insights(stats)
            print_heartbeat(stats, insights)
        else:
            print(stats["error"])


if __name__ == "__main__":
    main()
