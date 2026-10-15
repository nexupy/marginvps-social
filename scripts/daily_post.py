#!/usr/bin/env python3
"""
Daily MarginVPS poster, meant to be run by Windows Task Scheduler.

Picks the lowest-numbered entry in content/schedule.json that is approved and
not yet posted to every platform, publishes it to Instagram (carousel) and the
Facebook Page (multi-photo), and records the result back in schedule.json.
Posts at most one entry per run.

  python scripts/daily_post.py            # post next approved entry
  python scripts/daily_post.py --dry-run  # stage only, publish nothing
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(ROOT, ".env")
SCHEDULE_PATH = os.path.join(ROOT, "content", "schedule.json")
GRAPH = "https://graph.facebook.com/v21.0"


def log(msg):
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def load_env():
    env = {}
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def call(method, path, params):
    data = urllib.parse.urlencode(params).encode()
    if method == "GET":
        req = urllib.request.Request(f"{GRAPH}/{path}?{data.decode()}")
    else:
        req = urllib.request.Request(f"{GRAPH}/{path}", data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} failed: {e.read().decode()}") from None


def wait_until_ready(container_id, token, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = call("GET", container_id, {"fields": "status_code", "access_token": token})
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {container_id} status {code}")
        time.sleep(3)
    raise RuntimeError(f"container {container_id} not ready after {timeout}s")


def post_instagram(entry, env, dry_run):
    token, ig_id = env["IG_LONG_LIVED_TOKEN"], env["IG_BUSINESS_ACCOUNT_ID"]
    children = []
    for url in entry["publish_image_urls"]:
        resp = call("POST", f"{ig_id}/media",
                    {"image_url": url, "is_carousel_item": "true", "access_token": token})
        children.append(resp["id"])
    carousel = call("POST", f"{ig_id}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": entry["caption"],
        "access_token": token,
    })
    wait_until_ready(carousel["id"], token)
    if dry_run:
        return None
    return call("POST", f"{ig_id}/media_publish",
                {"creation_id": carousel["id"], "access_token": token})["id"]


def post_facebook(entry, env, dry_run):
    token, page_id = env["FB_PAGE_ACCESS_TOKEN"], env["FB_PAGE_ID"]
    photo_ids = []
    for url in entry["publish_image_urls"]:
        resp = call("POST", f"{page_id}/photos",
                    {"url": url, "published": "false", "access_token": token})
        photo_ids.append(resp["id"])
    if dry_run:
        return None
    params = {"message": entry["caption"], "access_token": token}
    for i, pid in enumerate(photo_ids):
        params[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    return call("POST", f"{page_id}/feed", params)["id"]


def pick_entry(schedule):
    for entry in sorted(schedule, key=lambda e: e["day_number"]):
        if entry.get("status") != "approved":
            continue
        if entry.get("ig_media_id") and entry.get("fb_post_id"):
            continue
        if entry.get("testimonial_note"):
            log(f"skipping {entry['id']}: testimonial needs a real, approved customer quote")
            continue
        return entry
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(SCHEDULE_PATH, encoding="utf-8") as f:
        schedule = json.load(f)

    entry = pick_entry(schedule)
    if not entry:
        log("nothing approved and unposted; done")
        return

    env = load_env()
    log(f"posting {entry['id']}: {entry['topic']}")
    failed = False

    for platform, field, fn in (("instagram", "ig_media_id", post_instagram),
                                 ("facebook", "fb_post_id", post_facebook)):
        if entry.get(field):
            log(f"  {platform}: already posted ({entry[field]})")
            continue
        try:
            result = fn(entry, env, args.dry_run)
        except Exception as e:
            failed = True
            log(f"  {platform}: FAILED - {e}")
            continue
        if args.dry_run:
            log(f"  {platform}: dry run ok")
        else:
            entry[field] = result
            entry[f"{platform}_posted_at"] = datetime.datetime.now().isoformat(timespec="seconds")
            log(f"  {platform}: published ({result})")

    if not args.dry_run:
        if entry.get("ig_media_id") and entry.get("fb_post_id"):
            entry["status"] = "posted"
        with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
            json.dump(schedule, f, indent=2, ensure_ascii=False)

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
