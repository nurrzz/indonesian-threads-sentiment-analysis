"""Check what the current Threads access token can do before building the collector.

The script makes two read-only calls:

1. GET /me              -> confirms the token is valid and shows which account it belongs to.
2. GET /keyword_search  -> runs one small search and reports how many results come back
                           and whether any of them were posted by accounts other than yours.

With Standard Access, keyword search only returns posts owned by the authenticated user.
If every result belongs to your own account (or nothing comes back for a common keyword),
the app most likely does not have Advanced Access for threads_keyword_search yet.

Nothing is written to disk. Post text is truncated in the output.

Usage:
    export THREADS_ACCESS_TOKEN=...      # or put it in a local .env file
    python src/check_threads_access.py --keyword gaji
"""

import argparse
import os
import sys

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

API_BASE = "https://graph.threads.net/v1.0"
DEFAULT_FIELDS = "id,text,timestamp,permalink,username,media_type"


def call(endpoint, params, token):
    params = {**params, "access_token": token}
    response = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=30)
    body = response.json()
    if "error" in body:
        error = body["error"]
        print(f"[{endpoint}] HTTP {response.status_code} error")
        print(f"  type:    {error.get('type')}")
        print(f"  code:    {error.get('code')} (subcode {error.get('error_subcode')})")
        print(f"  message: {error.get('message')}")
        return None
    return body


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keyword", default="gaji")
    parser.add_argument("--search-type", choices=["TOP", "RECENT"], default="RECENT")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--fields",
        default=DEFAULT_FIELDS,
        help="Comma-separated fields to request; useful for testing which fields the endpoint accepts.",
    )
    args = parser.parse_args()

    token = os.environ.get("THREADS_ACCESS_TOKEN")
    if not token:
        sys.exit("THREADS_ACCESS_TOKEN is not set. See .env.example.")

    me = call("me", {"fields": "id,username"}, token)
    if me is None:
        sys.exit("Token check failed; fix the token before testing search.")
    print(f"Token OK. Authenticated as @{me.get('username')} (id {me.get('id')})\n")

    result = call(
        "keyword_search",
        {
            "q": args.keyword,
            "search_type": args.search_type,
            "fields": args.fields,
            "limit": args.limit,
        },
        token,
    )
    if result is None:
        sys.exit(
            "Keyword search failed. A permissions error here usually means "
            "threads_keyword_search was not added to the app or not granted when the token was generated."
        )

    posts = result.get("data", [])
    own = [p for p in posts if p.get("username") == me.get("username")]
    others = [p for p in posts if p.get("username") != me.get("username")]

    print(f"Search q={args.keyword!r} search_type={args.search_type}: {len(posts)} result(s)")
    print(f"  from your own account: {len(own)}")
    print(f"  from other accounts:   {len(others)}\n")

    for post in posts:
        text = (post.get("text") or "").replace("\n", " ")
        print(f"- {post.get('timestamp')} {post.get('media_type')} {text[:80]!r}")
        extra = {k: v for k, v in post.items() if k not in {"id", "text", "timestamp", "permalink", "username", "media_type"}}
        if extra:
            print(f"  extra fields: {extra}")

    print()
    if others:
        print("Results include other accounts' posts: the app can search public posts.")
    elif posts:
        print("Only your own posts came back: consistent with Standard Access (own posts only).")
    else:
        print(
            "No results. With Standard Access this is expected unless your own account has posted "
            "something containing the keyword. Try a keyword from one of your own posts to confirm "
            "the endpoint itself works."
        )


if __name__ == "__main__":
    main()
