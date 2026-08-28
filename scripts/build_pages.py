#!/usr/bin/env python3
"""
Generate the tour and destination detail pages from data + templates.

    python3 scripts/build_pages.py            # write pages
    python3 scripts/build_pages.py --check    # fail if anything is stale

Inputs
    data/tours.json                  one entry per tour
    data/destinations.json           one entry per destination + region list
    partials/page-shell.html         head / header / banner / footer wrapper
    partials/tour-detail.html        tour body
    partials/destination-detail.html destination body

Outputs
    tour-<slug>.html          x8
    destination-<slug>.html   x6

The generated files are committed (this is a static site with no build step
on Vercel - the HTML must exist in the repo). Never hand-edit them: run this
script instead, then `python3 scripts/propagate.py` to stamp the shared
header and footer.

Validation is deliberately strict - it refuses to write pages that would
contain a broken image path or a link to a page that does not exist,
because the whole point of this rebuild is that every click resolves.
"""

from __future__ import annotations

import html
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_propagate():
    """Import scripts/propagate.py so generated pages get the shared chrome
    stamped in the same pass. Without this, build --check would always report
    the pages as stale, because propagate.py rewrites them afterwards."""
    spec = importlib.util.spec_from_file_location(
        "propagate", Path(__file__).resolve().parent / "propagate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# A very small Mustache subset: {{key}}, {{&key}} (raw), {{#section}}...{{/section}},
# {{^section}}...{{/section}} (inverted), {{.}} for the current scalar item and
# {{../key}} to reach the enclosing context.
# --------------------------------------------------------------------------

TOKEN = re.compile(r"\{\{([#^/&]?)([\w.\/]+)\}\}")


def render(template: str, context: dict, stack: tuple[dict, ...] = ()) -> str:
    out: list[str] = []
    pos = 0
    while True:
        m = TOKEN.search(template, pos)
        if not m:
            out.append(template[pos:])
            break
        out.append(template[pos : m.start()])
        sigil, key = m.group(1), m.group(2)

        if sigil in ("#", "^"):
            body, end = _section_body(template, m.end(), key)
            value = lookup(key, context, stack)
            if sigil == "#":
                if isinstance(value, list):
                    for item in value:
                        child = item if isinstance(item, dict) else {".": item}
                        out.append(render(body, child, stack + (context,)))
                elif value:
                    ctx = value if isinstance(value, dict) else context
                    out.append(render(body, ctx, stack + (context,)))
            else:  # inverted
                if not value:
                    out.append(render(body, context, stack))
            pos = end
            continue

        value = lookup(key, context, stack)
        text = "" if value is None else str(value)
        out.append(text if sigil == "&" else html.escape(text, quote=True))
        pos = m.end()
    return "".join(out)


def _section_body(template: str, start: int, key: str) -> tuple[str, int]:
    """Return the body of {{#key}}...{{/key}} and the offset just past it."""
    depth = 1
    pos = start
    while True:
        m = TOKEN.search(template, pos)
        if not m:
            raise ValueError(f"unclosed section {{{{#{key}}}}}")
        if m.group(1) in ("#", "^") :
            depth += 1
        elif m.group(1) == "/":
            depth -= 1
            if depth == 0:
                return template[start : m.start()], m.end()
        pos = m.end()


def lookup(key: str, context: dict, stack: tuple[dict, ...]):
    if key.startswith("../"):
        rest = key[3:]
        return lookup(rest, stack[-1], stack[:-1]) if stack else None
    if key == ".":
        return context.get(".")
    return context.get(key)


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

def load_template(name: str) -> str:
    text = (ROOT / "partials" / name).read_text(encoding="utf-8")
    return re.sub(r"^\s*<!--.*?-->\s*", "", text, count=1, flags=re.DOTALL)


def tour_href(slug: str) -> str:
    return f"tour-{slug}.html"


def destination_href(slug: str) -> str:
    return f"destination-{slug}.html"


def build() -> dict[str, str]:
    tours = json.loads((ROOT / "data" / "tours.json").read_text(encoding="utf-8"))["tours"]
    dest_data = json.loads((ROOT / "data" / "destinations.json").read_text(encoding="utf-8"))
    destinations = dest_data["destinations"]
    by_slug = {d["slug"]: d for d in destinations}

    shell = load_template("page-shell.html")
    tour_tpl = load_template("tour-detail.html")
    dest_tpl = load_template("destination-detail.html")

    pages: dict[str, str] = {}

    # ---- tours ----------------------------------------------------------
    for tour in tours:
        dest = by_slug[tour["destination"]]
        related = [
            {
                "name": t["name"],
                "href": tour_href(t["slug"]),
                "image": t["image"],
                "duration": t["duration"],
            }
            for t in tours
            if t["slug"] != tour["slug"] and t["destination"] == tour["destination"]
        ][:3]

        ctx = dict(tour)
        ctx["destination_name"] = dest["name"]
        ctx["destination_href"] = destination_href(dest["slug"])
        ctx["destination_image"] = dest["image"]
        ctx["related"] = [{"items": related}] if related else []

        body = render(tour_tpl, ctx)
        page = render(
            shell,
            {
                "TITLE": f"{tour['name']} | Hunzoria",
                "NAME": tour["name"],
                "CRUMB_HREF": "tours.html",
                "CRUMB_LABEL": "Tours",
                "BANNER_IMAGE": tour["image"],
                "LOCATION": dest["name"],
                "META": f"{tour['duration']} · {tour['difficulty']}",
                "CONTENT": body,
            },
        )
        pages[tour_href(tour["slug"])] = page

    # ---- destinations ---------------------------------------------------
    for dest in destinations:
        here = [
            {
                "name": t["name"],
                "href": tour_href(t["slug"]),
                "summary": t["summary"],
                "duration": t["duration"],
                "difficulty": t["difficulty"],
                "price": t["price"],
            }
            for t in tours
            if t["destination"] == dest["slug"]
        ]
        others = [
            {"name": d["name"], "href": destination_href(d["slug"]), "image": d["image"]}
            for d in destinations
            if d["slug"] != dest["slug"]
        ][:4]

        ctx = dict(dest)
        ctx["tours"] = here
        ctx["tour_count"] = len(here)
        ctx["others"] = others

        body = render(dest_tpl, ctx)
        page = render(
            shell,
            {
                "TITLE": f"{dest['name']} | Hunzoria",
                "NAME": dest["name"],
                "CRUMB_HREF": "destinations.html",
                "CRUMB_LABEL": "Destinations",
                "BANNER_IMAGE": dest["image"],
                "LOCATION": dest["name"],
                "META": f"Best season: {dest['best_season']}",
                "CONTENT": body,
            },
        )
        pages[destination_href(dest["slug"])] = page

    # Stamp the shared header/footer so the output matches what ends up on
    # disk after propagate.py runs.
    prop = _load_propagate()
    nav_items = prop.load_partial("nav.html")
    footer = prop.load_partial("footer.html")
    return {
        name: prop.render(content, name, nav_items, footer)
        for name, content in pages.items()
    }


def validate(pages: dict[str, str]) -> list[str]:
    """No unresolved placeholders, no missing images, no links to nowhere."""
    problems: list[str] = []
    known = {p.name for p in ROOT.glob("*.html")} | set(pages)
    for name, page in pages.items():
        for leftover in set(re.findall(r"\{\{[^}]+\}\}", page)):
            problems.append(f"{name}: unresolved placeholder {leftover}")
        # A body inserted through {{CONTENT}} instead of {{&CONTENT}} arrives
        # HTML-escaped and renders as visible angle brackets. Cheap to check,
        # easy to miss by eye.
        if "&lt;div" in page or "&lt;section" in page:
            problems.append(f"{name}: body markup is HTML-escaped (use {{{{&CONTENT}}}})")
        for src in set(re.findall(r'src="((?:images|css|js|fonts)/[^"]+)"', page)):
            if not (ROOT / src).is_file():
                problems.append(f"{name}: missing image {src}")
        for url in set(re.findall(r"url\(([^)]+)\)", page)):
            u = url.strip("'\"")
            if u.startswith("images/") and not (ROOT / u).is_file():
                problems.append(f"{name}: missing background {u}")
        for href in set(re.findall(r'href="([A-Za-z0-9_.-]+\.html)"', page)):
            if href not in known:
                problems.append(f"{name}: links to missing page {href}")
        if 'href="#"' in page:
            problems.append(f"{name}: contains a dead href=\"#\"")
    return problems


def main() -> int:
    check_only = "--check" in sys.argv
    pages = build()

    problems = validate(pages)
    if problems:
        print("Build failed:")
        for p in sorted(problems):
            print("  -", p)
        return 1

    stale = []
    for name, content in sorted(pages.items()):
        path = ROOT / name
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            print(f"  {name:38} ok")
            continue
        stale.append(name)
        if check_only:
            print(f"  {name:38} STALE")
        else:
            path.write_text(content, encoding="utf-8")
            print(f"  {name:38} {'written' if current is None else 'updated'}")

    print(f"\n{len(pages)} pages, {len(stale)} {'stale' if check_only else 'changed'}.")
    if check_only and stale:
        print("Run without --check to regenerate.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
