#!/usr/bin/env python3
"""
Push the canonical shared chrome (nav + footer + header CTA) into every page.

WHY THIS EXISTS
---------------
This is a static site with no build step and no templating, so the header and
footer are physically duplicated across every HTML file. Without this script,
changing one menu item is a 30-file hand edit and the pages drift apart -
which is exactly how the site ended up with 5 pages branded "Hunzoria" and
14 still branded "Treker".

Edit partials/nav.html or partials/footer.html, then run:

    python3 scripts/propagate.py            # apply
    python3 scripts/propagate.py --check    # verify only, non-zero exit on drift

The script is idempotent: running it twice changes nothing the second time.

WHAT IT TOUCHES (and nothing else)
----------------------------------
  1. Both copies of <ul class="navigation clearfix"> (desktop + mobile sidebar)
  2. The whole <footer> element
  3. The header .links-box  -> "Book Now" CTA
  4. Deletes the cart sidebar / cart backdrop / language / sign-in leftovers

Page body content is never modified.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Which top-level nav item gets the "current" highlight, per page.
# Pages not listed here still get the nav, just with nothing highlighted.
PAGE_NAV = {
    "index.html": "index.html",
    "destinations.html": "destinations.html",
    "tours.html": "tours.html",
    "activities.html": "activities.html",
    "trekking.html": "activities.html",
    "gallery.html": "activities.html",
    "about.html": "about.html",
    "team.html": "about.html",
    "team-member.html": "about.html",
    "faq.html": "about.html",
    "terms-conditions.html": "about.html",
    "blog.html": "blog.html",
    "blog-single.html": "blog.html",
    "contact.html": "contact.html",
    "booking.html": "contact.html",
    "thank-you.html": "contact.html",
}

# Generated detail pages (scripts/build_pages.py) highlight by prefix.
PREFIX_NAV = (
    ("tour-", "tours.html"),
    ("destination-", "destinations.html"),
)


def nav_key(page_name: str) -> str | None:
    if page_name in PAGE_NAV:
        return PAGE_NAV[page_name]
    for prefix, target in PREFIX_NAV:
        if page_name.startswith(prefix):
            return target
    return None

# Header CTA that replaces the cart / wishlist / dead-search cluster.
CTA_BLOCK = """<div class="links-box clearfix">
                            <!-- CHROME:CTA (managed by scripts/propagate.py) -->
                            <a href="booking.html" class="theme-btn btn-style-one"><span>Book Now</span></a>
                        </div>"""

# The mobile hidden-bar sidebar has its own links-box, which shipped with
# Login / Sign Up buttons pointing at the deleted auth pages.
SIDEBAR_CTA_BLOCK = """<div class="links-box clearfix">
                <!-- CHROME:CTA (managed by scripts/propagate.py) -->
                <div class="clearfix">
                    <div class="link"><a href="booking.html" class="theme-btn btn-style-one"><span>Book Now<i class="icon far fa-angle-right"></i></span></a></div>
                    <div class="link"><a href="contact.html" class="theme-btn btn-style-two"><span>Contact Us<i class="icon far fa-angle-right"></i></span></a></div>
                </div>
            </div>"""


# Floating WhatsApp button, added to every page before </body>.
# The href here is a no-JS fallback; js/inquiry.js rewrites it from its own
# WHATSAPP_NUMBER constant so the number is only maintained in one place.
WHATSAPP_FLOAT = """
<!-- CHROME:WHATSAPP (managed by scripts/propagate.py) -->
<a href="https://wa.me/923000000000" data-wa-float class="whatsapp-float" target="_blank" rel="noopener" aria-label="Chat with Hunzoria on WhatsApp">
    <i class="fab fa-whatsapp"></i>
