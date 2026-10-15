"""Collect public Threads posts for a set of keywords via the official keyword search endpoint.

Results are saved to data/raw/ (git-ignored). Run check_threads_access.py first: with Standard
Access the endpoint only returns the authenticated account's own posts.

Usage:
    python src/collect_threads.py                         # default keywords
    python src/collect_threads.py --keywords gaji phk --max-per-keyword 200
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

API_BASE = "https://graph.threads.net/v1.0"
FIELDS = "id,text,timestamp,permalink,media_type"
DEFAULT_KEYWORDS = [
    "fresh graduate",
    "fresh graduates",
    "fresh grad",
    "phk",
    "gaji",
    "karir",
    "dunia kerja",
    "work life balance",
    "kecerdasan buatan",
    "pendidikan",
]
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
CSV_COLUMNS = ["post_id", "text", "timestamp", "permalink", "media_type", "keyword", "search_type", "collected_at"]


def search_keyword(keyword, token, search_type, max_posts, page_size=100, pause=1.0):
    """Yield posts for one keyword, following pagination until max_posts or no more pages."""
    params = {
        "q": keyword,
        "search_type": search_type,
        "fields": FIELDS,
        "limit": min(page_size, max_posts),
        "access_token": token,
    }
    url = f"{API_BASE}/keyword_search"
    fetched = 0
    while url and fetched < max_posts:
        response = requests.get(url, params=params, timeout=30)
        body = response.json()
        if "error" in body:
            error = body["error"]
            raise RuntimeError(f"{keyword!r}: {error.get('code')} {error.get('message')}")
        for post in body.get("data", []):
            yield post
            fetched += 1
            if fetched >= max_posts:
                return
        # The "next" URL already carries every query parameter, including the token.
        url = body.get("paging", {}).get("next")
        params = None
        time.sleep(pause)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keywords", nargs="+", default=DEFAULT_KEYWORDS)
    parser.add_argument("--search-type", choices=["TOP", "RECENT"], default="RECENT")
    parser.add_argument("--max-per-keyword", type=int, default=250)
    args = parser.parse_args()

    token = os.environ.get("THREADS_ACCESS_TOKEN")
    if not token:
        sys.exit("THREADS_ACCESS_TOKEN is not set. See .env.example.")

    collected_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows, seen = [], set()
    for keyword in args.keywords:
        count = 0
        try:
            for post in search_keyword(keyword, token, args.search_type, args.max_per_keyword):
                # A post can match several keywords; keep the first match only.
                if post["id"] in seen:
                    continue
                seen.add(post["id"])
                rows.append(
                    {
                        "post_id": post["id"],
                        "text": post.get("text", ""),
                        "timestamp": post.get("timestamp"),
                        "permalink": post.get("permalink"),
                        "media_type": post.get("media_type"),
                        "keyword": keyword,
                        "search_type": args.search_type,
                        "collected_at": collected_at,
                    }
                )
                count += 1
        except RuntimeError as exc:
            print(f"Stopped early: {exc}")
        print(f"{keyword!r}: {count} new posts")

    if not rows:
        sys.exit("No posts collected; nothing written.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"threads_posts_{collected_at[:10]}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} posts to {out_path}")


if __name__ == "__main__":
    main()
