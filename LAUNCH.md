# Launch checklist

The site is complete and deployable as a **staging** build today. Everything
below must be settled before it is made public.

---

## 1. Blockers — legal / licensing

These are not polish. Do not make the site public until they are resolved.

- [ ] **Template licence.** This is the commercial "Treker" theme by ThemeIM
      (ThemeForest). Confirm a Regular Licence was purchased for this site.
- [ ] **Replace the demo photographs.** All 162 images under `images/resource/`
      and `images/background/` are the theme's *demo* images. ThemeForest demo
      imagery is licensed for the preview only and is almost never
      redistributable — using it commercially is a licence breach.
      Real Hunza/Skardu photography will also convert far better.
      Update the `image` and `gallery` fields in `data/*.json`, then rerun the
      build (see README).
- [ ] **Font Awesome Pro.** `css/font-awesome.css` and `fonts/` ship Font
      Awesome **Pro 6.1.1**. That licence does not transfer with the template.
      Either buy a Pro licence, or switch to Font Awesome Free — note that the
      markup uses the Pro-only `fal` (Light) style in 43 places
      (`fal fa-calendar`, `fal fa-phone`, `fal fa-user`). Those three icons all
      exist in Free Solid, so a switch means changing `fal` → `fas` and then
      re-checking the 99 `far` usages against Free Regular's smaller icon set.

## 2. Blockers — real details

Every one of these is currently a clearly-marked placeholder.

- [ ] **WhatsApp number.** `js/inquiry.js`, `WHATSAPP_NUMBER` (currently
      `923000000000`). This single constant drives every enquiry form and every
      WhatsApp button on the site. Format: country code + number, digits only.
      The browser console warns while it is still the placeholder.
- [ ] **Domain.** `scripts/build_seo.py`, `SITE_URL`. Canonical tags and
      `sitemap.xml` are wrong until this is set — and a wrong canonical is worse
      than no canonical. Rerun `python3 scripts/build_seo.py` afterwards.
- [ ] **Office address, phone, email.** `partials/footer.html` and
      `contact.html` (three `TODO(launch)` markers).
- [ ] **Map pin.** `contact.html` currently points at Karimabad
      (36.3167, 74.6667). Adjust if the office is elsewhere.
- [ ] **Team.** `data/team.json` — names, roles and phone numbers are invented.
- [ ] **Trips.** `data/tours.json` — itineraries are realistic but the prices,
      durations and inclusions must be confirmed by someone who runs them.
- [ ] **Social profiles.** The footer social block is commented out in
      `partials/footer.html` rather than left as dead `#` links. Add real URLs
      and uncomment.

## 3. Going public

- [ ] Remove the staging `noindex` from all pages — delete the block between
      `<!-- STAGING:NOINDEX:START -->` and `<!-- STAGING:NOINDEX:END -->`.
- [ ] Open up `robots.txt` (it currently disallows everything; the production
      rules are commented in the file, including the `Sitemap:` line).
- [ ] Turn off Vercel Deployment Protection.
- [ ] Attach the custom domain, confirm HTTPS.
- [ ] Tighten caching: `vercel.json` currently sets `must-revalidate` on
      `/css` and `/js` so edits appear immediately while building. Once the
      site is stable, raise that.
- [ ] Add analytics (Vercel Analytics is one line, or GA4).
- [ ] Replace `images/favicon.png` with a real Hunzoria favicon.
- [ ] Submit `sitemap.xml` in Google Search Console.

## 4. Worth doing, not blocking

- [ ] **Images are 14 MB and none are WebP.** Deliberately left until the demo
      photos are replaced — converting images you are about to throw away is
      wasted effort. Convert the real photos as they go in.
- [ ] Minify `css/style.css` (229 KB) and subset `css/font-awesome.css`
      (660 KB) to the icons actually used.
- [ ] `css/custom-animate.css` references `images/background/pattern-13.png`,
      which does not exist. Harmless: the only rule using it (`.empty-animation`)
      is applied on zero pages, so the browser never requests it. Delete the
      rule if you want the CSS clean.
- [ ] `blog.html` / `blog-single.html` still carry the theme's placeholder
      article text. Real journal posts are good for SEO.
- [ ] The FAQ answers on `faq.html` are still generic template copy.

## 5. Known ceilings

Accepted trade-offs, recorded so nobody rediscovers them as surprises:

- **No booking engine.** WhatsApp is an enquiry funnel: no availability, no
  payment, no order record. Correct for launch, and it matches how trips in
  this region are actually sold — but it is a ceiling.
- **Header and footer are duplicated across 31 files.**
  `scripts/propagate.py` manages that duplication safely, but does not remove
  it. The real fix is a CMS or a build step. Revisit when the site is earning.
- **Bootstrap 4.6 is end-of-life** and the stack is jQuery-era. Fine for a
  brochure site; a constraint on anything more ambitious.
