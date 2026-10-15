#!/usr/bin/env python3
"""
Publish a MarginVPS multi-photo Facebook Page post from the tracker's
approved queue.

Facebook Pages don't have an Instagram-style "carousel" object; a multi-photo
post is built by uploading each image unpublished, then creating a single
feed post that attaches all of them.

Usage:
  python scripts/post_to_facebook.py --day day-01 --doc-file <path> --dry-run
  python scripts/post_to_facebook.py --day day-01 --doc-file <path> --publish

Safety: refuses --publish unless the doc's status is "approved". --dry-run
uploads the photos as UNPUBLISHED (not visible on the Page) and stops before
creating the feed post, so it's safe to run any time.
"""
import argparse
import json
import os
import sys
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", required=True)
    ap.add_argument("--doc-file", required=True,
                     help="local JSON file with this day's tracker doc fields")
    ap.add_argument("--env-file", default=os.path.join(os.path.dirname(__file__), "..", ".env"))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--publish", action="store_true")
    args = ap.parse_args()

    env = load_env(args.env_file)
    token = env.get("FB_PAGE_ACCESS_TOKEN")
    page_id = env.get("FB_PAGE_ID")
    if not token or not page_id:
        print("Missing FB_PAGE_ACCESS_TOKEN or FB_PAGE_ID in .env", file=sys.stderr)
        sys.exit(1)

    with open(args.doc_file, "r", encoding="utf-8") as f:
        doc = json.load(f)

    image_urls = doc.get("publish_image_urls") or []
    caption = doc.get("caption", "")
    status = doc.get("status", "")

    if not image_urls:
        print("publish_image_urls is empty", file=sys.stderr)
        sys.exit(1)

    if args.publish and status != "approved":
        print(f"Refusing to publish: tracker status for {args.day} is '{status}', not 'approved'.",
              file=sys.stderr)
        sys.exit(1)

    print(f"[{args.day}] uploading {len(image_urls)} unpublished photos to the Page...")
    media_ids = []
    for i, url in enumerate(image_urls, 1):
        resp = api_post(f"{page_id}/photos", {
            "url": url,
            "published": "false",
            "access_token": token,
        })
        if "id" not in resp:
            print(f"  photo {i} failed: {resp}", file=sys.stderr)
            sys.exit(1)
        media_ids.append(resp["id"])
        print(f"  photo {i}/{len(image_urls)} uploaded -> media_fbid {resp['id']}")

    if args.dry_run:
        print("\nDRY RUN complete. Photos were uploaded UNPUBLISHED (not visible on the Page) "
              "and no feed post was created.")
        print(json.dumps({"unpublished_media_ids": media_ids}, indent=2))
        return

    print("creating feed post with attached photos...")
    attached = [{"media_fbid": mid} for mid in media_ids]
    post = api_post(f"{page_id}/feed", {
        "message": caption,
        "attached_media": json.dumps(attached),
        "access_token": token,
    })
    if "id" not in post:
        print(f"feed post failed: {post}", file=sys.stderr)
        sys.exit(1)
    print(f"\nPUBLISHED. Facebook post ID: {post['id']}")
    print(json.dumps({"post_id": post["id"]}, indent=2))


if __name__ == "__main__":
    main()