</a>"""


def find_element(src: str, start_idx: int, tag: str) -> int:
    """Return the index just past the element opened at start_idx, honouring nesting."""
    depth = 0
    pattern = re.compile(rf"<{tag}\b[^>]*?(/?)>|</{tag}>", re.IGNORECASE)
    for m in pattern.finditer(src, start_idx):
        if m.group(0).startswith("</"):
            depth -= 1
            if depth == 0:
                return m.end()
        elif m.group(1) != "/":  # ignore self-closing
            depth += 1
    raise ValueError(f"unbalanced <{tag}> from offset {start_idx}")


def load_partial(name: str) -> str:
    """Read a partial, stripping the leading explanatory HTML comment."""
    text = (ROOT / "partials" / name).read_text(encoding="utf-8")
    return re.sub(r"^\s*<!--.*?-->\s*", "", text, count=1, flags=re.DOTALL).strip()


def build_nav(nav_items: str, current: str | None, indent: str) -> str:
    """Indent the canonical nav and mark the active top-level item."""
    if current:
        # Match only top-level <li> items (those at column 0 of the partial).
        def mark(m: re.Match) -> str:
            attrs, href = m.group(1), m.group(2)
            if href != current:
                return m.group(0)
            if 'class="' in attrs:
                attrs = attrs.replace('class="', 'class="current ', 1)
            else:
                attrs = ' class="current"' + attrs
            return f"<li{attrs}><a href=\"{href}\""

        nav_items = re.sub(
            r'^<li([^>]*)><a href="([^"]+)"',
            mark,
            nav_items,
            flags=re.MULTILINE,
        )
    body = "\n".join(indent + line if line.strip() else line
                     for line in nav_items.splitlines())
    return f'<ul class="navigation clearfix">\n{body}\n{indent[:-4]}</ul>'


def validate_partials(nav_items: str, footer: str) -> list[str]:
    """Every internal href in the chrome must resolve to a real file."""
    problems = []
    for source, label in ((nav_items, "nav.html"), (footer, "footer.html")):
        for href in re.findall(r'href="([^"#:]+\.html)"', source):
            if not (ROOT / href).is_file():
                problems.append(f"{label}: links to missing page '{href}'")
        if 'href="#"' in source:
            problems.append(f"{label}: contains a dead href=\"#\"")
    return problems


def render(src: str, page_name: str, nav_items: str, footer: str) -> str:
    """Return `src` with the canonical chrome applied. Pure - writes nothing."""
    current = nav_key(page_name)

    # 1. Both navigation menus (desktop + mobile sidebar).
    # Collect every occurrence first, then rewrite back-to-front so that
    # earlier offsets stay valid as we splice.
    spans = []
    for m in re.finditer(r'(?m)^([ \t]*)<ul class="navigation clearfix">', src):
        spans.append((m.start(1), find_element(src, m.start(), "ul"), m.group(1)))
    for start, end, lead in reversed(spans):
        src = src[:start] + lead + build_nav(nav_items, current, lead + "    ") + src[end:]

    # 2. Footer.
    fi = src.find("<footer")
    if fi != -1:
        fj = find_element(src, fi, "footer")
        src = src[:fi] + footer + src[fj:]

    # 3. links-box -> Book Now CTA. The first is the desktop header; any
    #    further ones belong to the mobile hidden-bar sidebar.
    boxes = [m.start() for m in re.finditer(r'<div class="links-box clearfix">', src)]
    for idx, start in reversed(list(enumerate(boxes))):
        end = find_element(src, start, "div")
        src = src[:start] + (CTA_BLOCK if idx == 0 else SIDEBAR_CTA_BLOCK) + src[end:]

    # 4. Remove shop/auth/search leftovers. The search box has no button to
    #    open it any more, and site search cannot work without a backend or a
    #    client-side index, so the markup goes too.
    for marker, tag in (
        ('<div class="cart-sidebar">', "div"),
        ('<div class="cart-backdrop"></div>', None),
        ('<div class="lang-box">', "div"),
        ('<div class="login">', "div"),
        ('<div class="search-box">', "div"),
        ('<div class="search-backdrop"></div>', None),
    ):
        while True:
            k = src.find(marker)
            if k == -1:
                break
            end = k + len(marker) if tag is None else find_element(src, k, tag)
            src = src[:k] + src[end:]

    # Drop the now-meaningless comments the removed blocks left behind.
    for stale in ("<!--Cart Sidebar-->", "<!-- Cart Sidebar -->"):
        src = src.replace(stale, "")

    # 4a. Logo still carried the template's brand in title/alt attributes.
    src = re.sub(
        r'<a href="index\.html" title="Treker"><img src="images/logo\.svg" alt="[^"]*" title="Treker"></a>',
        '<a href="index.html" title="Hunzoria"><img src="images/logo.svg" alt="Hunzoria" title="Hunzoria"></a>',
        src,
    )

    # 4b. Header-top contact strip still carried the template's details
    #     (INFO@TREKER.COM and a made-up phone number).
    src = re.sub(
        r'<ul class="info clearfix">.*?</ul>',
        '<ul class="info clearfix">\n'
        '                            <li><i class="icon fa fa-envelope"></i> '
        '<a href="mailto:hello@hunzoria.com">hello@hunzoria.com</a></li>\n'
        '                            <li><i class="icon fa fa-phone-circle"></i> '
        '<a href="tel:+923000000000">+92 300 000 0000</a></li>\n'
        '                        </ul>',
        src,
        count=1,
        flags=re.DOTALL,
    )

    # 5. Site-specific stylesheet, loaded last so it overrides the vendor CSS.
    if "css/hunzoria.css" not in src and 'href="css/responsive.css"' in src:
        src = src.replace(
            '<link href="css/responsive.css" rel="stylesheet">',
            '<link href="css/responsive.css" rel="stylesheet">\n<link href="css/hunzoria.css" rel="stylesheet">',
            1,
        )

    # 6. Enquiry handling: js/inquiry.js plus the floating WhatsApp button.
    if "js/inquiry.js" not in src and "js/custom-script.js" in src:
        src = src.replace(
            '<script src="js/custom-script.js"></script>',
            '<script src="js/custom-script.js"></script>\n<script src="js/inquiry.js"></script>',
            1,
        )
    if "data-wa-float" not in src and "</body>" in src:
        src = src.replace("</body>", WHATSAPP_FLOAT + "\n</body>", 1)

    # Tidy the blank lines those removals leave behind. Repeat to a fixed
    # point, otherwise a second run of this script would keep finding more
    # to collapse and --check would report phantom drift forever.
    while True:
        collapsed = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", src)
        if collapsed == src:
            break
        src = collapsed
    return src


def main() -> int:
    check_only = "--check" in sys.argv
    nav_items = load_partial("nav.html")
    footer = load_partial("footer.html")

    problems = validate_partials(nav_items, footer)
    if problems:
        print("Refusing to run - the chrome partials are broken:")
        for p in problems:
            print("  -", p)
        return 1

    pages = sorted(ROOT.glob("*.html"))
    changed = []
    for page in pages:
        before = page.read_text(encoding="utf-8")
        if '<ul class="navigation clearfix">' not in before:
            print(f"  {page.name:26} skipped (no chrome)")
            continue

        after = render(before, page.name, nav_items, footer)
        if after == before:
            status = "ok"
        else:
            changed.append(page.name)
            status = "would change" if check_only else "updated"
            if not check_only:
                page.write_text(after, encoding="utf-8")
        print(f"  {page.name:26} {status}")

    verb = "would be updated" if check_only else "updated"
    print(f"\n{len(changed)} of {len(pages)} pages {verb}.")
    if check_only and changed:
        print("Drift detected. Run without --check to fix.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
