#!/usr/bin/env python3
import argparse
import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.cli_common import DEFAULT_NEWS_ARTICLES_DB, resolve_path  # noqa: E402

def get_stats(db_path):
    if not Path(db_path).exists():
        return None
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        # Total articles
        total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        
        # Articles today (UTC)
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        today_count = conn.execute("SELECT COUNT(*) FROM articles WHERE fetched_at_utc >= ?", (today,)).fetchone()[0]
        
        # Providers summary
        providers = conn.execute("SELECT provider_best, COUNT(*) as count FROM articles GROUP BY provider_best").fetchall()
        provider_stats = {row['provider_best']: row['count'] for row in providers}
        
        # Recent runs
        recent_runs = conn.execute("SELECT run_id, provider, status, fetched, inserted, finished_at as ended_at_utc FROM provider_runs ORDER BY started_at DESC LIMIT 5").fetchall()
        runs_list = [dict(row) for row in recent_runs]
        
        return {
            "total_articles": total,
            "today_articles": today_count,
            "provider_stats": provider_stats,
            "recent_runs": runs_list,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    finally:
        conn.close()

def generate_markdown(stats):
    if not stats:
        return "No news database found."
    
    md = f"### 📰 News Ingestion Progress\n\n"
    md += f"**Total Articles:** {stats['total_articles']}\n"
    md += f"**New Today:** {stats['today_articles']}\n\n"
    
    md += "| Provider | Articles |\n"
    md += "| :--- | :--- |\n"
    for provider, count in stats['provider_stats'].items():
        md += f"| {provider} | {count} |\n"
    
    md += "\n**Recent Runs:**\n"
    md += "| Run ID | Provider | Status | In/Out |\n"
    md += "| :--- | :--- | :--- | :--- |\n"
    for run in stats['recent_runs']:
        md += f"| `{run['run_id'][:8]}` | {run['provider']} | {run['status']} | {run['inserted']}/{run['fetched']} |\n"
    
    return md

def take_screenshot(url, output_path):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Use the existing chromium instance if possible, or hope headless shell works now
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as e:
                print(f"Failed to launch chromium: {e}")
                # Try to find existing executable
                for path in Path("/home/l4nd0/.cache/ms-playwright/").glob("chromium-*/chrome-linux/chrome"):
                    try:
                        browser = p.chromium.launch(executable_path=str(path), headless=True)
                        break
                    except Exception:
                        continue
                else:
                    raise e

            page = browser.new_page(viewport={'width': 1200, 'height': 900})
            page.goto(url)
            # Wait for the specific job list to appear or just wait a bit
            page.wait_for_timeout(5000)
            
            # If we want the job status specifically, we can clip
            # page.screenshot(path=output_path, clip={'x': 0, 'y': 0, 'width': 1200, 'height': 900})
            page.screenshot(path=output_path)
            browser.close()
            return True
    except Exception as e:
        print(f"Screenshot failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DEFAULT_NEWS_ARTICLES_DB))
    parser.add_argument("--out-md", default="reports/news_progress.md")
    parser.add_argument("--out-img", default="reports/news_progress.png")
    parser.add_argument("--url", default="http://localhost:8081/operations")
    args = parser.parse_args()
    
    stats = get_stats(resolve_path(args.db))
    md = generate_markdown(stats)
    
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_md, "w") as f:
        f.write(md)
    
    print(f"Markdown report generated: {args.out_md}")
    
    if take_screenshot(args.url, args.out_img):
        print(f"Screenshot generated: {args.out_img}")
    else:
        print("Continuing without screenshot.")

if __name__ == "__main__":
    main()
