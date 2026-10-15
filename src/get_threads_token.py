"""Get a long-lived Threads user token that includes threads_keyword_search.

The dashboard's User Token Generator only grants a fixed set of permissions, so this script
runs the standard OAuth flow with an explicit scope list instead.

Requires in .env (or the environment):
    THREADS_APP_ID        Threads app ID (Use cases > Access the Threads API > Settings)
    THREADS_APP_SECRET    Threads app secret (same page)
    THREADS_REDIRECT_URI  Must exactly match a Redirect Callback URL in the same settings page

Usage:
    python src/get_threads_token.py
    1. Open the printed URL, approve the permissions.
    2. You are sent to the redirect URI (the page may fail to load; that is fine).
       Copy the full URL from the address bar and paste it back into the terminal.
"""

import os
import sys
from urllib.parse import parse_qs, urlencode, urlparse

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

AUTHORIZE_URL = "https://threads.net/oauth/authorize"
GRAPH = "https://graph.threads.net"
SCOPES = "threads_basic,threads_keyword_search"


def check(response):
    body = response.json()
    if "error" in body or "access_token" not in body:
        sys.exit(f"Token request failed: {body}")
    return body


def main():
    try:
        app_id = os.environ["THREADS_APP_ID"]
        app_secret = os.environ["THREADS_APP_SECRET"]
        redirect_uri = os.environ["THREADS_REDIRECT_URI"]
    except KeyError as missing:
        sys.exit(f"{missing.args[0]} is not set. See .env.example.")

    params = {"client_id": app_id, "redirect_uri": redirect_uri, "scope": SCOPES, "response_type": "code"}
    print("Open this URL and approve the permissions:\n")
    print(f"{AUTHORIZE_URL}?{urlencode(params)}\n")

    redirected = input("Paste the full URL you were redirected to: ").strip()
    code = parse_qs(urlparse(redirected).query).get("code", [None])[0]
    if not code:
        sys.exit("No ?code= found in that URL.")
    code = code.removesuffix("#_")  # Threads appends #_ to the redirect

    short = check(
        requests.post(
            f"{GRAPH}/oauth/access_token",
            data={
                "client_id": app_id,
                "client_secret": app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
            },
            timeout=30,
        )
    )
    long_lived = check(
        requests.get(
            f"{GRAPH}/access_token",
            params={
                "grant_type": "th_exchange_token",
                "client_secret": app_secret,
                "access_token": short["access_token"],
            },
            timeout=30,
        )
    )

    days = long_lived.get("expires_in", 0) // 86400
    print(f"\nLong-lived token (valid ~{days} days). Store it as THREADS_ACCESS_TOKEN; do not commit it:\n")
    print(long_lived["access_token"])


if __name__ == "__main__":
    main()
