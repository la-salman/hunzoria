#!/usr/bin/env python3
"""
Give content images real alt text; mark decorative images as decorative.

    python3 scripts/build_alt_text.py            # apply
    python3 scripts/build_alt_text.py --check    # fail if stale

The template shipped with alt="" on every single image. The fix is NOT to
put text on all of them: for purely decorative images (arrows, menu glyphs,
the background "stones", quote marks) an empty alt is the correct choice,
because it tells a screen reader to skip them. Filling those in makes the
page noisier to listen to, not more accessible.

So this splits the images in two:
  - decorative -> keep alt="", add aria-hidden="true" so they are skipped
  - content    -> a real description, from the data files where we have one

Anything not recognised is reported rather than guessed at.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Filename fragments that identify purely decorative artwork.
DECORATIVE = (
    "arrow-up", "menu-icon", "logo-icon", "stones-", "quotes-", "floated-icon",
    "zoom-icon", "video-icon", "phone-call", "location.svg", "team-icon",
    "pattern-", "bg-", "shape-", "dots", "curve", "separator", "line-",
    "why-image", "buy-", "map-icon", "loc-hover", "email-1", "duration.svg",
    "speedometer", "team-group", "hill.svg", "campings", "toilet", "kitchen-tool",
    "lights", "smoking", "wifi-signal", "share-icon", "review-icon", "heart-icon",
    "phone-1", "quote-icon", "about-icon-", "about-stone-", "about-vector-",
    "f-icon-", "hills-image", "icon-1", "icon-2", "icon-3", "icon-4", "icon-5",
    "icon-6", "newsletter-image", "signature-",
)

# Descriptions for recurring content imagery.
CONTENT = {
    "news-": "Hunzoria journal article",
    "post-thumb-": "Journal article thumbnail",
    "testi-thumb-": "Hunzoria traveller",
    "rev-thumb-": "Hunzoria traveller",
    "author-": "Article author",
    "team-": "Hunzoria guide",
    "gallery-": "Mountain scenery in Gilgit-Baltistan",
    "tour-": "Trip in Gilgit-Baltistan",
    "activity-": "Day activity in Gilgit-Baltistan",
    "f-image-": "Trekking in the Karakoram",
    "trek-": "Trekking in the Karakoram",
    "dest-": "Destination in Gilgit-Baltistan",
    "banner-": "Mountain landscape in Gilgit-Baltistan",
    "image-": "Mountain landscape in Gilgit-Baltistan",
    "404-": "Page not found illustration",
    "world-map": "Map of Hunzoria trip destinations",
    "europe-map": "Regional map",
    "asia-map": "Regional map",
    "north-america-map": "Regional map",
    "logo.svg": "Hunzoria",
    "sponsor-": "Partner logo",
    "about-thumb-": "Hunzoria guides in the mountains",
}

IMG = re.compile(r'<img\b[^>]*>')


def describe(src_path: str) -> str | None:
    name = src_path.rsplit("/", 1)[-1]
    for frag in DECORATIVE:
        if frag in name:
            return None  # decorative
    for frag, text in CONTENT.items():
        if name.startswith(frag) or frag in name:
            return text
    return ""  # unknown - reported


def fix_tag(tag: str, unknown: set) -> str:
    m = re.search(r'src="([^"]*)"', tag)
    if not m:
        return tag
    src_path = m.group(1)

    existing = re.search(r'alt="([^"]*)"', tag)
    if existing and existing.group(1).strip():
        return tag  # already described - leave it alone

    desc = describe(src_path)

    if desc is None:
        # Decorative: empty alt is correct; make it explicit to assistive tech.
        if 'alt="' not in tag:
            tag = tag.replace("<img", '<img alt=""', 1)
        if "aria-hidden" not in tag:
            tag = tag.replace("<img", '<img aria-hidden="true"', 1)
        return tag

    if desc == "":
        unknown.add(src_path)
        return tag

    if 'alt="' in tag:
        tag = re.sub(r'alt="[^"]*"', f'alt="{desc}"', tag, count=1)
    else:
        tag = tag.replace("<img", f'<img alt="{desc}"', 1)
    return tag


def main() -> int:
    check_only = "--check" in sys.argv
    unknown: set = set()
    stale = []

    for path in sorted(ROOT.glob("*.html")):
        src = path.read_text(encoding="utf-8")
        updated = IMG.sub(lambda m: fix_tag(m.group(0), unknown), src)
        if updated != src:
            stale.append(path.name)
            if not check_only:
                path.write_text(updated, encoding="utf-8")

    print(f"{'would update' if check_only else 'updated'}: {len(stale)} pages")
    if unknown:
        print("\nUnrecognised images (add a rule to CONTENT or DECORATIVE):")
        for u in sorted(unknown):
            print("  -", u)
    return 1 if (check_only and stale) else 0


if __name__ == "__main__":
    raise SystemExit(main())
