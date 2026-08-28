#!/usr/bin/env python3
"""
Inject per-page SEO metadata and generate sitemap.xml.

    python3 scripts/build_seo.py            # apply
    python3 scripts/build_seo.py --check    # fail if stale

Adds to every page, between managed markers so re-running is safe:
    meta description        (0 of 31 pages had one)
    canonical URL
    Open Graph + Twitter card tags, so a link shared into WhatsApp renders
        with a title, description and image instead of a bare URL - which
        matters more than anything else here, given how this business is
        actually marketed
    JSON-LD: TravelAgency on the core pages, TouristTrip per tour,
        TouristDestination per destination

--------------------------------------------------------------------------
BEFORE LAUNCH: set SITE_URL to the real domain. Canonicals and the sitemap
are wrong until you do, and a wrong canonical is worse than none.
--------------------------------------------------------------------------
"""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SITE_URL = "https://hunzoria.com"  # TODO(launch): real domain
SITE_NAME = "Hunzoria"
DEFAULT_IMAGE = "images/resource/tour-1.jpg"

START = "<!-- SEO:START (managed by scripts/build_seo.py) -->"
END = "<!-- SEO:END -->"

# Hand-written descriptions for the pages that are not generated from data.
DESCRIPTIONS = {
    "index.html": "Small-group tours in Hunza, Skardu and the Karakoram, run by guides from Gilgit-Baltistan. Trekking, jeep trips and day experiences, with honest pricing and no crowds.",
    "about.html": "Hunzoria is a tour operator based in Karimabad, Hunza. Local guides, small groups, and trips built around the pace of the valley rather than a checklist.",
    "team.html": "Meet the guides, drivers and operations team who run Hunzoria's trips across Hunza, Nagar, Skardu and the Karakoram.",
    "team-member.html": "Meet one of the Hunzoria guides leading trips across Gilgit-Baltistan and the Karakoram.",
    "faq.html": "Permits, altitude, best months to travel, what to pack, and how booking works. Straight answers about travelling in Gilgit-Baltistan.",
    "gallery.html": "Photographs from Hunza, Skardu, Deosai, Fairy Meadows and the Karakoram, taken on Hunzoria trips.",
    "blog.html": "Notes from the valley: season reports, route conditions, packing advice and stories from the Karakoram.",
    "blog-single.html": "What a trek in the Karakoram actually involves - altitude, distances, camp life and how to prepare for it.",
    "contact.html": "Get in touch with Hunzoria in Karimabad, Hunza Valley. WhatsApp, phone and email, answered by a person within 24 hours.",
    "booking.html": "Tell us where you want to go and when, and we will send back a draft itinerary with real prices. Nothing is booked until you say so.",
    "thank-you.html": "Thanks for your enquiry - here is what happens next.",
    "terms-conditions.html": "Booking terms, cancellation policy and conditions of travel for Hunzoria trips.",
    "tours.html": "Every Hunzoria trip: Hunza, Skardu and Deosai, Fairy Meadows, Rakaposhi base camp, Khunjerab Pass, Naltar and the K2 Baltoro trek.",
    "destinations.html": "The areas we run trips in - Hunza, Skardu, Nagar, Ghizer, Astore and Diamer - with the trips available in each.",
    "activities.html": "Day experiences across Gilgit-Baltistan: the Hussaini bridge, Attabad Lake, Naltar skiing, Hopper glacier, blossom walks and trout fishing.",
    "trekking.html": "Treks in the Karakoram graded by difficulty, from the Rakaposhi base camp walk to the full Baltoro glacier route to Concordia and K2.",
    "404.html": "That page does not exist. Browse our trips or get in touch and we will point you the right way.",
}

# Pages deliberately kept out of the sitemap.
NOINDEX = {"404.html", "thank-you.html"}


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def load(name: str) -> dict:
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def page_title(src: str) -> str:
    m = re.search(r"<title>(.*?)</title>", src, re.DOTALL)
    return m.group(1).strip() if m else SITE_NAME


def truncate(text: str, limit: int = 158) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + "..."


