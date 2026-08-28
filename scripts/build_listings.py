#!/usr/bin/env python3
"""
Rewrite the card grids on the listing pages from the same JSON that drives
the detail pages, so a listing can never advertise a trip that has no page.

    python3 scripts/build_listings.py            # apply
    python3 scripts/build_listings.py --check    # fail if stale

Pages touched
    tours.html          grid of every tour            (data/tours.json)
    destinations.html   grid + region filter buttons  (data/destinations.json)
    trekking.html       grid + difficulty filters     (tours marked is_trek)
    activities.html     grid linking to booking.html  (data/activities.json)

Only the card container (and, where present, the filter button row) is
replaced. The rest of each page - banners, facts, FAQs, testimonials - is
left exactly as it is.

MixItUp note: the filter buttons' data-filter values and the `mix` classes on
the cards are generated together from one list. That pairing is what makes
the filters work; editing one by hand without the other silently breaks them.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

IND = " " * 20  # indentation the template uses for card blocks


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def load(name: str) -> dict:
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Locating the container to replace
# --------------------------------------------------------------------------

def container_span(src: str, cls: str, occurrence: int = 0) -> tuple[int, int]:
    """Return (inner_start, inner_end) for the nth element carrying class `cls`.

    The tag name is taken from the match, so this works for the card grids
    (<div class="filter-list ...">) and the filter rows (<ul class="filter-tabs ...">)
    alike.
    """
    starts = list(re.finditer(rf'<([a-z]+) class="{re.escape(cls)}[^"]*"[^>]*>', src))
    if not starts:
        raise KeyError(f'container "{cls}" not found')
    m = starts[occurrence]
    tag = m.group(1)
    depth = 0
    for t in re.finditer(rf"<{tag}\b[^>]*>|</{tag}>", src[m.start():]):
        if t.group().startswith("</"):
            depth -= 1
            if depth == 0:
                return m.end(), m.start() + t.start()
        else:
            depth += 1
    raise ValueError(f'unbalanced container "{cls}"')


def replace_inner(src: str, cls: str, new_inner: str, occurrence: int = 0) -> str:
    a, b = container_span(src, cls, occurrence)
    return src[:a] + "\n" + new_inner + "\n" + " " * 16 + src[b:]


# --------------------------------------------------------------------------
# Card builders
# --------------------------------------------------------------------------

def tour_card(t: dict, extra_classes: str = "col-xl-4 col-lg-6 col-md-6 col-sm-12") -> str:
    href = f"tour-{t['slug']}.html"
    return f"""{IND}<!--Block-->
{IND}<div class="trek-block-one style-two {extra_classes}">
{IND}    <div class="inner-box">
{IND}        <div class="image-box">
{IND}            <div class="image"><a href="{href}"><img src="{esc(t['image'])}" alt="{esc(t['name'])}" title="{esc(t['name'])}"></a></div>
{IND}            <div class="price"><span>{esc(t['price'])}</span></div>
{IND}            <div class="info">
{IND}                <span class="i-block"><i class="icon far fa-clock"></i> {esc(t['duration'])}</span> &ensp; | &ensp; <span class="i-block">{esc(t['difficulty'])}</span>
{IND}            </div>
{IND}        </div>
{IND}        <div class="lower-content">
{IND}            <h4><a href="{href}">{esc(t['name'])}</a></h4>
{IND}            <div class="text">{esc(t['summary'])}</div>
{IND}        </div>
{IND}        <div class="bottom-box clearfix">
{IND}            <div class="more-link"><a href="{href}" class="theme-btn"><span>View Details <i class="icon"><img src="images/icons/logo-icon.svg" alt=""></i></span></a></div>
{IND}        </div>
{IND}    </div>
{IND}</div>"""


def destination_card(d: dict, tour_count: int) -> str:
    href = f"destination-{d['slug']}.html"
    label = "Trip" if tour_count == 1 else "Trips"
    return f"""{IND}<!--Block-->
{IND}<div class="trend-block-one mix all {esc(d['region'])} col-xl-4 col-lg-6 col-md-6 col-sm-12">
{IND}    <div class="inner-box">
{IND}        <div class="image-box">
{IND}            <div class="image"><a href="{href}"><img src="{esc(d['image'])}" alt="{esc(d['name'])}" title="{esc(d['name'])}"></a></div>
{IND}        </div>
{IND}        <div class="count"><span>{tour_count} {label}</span></div>
{IND}        <div class="title clearfix">
{IND}            <h4><a href="{href}">{esc(d['name'])}</a></h4>
{IND}            <div class="more-link"><a href="{href}" class="theme-btn"><span class="far fa-long-arrow-right"></span></a></div>
{IND}        </div>
{IND}    </div>
{IND}</div>"""


def trek_card(t: dict, mix: str) -> str:
    return tour_card(t, f"mix all {mix} col-xl-4 col-lg-6 col-md-6 col-sm-12")


def activity_card(a: dict) -> str:
    href = f"booking.html?activity={a['slug']}"
    return f"""{IND}<!--Block-->
{IND}<div class="activity-block-one col-xl-4 col-lg-6 col-md-6 col-sm-12">
{IND}    <div class="inner-box">
{IND}        <div class="image-box">
{IND}            <div class="image"><a href="{href}"><img src="{esc(a['image'])}" alt="{esc(a['name'])}" title="{esc(a['name'])}"></a></div>
{IND}        </div>
{IND}        <div class="lower-content">
{IND}            <div class="price"><span>{esc(a['price'])}</span></div>
{IND}            <h4><a href="{href}">{esc(a['name'])}</a></h4>
{IND}            <div class="text">{esc(a['summary'])}</div>
{IND}            <ul class="bottom-box">
{IND}                <li><span class="icon far fa-clock fa-fw"></span>{esc(a['duration'])}</li>
{IND}                <li>{esc(a['location'])}</li>
{IND}            </ul>
{IND}        </div>
{IND}    </div>
{IND}</div>"""


def booking_form(tours: list[dict], activities: list[dict]) -> str:
    """The main enquiry form on booking.html.

    The trip <select> is generated so it can never drift from the trips that
    actually have pages. Option values are slugs, which is what
    js/inquiry.js matches against ?tour= / ?activity= in the URL.
    """
    def options() -> str:
        out = ['<option value="">-- choose a trip (or leave blank) --</option>']
        out.append('<optgroup label="Multi-day trips">')
        for t in tours:
            out.append(f'<option value="{esc(t["slug"])}">{esc(t["name"])} &ndash; {esc(t["duration"])}</option>')
        out.append("</optgroup>")
        out.append('<optgroup label="Day experiences">')
        for a in activities:
            out.append(f'<option value="{esc(a["slug"])}">{esc(a["name"])} &ndash; {esc(a["duration"])}</option>')
        out.append("</optgroup>")
        out.append('<option value="custom">Something custom / not sure yet</option>')
        return ("\n" + " " * 40).join(out)

    i = " " * 20
    return f"""{i}<form class="enquiry-form" novalidate>
{i}    <div class="row clearfix">
{i}        <div class="form-group col-lg-6 col-md-6 col-sm-12">
{i}            <div class="f-label">Your Name <i>*</i></div>
{i}            <div class="field-inner">
{i}                <input type="text" name="name" placeholder="Full name" required>
{i}            </div>
{i}        </div>
{i}        <div class="form-group col-lg-6 col-md-6 col-sm-12">
{i}            <div class="f-label">Phone / WhatsApp <i>*</i></div>
{i}            <div class="field-inner">
{i}                <input type="tel" name="phone" placeholder="e.g. +92 301 234 5678" required>
{i}            </div>
{i}        </div>
{i}        <div class="form-group col-lg-6 col-md-6 col-sm-12">
{i}            <div class="f-label">Email</div>
{i}            <div class="field-inner">
{i}                <input type="email" name="email" placeholder="Optional">
{i}            </div>
{i}        </div>
{i}        <div class="form-group col-lg-6 col-md-6 col-sm-12">
{i}            <div class="f-label">Which trip?</div>
{i}            <div class="field-inner">
{i}                <select name="trip">
{" " * 40}{options()}
{i}                </select>
{i}                <span class="alt-icon far fa-angle-down"></span>
{i}            </div>
{i}        </div>
{i}        <div class="form-group col-lg-6 col-md-6 col-sm-12">
{i}            <div class="f-label">Preferred start date</div>
{i}            <div class="field-inner">
{i}                <input type="text" class="datepicker" name="start_date" placeholder="DD - MM - YYYY" autocomplete="off">
{i}                <span class="alt-icon fal fa-calendar fa-fw"></span>
{i}            </div>
{i}        </div>
{i}        <div class="form-group col-lg-6 col-md-6 col-sm-12">
{i}            <div class="f-label">Group size</div>
{i}            <div class="field-inner">
{i}                <input type="number" name="group_size" value="2" min="1" max="40">
{i}            </div>
{i}        </div>
{i}        <div class="form-group col-lg-12 col-md-12 col-sm-12">
{i}            <div class="f-label">Anything we should know?</div>
{i}            <div class="field-inner">
{i}                <textarea name="message" rows="4" placeholder="Fitness level, dietary needs, dates you cannot move, questions..."></textarea>
{i}            </div>
{i}        </div>
{i}        <div class="form-group col-lg-12 col-md-12 col-sm-12">
{i}            <button type="submit" class="theme-btn btn-style-two"><span>Send on WhatsApp<i class="icon far fa-angle-right"></i></span></button>
{i}            <div class="text" style="margin-top:15px;">This opens WhatsApp with your details already filled in. Nothing is sent until you press send there.</div>
{i}        </div>
{i}    </div>
{i}</form>"""


def contact_form() -> str:
    """General contact form. Same WhatsApp handoff as the booking form, but
    without the trip picker - people land here with questions, not bookings."""
    i = " " * 20
    return f"""{i}<form class="enquiry-form" novalidate>
{i}    <div class="row clearfix">
{i}        <div class="form-group col-lg-6 col-md-6 col-sm-12">
{i}            <div class="f-label">Your Name <i>*</i></div>
{i}            <div class="field-inner">
{i}                <input type="text" name="name" placeholder="Full name" required>
{i}            </div>
{i}        </div>
{i}        <div class="form-group col-lg-6 col-md-6 col-sm-12">
{i}            <div class="f-label">Phone / WhatsApp <i>*</i></div>
{i}            <div class="field-inner">
{i}                <input type="tel" name="phone" placeholder="e.g. +92 301 234 5678" required>
{i}            </div>
{i}        </div>
{i}        <div class="form-group col-lg-12 col-md-12 col-sm-12">
{i}            <div class="f-label">Email</div>
{i}            <div class="field-inner">
{i}                <input type="email" name="email" placeholder="Optional">
{i}            </div>
{i}        </div>
{i}        <div class="form-group col-lg-12 col-md-12 col-sm-12">
{i}            <div class="f-label">Your message <i>*</i></div>
{i}            <div class="field-inner">
{i}                <textarea name="message" rows="5" placeholder="How can we help?" required></textarea>
{i}            </div>
{i}        </div>
{i}        <div class="form-group col-lg-12 col-md-12 col-sm-12">
{i}            <button type="submit" class="theme-btn btn-style-two"><span>Send on WhatsApp<i class="icon far fa-angle-right"></i></span></button>
{i}            <div class="text" style="margin-top:15px;">This opens WhatsApp with your message already written. Nothing is sent until you press send there.</div>
{i}        </div>
{i}    </div>
{i}</form>"""


def filter_buttons(pairs: list[tuple[str, str]], all_label: str) -> str:
    ind = " " * 20
    out = [f'{ind}<li class="filter active" data-role="button" data-filter="all">{all_label}</li>']
    for value, label in pairs:
        out.append(f'{ind}<li class="filter" data-role="button" data-filter=".{value}">{esc(label)}</li>')
    return "\n".join(out)


# --------------------------------------------------------------------------
# Difficulty -> MixItUp class, matching trekking.html's existing filter values
# --------------------------------------------------------------------------

DIFFICULTY_MIX = {
    "Easy": "easy-m",
    "Easy-Moderate": "easy-m moderate",
    "Moderate": "moderate",
    "Moderate-Difficult": "m-difficult difficult",
    "Difficult": "difficult",
}
DIFFICULTY_FILTERS = [
    ("easy-m", "Easy"),
    ("moderate", "Moderate"),
    ("m-difficult", "Challenging"),
    ("difficult", "Difficult"),
]


def build(check_only: bool) -> int:
    tours = load("tours.json")["tours"]
    dest_data = load("destinations.json")
    destinations = dest_data["destinations"]
    regions = dest_data["regions"]
    activities = load("activities.json")["activities"]

    counts: dict[str, int] = {}
    for t in tours:
        counts[t["destination"]] = counts.get(t["destination"], 0) + 1

    edits: list[tuple[str, str]] = []

    # ---- destinations.html ---------------------------------------------
    src = (ROOT / "destinations.html").read_text(encoding="utf-8")
    cards = "\n".join(destination_card(d, counts.get(d["slug"], 0)) for d in destinations)
    src = replace_inner(src, "filter-list", cards)
    src = replace_inner(
        src, "filter-tabs",
        filter_buttons([(r["slug"], r["label"]) for r in regions], "All Areas"),
    )
    edits.append(("destinations.html", src))

    # ---- trekking.html --------------------------------------------------
    treks = [t for t in tours if t["difficulty"] != "Easy"]
    src = (ROOT / "trekking.html").read_text(encoding="utf-8")
    cards = "\n".join(trek_card(t, DIFFICULTY_MIX[t["difficulty"]]) for t in treks)
    src = replace_inner(src, "filter-list", cards)
    src = replace_inner(src, "filter-tabs", filter_buttons(DIFFICULTY_FILTERS, "All Treks"))
    edits.append(("trekking.html", src))

    # ---- activities.html ------------------------------------------------
    src = (ROOT / "activities.html").read_text(encoding="utf-8")
    cards = "\n".join(activity_card(a) for a in activities)
    src = replace_inner(src, "row clearfix", cards, occurrence=_activity_grid_index(src))
    edits.append(("activities.html", src))

    # ---- tours.html -----------------------------------------------------
    src = (ROOT / "tours.html").read_text(encoding="utf-8")
    cards = "\n".join(tour_card(t) for t in tours)
    src = replace_inner(src, "tour-grid", cards)
    edits.append(("tours.html", src))

    # ---- booking.html enquiry form --------------------------------------
    src = (ROOT / "booking.html").read_text(encoding="utf-8")
    src = replace_inner(src, "booking-form", booking_form(tours, activities))
    edits.append(("booking.html", src))

    # ---- contact.html enquiry form --------------------------------------
    # Shipped with every field named "fieldname" and posting to contact.html,
    # so it silently discarded whatever anyone typed.
    src = (ROOT / "contact.html").read_text(encoding="utf-8")
    src = replace_inner(src, "contact-form", contact_form())
    edits.append(("contact.html", src))

    # ---- index.html featured carousel -----------------------------------
    # Shipped pointing at packages.html for every card; now shows six real
    # trips. No col-* classes here - Owl Carousel sizes the slides itself.
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    cards = "\n".join(tour_card(t, "") for t in tours[:6])
    src = replace_inner(src, "popular-carousel", cards)
    edits.append(("index.html", src))

    # ---- write ----------------------------------------------------------
    stale = []
    for name, content in edits:
        path = ROOT / name
        if path.read_text(encoding="utf-8") == content:
            print(f"  {name:24} ok")
            continue
        stale.append(name)
        if check_only:
            print(f"  {name:24} STALE")
        else:
            path.write_text(content, encoding="utf-8")
            print(f"  {name:24} updated")

    print(f"\n{len(edits)} listing pages, {len(stale)} {'stale' if check_only else 'changed'}.")
    return 1 if (check_only and stale) else 0


def _activity_grid_index(src: str) -> int:
    """activities.html has several `row clearfix` divs; find the one holding the cards."""
    target = src.find('class="activity-block-one')
    if target == -1:
        target = src.find("<!--Block-->")
    for i, m in enumerate(re.finditer(r'<div class="row clearfix"[^>]*>', src)):
        try:
            a, b = container_span(src, "row clearfix", i)
        except (KeyError, ValueError):
            continue
        if a <= target <= b:
            return i
    raise KeyError("activities.html: could not locate the card grid")


if __name__ == "__main__":
    raise SystemExit(build("--check" in sys.argv))
