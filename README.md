# Hunzoria

Static marketing site for a Gilgit-Baltistan tour operator. Plain HTML, CSS and
jQuery — **no build step on deploy**, no backend, no database. Vercel serves the
`.html` files exactly as they sit in this repo.

See [LAUNCH.md](LAUNCH.md) for what must happen before this goes public.

## Run it locally

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## The one rule

**Do not hand-edit the generated pages.** Content lives in `data/*.json` and
layout in `partials/`; the `.html` files are output. A hand edit is silently
overwritten the next time anyone runs the build.

Generated: `tour-*.html`, `destination-*.html`, plus the card grids, filter
buttons, enquiry forms, shared header/footer and SEO tags on every other page.

## Making a change

| To change | Edit | Then run |
|---|---|---|
| A trip, price, itinerary | `data/tours.json` | `./build.sh` |
| A destination | `data/destinations.json` | `./build.sh` |
| A day activity | `data/activities.json` | `./build.sh` |
| Guides / staff | `data/team.json` | `./build.sh` |
| Menu | `partials/nav.html` | `./build.sh` |
| Footer | `partials/footer.html` | `./build.sh` |
| Detail page layout | `partials/tour-detail.html`, `partials/destination-detail.html` | `./build.sh` |
| Page wrapper (head, banner) | `partials/page-shell.html` | `./build.sh` |
| Meta descriptions | `DESCRIPTIONS` in `scripts/build_seo.py` | `./build.sh` |
| Styling | `css/hunzoria.css` — **never** the vendor stylesheets | — |
| WhatsApp number | `WHATSAPP_NUMBER` in `js/inquiry.js` | — |

```bash
./build.sh          # regenerate everything
./build.sh --check  # verify nothing is stale; non-zero exit on drift (use in CI)
```

Order matters, and `build.sh` handles it: pages → listings → SEO → alt text →
chrome.

## Layout

```
data/          content, the source of truth
partials/      HTML templates and the shared chrome
scripts/       generators (see below)
css/hunzoria.css   all local style overrides
js/inquiry.js      WhatsApp enquiry handling
*.html         generated output, committed because Vercel does no build
```

Both `partials/` and `scripts/` are in `.vercelignore` — they never ship.

### The generators

- `build_pages.py` — tour and destination detail pages from `data/`.
- `build_listings.py` — card grids, MixItUp filter buttons, enquiry forms,
  team cards. Generates each filter button together with the `mix` classes on
  its cards, because those two drifting apart is what silently breaks
  filtering.
- `build_seo.py` — meta description, canonical, Open Graph/Twitter, JSON-LD,
  and `sitemap.xml`.
- `build_alt_text.py` — alt text on content images; `alt="" aria-hidden="true"`
  on decorative ones. Reports unrecognised images instead of guessing.
- `propagate.py` — stamps the header, nav, footer and WhatsApp button into
  every page.

Every generator is idempotent and refuses to emit a link to a page that does
not exist.

## How enquiries work

There is no server. Every form carries `class="enquiry-form"`;
`js/inquiry.js` serialises it into a pre-filled `wa.me` message, opens
WhatsApp, then shows `thank-you.html`. If the pop-up is blocked it navigates
straight to WhatsApp so the enquiry is never lost.

Cards on `activities.html` link to `booking.html?activity=<slug>`, and the
form preselects that activity on load.

## Checks

```bash
./build.sh --check                      # generated files up to date
grep -o 'href="#"' *.html | wc -l       # dead links; must be 0
```
