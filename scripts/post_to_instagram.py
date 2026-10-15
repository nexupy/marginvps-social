#!/usr/bin/env python3
"""
Publish a MarginVPS Instagram carousel post from the tracker's approved queue.

Reads credentials from .env (META_APP_ID/SECRET not needed here, only the
long-lived token + IG business account id), pulls a day's publish_image_urls
and caption from the tracker artifact's database, and posts a carousel via
the Meta Graph API.

Usage:
  python scripts/post_to_instagram.py --day day-01 --dry-run   # stage only, no publish
  python scripts/post_to_instagram.py --day day-01 --publish   # actually go live

Safety: refuses to run --publish unless the tracker doc's status is "approved".
--dry-run creates carousel item containers (not public) and stops before the
final media_publish call, so it's safe to run any time to sanity-check the
pipeline.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

GRAPH = "https://graph.facebook.com/v21.0"


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


def api_get(path, params):
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"GET {path} failed: {body}") from None


def api_post(path, params):
    url = f"{GRAPH}/{path}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"POST {path} failed: {body}") from None


def get_tracker_doc(tracker_url, collection, doc_id):
    # Shells out to nothing — the ArtifactData tool is not callable from a
    # plain script, so the caller (Claude Code) passes the doc's fields in
    # via a local JSON file instead. See --doc-file.
    raise NotImplementedError


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", required=True, help='e.g. "day-01"')
    ap.add_argument("--doc-file", required=True,
                     help="local JSON file with this day's tracker doc fields "
                          "(caption, publish_image_urls, status)")
    ap.add_argument("--env-file", default=os.path.join(os.path.dirname(__file__), "..", ".env"))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true",
                       help="create carousel item containers only, do not publish")
    mode.add_argument("--publish", action="store_true",
                       help="actually publish the post live (requires status=approved)")
    args = ap.parse_args()

    env = load_env(args.env_file)
    token = env.get("IG_LONG_LIVED_TOKEN")
    ig_id = env.get("IG_BUSINESS_ACCOUNT_ID")
    if not token or not ig_id:
        print("Missing IG_LONG_LIVED_TOKEN or IG_BUSINESS_ACCOUNT_ID in .env", file=sys.stderr)
        sys.exit(1)

    with open(args.doc_file, "r", encoding="utf-8") as f:
        doc = json.load(f)

    image_urls = doc.get("publish_image_urls") or []
    caption = doc.get("caption", "")
    status = doc.get("status", "")

    if not (2 <= len(image_urls) <= 10):
        print(f"publish_image_urls must have 2-10 entries, got {len(image_urls)}", file=sys.stderr)
        sys.exit(1)

    if args.publish and status != "approved":
        print(f"Refusing to publish: tracker status for {args.day} is '{status}', not 'approved'.",
              file=sys.stderr)
        sys.exit(1)

    print(f"[{args.day}] staging {len(image_urls)} carousel items...")
    child_ids = []
    for i, url in enumerate(image_urls, 1):
        resp = api_post(f"{ig_id}/media", {
            "image_url": url,
            "is_carousel_item": "true",
            "access_token": token,
        })
        if "id" not in resp:
            print(f"  slide {i} failed: {resp}", file=sys.stderr)
            sys.exit(1)
        child_ids.append(resp["id"])
        print(f"  slide {i}/{len(image_urls)} staged -> container {resp['id']}")
        time.sleep(1)  # be gentle on rate limits

    print("creating carousel container...")
    carousel = api_post(f"{ig_id}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
        "caption": caption,
        "access_token": token,
    })
    if "id" not in carousel:
        print(f"carousel container failed: {carousel}", file=sys.stderr)
        sys.exit(1)
    creation_id = carousel["id"]
    print(f"carousel container ready -> {creation_id}")

    if args.dry_run:
        print("\nDRY RUN complete. Nothing was published. "
              f"Creation ID {creation_id} will expire unused in ~24h.")
        return

    print("publishing live...")
    pub = api_post(f"{ig_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": token,
    })
    if "id" not in pub:
        print(f"publish failed: {pub}", file=sys.stderr)
        sys.exit(1)
    print(f"\nPUBLISHED. Instagram media ID: {pub['id']}")
    print(json.dumps({"media_id": pub["id"], "creation_id": creation_id}, indent=2))


if __name__ == "__main__":
    main()
