#!/usr/bin/env python3
"""
Refresh MarginVPS Meta credentials in .env:
1. Exchanges whatever's in IG_LONG_LIVED_TOKEN for a real 60-day long-lived
   user token (safe to run even if it's already long-lived).
2. Confirms the Instagram Business Account ID (@marginvps) and writes it.
3. Fetches a Page access token for the "Margin VPS" Facebook Page and writes it.

Run from the project root:
  python scripts/refresh_tokens.py
"""
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error

GRAPH = "https://graph.facebook.com/v21.0"
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
PAGE_ID = "933092616551611"  # Margin VPS Page


def load_env(path):
    env = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def write_env(path, updates):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    seen = set()
    out = []
    for line in lines:
        stripped = line.strip()
        matched = False
        for k, v in updates.items():
            if stripped.startswith(k + "="):
                out.append(f"{k}={v}\n")
                seen.add(k)
                matched = True
                break
        if not matched:
            out.append(line)
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out)


def get(url_path, params):
    url = f"{GRAPH}/{url_path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(e.read().decode(), file=sys.stderr)
        raise


def main():
    env = load_env(ENV_PATH)
    app_id = env.get("META_APP_ID")
    app_secret = env.get("META_APP_SECRET")
    short_token = env.get("IG_LONG_LIVED_TOKEN")
    if not all([app_id, app_secret, short_token]):
        print("Missing META_APP_ID / META_APP_SECRET / IG_LONG_LIVED_TOKEN in .env", file=sys.stderr)
        sys.exit(1)

    print("1/3 exchanging for long-lived user token...")
    exch = get("oauth/access_token", {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token,
    })
    long_token = exch["access_token"]
    days = round(exch.get("expires_in", 0) / 86400, 1)
    print(f"    ok, valid ~{days} days")

    print("2/3 confirming Instagram Business Account...")
    ig = get(PAGE_ID, {
        "fields": "instagram_business_account{id,username}",
        "access_token": long_token,
    })
    ig_account = ig.get("instagram_business_account", {})
    print(f"    @{ig_account.get('username')} -> {ig_account.get('id')}")

    print("3/3 fetching Facebook Page access token...")
    page = get(PAGE_ID, {
        "fields": "access_token,name",
        "access_token": long_token,
    })
    print(f"    Page '{page.get('name')}' token acquired")

    write_env(ENV_PATH, {
        "IG_LONG_LIVED_TOKEN": long_token,
        "IG_BUSINESS_ACCOUNT_ID": ig_account.get("id", ""),
        "FB_PAGE_ID": PAGE_ID,
        "FB_PAGE_ACCESS_TOKEN": page.get("access_token", ""),
    })
    print("\n.env updated. All tokens refreshed.")


if __name__ == "__main__":
    main()