def json_ld(name: str, tours: list[dict], destinations: list[dict]) -> dict | None:
    org = {
        "@type": "TravelAgency",
        "name": SITE_NAME,
        "url": SITE_URL,
        "description": DESCRIPTIONS.get("index.html", ""),
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Karimabad, Hunza",
            "addressRegion": "Gilgit-Baltistan",
            "addressCountry": "PK",
        },
        "areaServed": "Gilgit-Baltistan, Pakistan",
    }

    if name in ("index.html", "about.html", "contact.html"):
        return {"@context": "https://schema.org", **org}

    if name.startswith("tour-"):
        slug = name[len("tour-"):-len(".html")]
        tour = next((t for t in tours if t["slug"] == slug), None)
        if not tour:
            return None
        return {
            "@context": "https://schema.org",
            "@type": "TouristTrip",
            "name": tour["name"],
            "description": tour["summary"],
            "url": f"{SITE_URL}/{name[:-5]}",
            "image": f"{SITE_URL}/{tour['image']}",
            "touristType": tour["difficulty"],
            "provider": org,
            "offers": {
                "@type": "Offer",
                "price": re.sub(r"[^\d]", "", tour["price"]),
                "priceCurrency": "PKR",
                "availability": "https://schema.org/InStock",
            },
            "itinerary": {
                "@type": "ItemList",
                "numberOfItems": len(tour["itinerary"]),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": n + 1,
                        "name": f"{day['day']} - {day['title']}",
                        "description": day["text"],
                    }
                    for n, day in enumerate(tour["itinerary"])
                ],
            },
        }

    if name.startswith("destination-"):
        slug = name[len("destination-"):-len(".html")]
        dest = next((d for d in destinations if d["slug"] == slug), None)
        if not dest:
            return None
        return {
            "@context": "https://schema.org",
            "@type": "TouristDestination",
            "name": dest["name"],
            "description": dest["summary"],
            "url": f"{SITE_URL}/{name[:-5]}",
            "image": f"{SITE_URL}/{dest['image']}",
            "touristType": "Adventure travel",
            "includesAttraction": [
                {"@type": "TouristAttraction", "name": h} for h in dest["highlights"]
            ],
        }
    return None


def block_for(name: str, src: str, tours: list[dict], destinations: list[dict]) -> str:
    slug = name[:-5]
    canonical = SITE_URL if name == "index.html" else f"{SITE_URL}/{slug}"

    if name.startswith("tour-"):
        tour = next((t for t in tours if t["slug"] == name[5:-5]), None)
        description = tour["summary"] if tour else ""
        image = tour["image"] if tour else DEFAULT_IMAGE
    elif name.startswith("destination-"):
        dest = next((d for d in destinations if d["slug"] == name[12:-5]), None)
        description = dest["summary"] if dest else ""
        image = dest["image"] if dest else DEFAULT_IMAGE
    else:
        description = DESCRIPTIONS.get(name, "")
        image = DEFAULT_IMAGE

    description = truncate(description)
    title = page_title(src)

    lines = [
        START,
        f'<meta name="description" content="{esc(description)}">',
        f'<link rel="canonical" href="{canonical}">',
        f'<meta property="og:type" content="{"website" if name == "index.html" else "article"}">',
        f'<meta property="og:site_name" content="{esc(SITE_NAME)}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        f'<meta property="og:url" content="{canonical}">',
        f'<meta property="og:image" content="{SITE_URL}/{image}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(description)}">',
        f'<meta name="twitter:image" content="{SITE_URL}/{image}">',
    ]

    data = json_ld(name, tours, destinations)
    if data:
        lines.append(
            '<script type="application/ld+json">\n'
            + json.dumps(data, indent=2, ensure_ascii=False)
            + "\n</script>"
        )
    lines.append(END)
    return "\n".join(lines)


def apply(src: str, block: str) -> str:
    if START in src:
        return re.sub(re.escape(START) + r".*?" + re.escape(END), block, src, flags=re.DOTALL)
    # Insert just before </head>.
    return src.replace("</head>", block + "\n</head>", 1)


def sitemap(pages: list[str]) -> str:
    today = date.today().isoformat()
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for name in sorted(pages):
        if name in NOINDEX:
            continue
        loc = SITE_URL if name == "index.html" else f"{SITE_URL}/{name[:-5]}"
        priority = "1.0" if name == "index.html" else ("0.8" if name.startswith(("tour-", "destination-")) else "0.6")
        out += ["  <url>", f"    <loc>{loc}</loc>", f"    <lastmod>{today}</lastmod>",
                f"    <priority>{priority}</priority>", "  </url>"]
    out.append("</urlset>")
    return "\n".join(out) + "\n"


def main() -> int:
    check_only = "--check" in sys.argv
    tours = load("tours.json")["tours"]
    destinations = load("destinations.json")["destinations"]

    pages = sorted(p.name for p in ROOT.glob("*.html"))
    stale = []

    for name in pages:
        path = ROOT / name
        src = path.read_text(encoding="utf-8")
        updated = apply(src, block_for(name, src, tours, destinations))
        if updated == src:
            continue
        stale.append(name)
        if not check_only:
            path.write_text(updated, encoding="utf-8")

    sm = sitemap(pages)
    sm_path = ROOT / "sitemap.xml"
    if not sm_path.exists() or sm_path.read_text(encoding="utf-8") != sm:
        stale.append("sitemap.xml")
        if not check_only:
            sm_path.write_text(sm, encoding="utf-8")

    verb = "would update" if check_only else "updated"
    print(f"{verb}: {len(stale)} of {len(pages) + 1} files")
    for s in stale:
        print("  -", s)
    if check_only and stale:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
