#!/usr/bin/env python3
"""
Merge tracker exports (scripts/.tmp/posts/*.json) into content/schedule.json.

Tracker fields (status, caption, image URLs) win, except that anything already
posted locally keeps its post IDs and "posted" status.
"""
import glob
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXPORT_GLOB = os.path.join(ROOT, "scripts", ".tmp", "posts", "*.json")
SCHEDULE_PATH = os.path.join(ROOT, "content", "schedule.json")
KEEP = ("day_number", "date", "pillar", "topic", "caption",
        "publish_image_urls", "status", "testimonial_note")
POSTED = ("ig_media_id", "fb_post_id", "instagram_posted_at",
          "facebook_posted_at")

existing = {}
if os.path.exists(SCHEDULE_PATH):
    with open(SCHEDULE_PATH, encoding="utf-8") as f:
        existing = {e["id"]: e for e in json.load(f)}

schedule = []
for path in sorted(glob.glob(EXPORT_GLOB)):
    doc_id = os.path.splitext(os.path.basename(path))[0]
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    entry = {"id": doc_id, **{k: doc[k] for k in KEEP if k in doc}}
    old = existing.get(doc_id, {})
    for k in POSTED:
        if k in old:
            entry[k] = old[k]
    if old.get("status") == "posted":
        entry["status"] = "posted"
    schedule.append(entry)

with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
    json.dump(schedule, f, indent=2, ensure_ascii=False)

approved = [e["id"] for e in schedule if e.get("status") == "approved"]
print(f"synced {len(schedule)} entries; approved & queued: {approved or 'none'}")
