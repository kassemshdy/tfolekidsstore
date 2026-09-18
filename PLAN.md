# Tfole Store — Custom Odoo Community Build Plan

Target: a fully custom-designed, Arabic-first eCommerce storefront on self-hosted
Odoo 19 Community, developed with Claude Code and deployed to Railway.

---

## Decisions made up front

These are settled. Don't relitigate them mid-build.

| Question | Decision | Why |
|---|---|---|
| Hosting | Self-hosted Odoo **Community 19**, Docker, on **Railway** | Odoo Online forbids custom Python modules; Odoo.sh needs a paid Enterprise subscription. Originally Leaseweb — changed mid-build, see below |
| Customization vehicle | One module, `website_tfole` — **not** a `theme_*` module | Theme modules use `theme.ir.ui.view` / `theme.website.page` proxy records that get copied per website, and are mutually exclusive with other themes. For a single site you control, a plain module writing views directly is simpler to reason about and to upgrade |
| Migration from SaaS | **Fresh database**, products re-imported via CSV | Odoo Online runs Enterprise. Restoring an Enterprise dump into Community means stripping enterprise modules from the dump — more work than re-importing a young catalogue |
| Storefront rendering | Odoo's own QWeb frontend, not headless | Checkout, tax, delivery and payment callbacks are the expensive part to re-implement. Design freedom via QWeb + SCSS is enough |
| Styling | Bootstrap 5 via Odoo's SCSS variable pipeline | Fighting Bootstrap produces a fragile site; overriding its variables produces a coherent one |

---

## Decisions taken during the build

Recorded as they were made, so later phases don't reopen them.

| Phase | Question | Decision |
|---|---|---|
| 1 | Currency: USD-only vs USD + LBP pricelist | **USD only.** No LBP pricelist. USD is pinned explicitly on the company in `data/website_config.xml`, because `base.lb` carries `currency_id = LBP` and anything deriving currency from the company country would otherwise flip pricing |
| 1 | Arabic as the default website language | **Deferred to Phase 5.** The site is English-only for now: `ar_001` is not installed and English stays the default. The RTL discipline in CLAUDE.md still applies to every stylesheet written in the meantime — the point is to avoid shipping an Arabic site whose content is untranslated English |
| 1 | Product catalogue | **Placeholder catalogue** of 8 products across 5 categories, so `/shop` renders and the import pipeline is proven. Replace the CSV rows with the real export; the images in `static/img/products/` are generated placeholders |
| 8 | Hosting: Leaseweb vs Railway | **Railway.** Leaseweb is out. The tradeoff accepted: Railway routes one domain to one port for all of that domain's traffic, and multi-worker Odoo serves websockets on a separate port that cannot be path-split onto the same hostname — so production runs `workers = 0`, a single process serving every request. Fine for launch traffic; revisit if it becomes the bottleneck |

### Note for Phase 5

Odoo data CSVs support a `field@lang` column: `name` holds the English source
and `name@ar_001` the Arabic, imported as a translation rather than a second
record (`odoo/tools/translate.py::CSVDataFileReader`). That is the cheap path
for translating the catalogue — no `.po` round-trip for data records. Template
strings still go through the normal export/translate/reimport cycle.

---

## Phase 0 — Repo and local stack

**Goal:** `docker compose up` gives a working Odoo with the addon hot-reloading.

Tasks:
1. Create the repo skeleton:
   ```
   .
   ├── CLAUDE.md
   ├── PLAN.md
   ├── docker-compose.yml
   ├── Makefile
   ├── config/odoo.conf
   ├── addons/website_tfole/
   ├── data/            # CSV imports, seed data
   └── tests/           # Playwright specs
   ```
2. `docker-compose.yml` — `odoo:19` + `postgres:16`, bind-mount `./addons` to
   `/mnt/extra-addons`, bind-mount `./config`, named volume for `/var/lib/odoo`
   (the filestore — product images live here, not in Postgres).
3. Odoo command must include `--dev=xml,qweb,reload`. Without it every template
   edit needs a container restart and the loop becomes unusable.
4. `Makefile` targets: `up`, `down`, `logs`, `shell`, `upgrade` (runs
   `odoo -u website_tfole -d tfole --stop-after-init`), `psql`, `test`.
5. `.gitignore` — never commit filestore, `.env`, or database dumps.

**Done when:** you can edit a QWeb template, refresh the browser, and see it.

---

## Phase 1 — Module skeleton and base data

**Goal:** `website_tfole` installs cleanly and the shop renders unstyled.

Tasks:
1. `__manifest__.py` — depends on `['website', 'website_sale']`, declares asset
   bundles (see `CLAUDE.md` for the exact bundle names and prepend semantics).
2. Install Arabic (`ar_001`) alongside English. Set Arabic as the default
   website language.
3. Currency and pricing: decide USD-only vs USD + LBP pricelist. Lebanon's dual
   pricing reality means this needs an explicit answer before product import.
4. Product import: categories first, then products, then variants and images.
   Keep the CSVs in `data/` and version them — reimporting a clean DB has to be
   a one-command operation.
5. Configure Website settings: company info, favicon, social links, the
   Instagram handle.

**Done when:** `/shop` lists real products in Arabic with correct prices.

---

## Phase 2 — Design foundation

**Goal:** the site stops looking like stock Odoo before a single custom template
is written.

Tasks:
1. `static/src/scss/primary_variables.scss` — brand palette, font families,
   border radii, spacing scale. This file is injected into
   `web._assets_primary_variables`, which Odoo reads *before* compiling
   Bootstrap, so changing a variable here restyles the entire site including
   components you never touch.
2. Fonts: self-host the Arabic and Latin faces under `static/src/fonts/` and
   `@font-face` them. Do not hotlink Google Fonts — it costs you a round trip
   to a third party on every page and is a GDPR nuisance.
3. `static/src/scss/bootstrap_overridden.scss` for anything the variable layer
   can't express.
4. `views/layout.xml` — inherit `website.layout` to restructure header, nav and
   footer. Use XPath `position="replace"` sparingly; prefer `before`/`after`/
   `inside` so Odoo upgrades don't silently drop your changes.

**Done when:** a stock page (say `/contactus`) already looks like Tfole.

---

## Phase 3 — Shop and product page

**Goal:** the two pages that actually convert.

Tasks:
1. Product card — inherit `website_sale.products_item`. Badge for age range,
   clean price display, add-to-cart affordance.
2. Shop grid — inherit `website_sale.products`. Decide column count per
   breakpoint, filter sidebar behaviour on mobile.
3. Product detail page — inherit `website_sale.product`. Gallery, variant
   selector, delivery expectation, "what's inside the box".
4. Cart and checkout — inherit `website_sale.cart` and the checkout templates.
   Keep edits light here: this is where Odoo's JS is densest and where a
   careless `position="replace"` breaks the purchase flow.
5. Mobile first. Most of the traffic will arrive from Instagram on a phone.

**Done when:** a full purchase completes on a phone viewport without a layout
break.

---

## Phase 4 — Custom snippets

**Goal:** you can build new landing pages in the editor without calling Claude
Code again.

Tasks:
1. Build 4–6 snippets: hero, product highlight, testimonial/UGC strip,
   age-range selector, newsletter/WhatsApp CTA, FAQ accordion.
2. Each snippet needs: the template, registration in `website.snippets`, a
   thumbnail, and editable `data-oe-*` fields so content is editable in place.
3. Snippet options (colour variants, spacing) via `snippet_options` XML.

**Done when:** a new landing page can be assembled from the editor in ten
minutes.

---

## Phase 5 — Arabic and RTL

**Goal:** Arabic is the first-class experience, not a mirrored afterthought.

Tasks:
1. Audit every custom SCSS rule for physical properties. Odoo runs custom SCSS
   through an RTL transform, but logical properties
   (`margin-inline-start`, `padding-inline-end`, `inset-inline-start`) are the
   reliable path.
2. Check icons and chevrons that imply direction — those need explicit flipping.
3. Arabic numerals: decide Eastern vs Western digits and be consistent.
4. Line height and font size for Arabic typically need to run larger than the
   Latin equivalent. Set this per-language, not globally.
5. Translate all custom template strings — wrap them properly so they land in
   the `.po` files, then export, translate, reimport.

**Done when:** the Arabic site is visually correct at 320px, 768px and 1440px.

---

## Phase 6 — Payment and delivery for Lebanon

**Goal:** a customer in Lebanon can actually pay.

Tasks:
1. **Cash on delivery** is the realistic primary method. Odoo Community has no
   dedicated COD provider — configure `payment_custom` (Wire Transfer),
   rename it, and write the instructions copy.
2. Bank transfer / OMT / Whish as a second `payment_custom` instance.
3. Card processing: Stripe does not onboard Lebanese entities. If you need
   cards, the options are a regional acquirer with a custom payment provider
   module, or an offshore entity. Decide this explicitly rather than
   discovering it at launch.
4. Delivery methods and pricing by governorate. Free-shipping threshold.
5. Order confirmation emails in Arabic — the default templates are English and
   LTR.

**Done when:** a test order goes from cart to a confirmed sale order with the
right delivery charge.

---

## Phase 7 — SEO and performance

Tasks:
1. Per-page meta via Odoo's Promote tool; verify `og:` tags render for Arabic
   pages.
2. Verify the product JSON-LD Odoo emits is complete (price, availability,
   currency) — incomplete structured data is worse than none.
3. `hreflang` for the ar/en pair.
4. Image discipline: Odoo serves WebP variants, but only if the source images
   are sane. Cap upload dimensions.
5. Lighthouse pass on mobile. Odoo's default asset bundles are heavy; check
   what your snippets pull in.
6. `robots.txt`, sitemap, Search Console for both language roots.

---

## Phase 8 — Deploy to Railway

**Goal:** the storefront runs on Railway, on the custom domain, with the
filestore surviving redeploys.

Tasks:
1. **Production image.** Railway has no bind mounts, so `website_tfole` is baked
   in: a `Dockerfile` on `odoo:19` that copies `addons/` and a production
   config. Railway builds it on every push.
2. **Services.** The Odoo service plus Railway's managed Postgres. Wire the
   database through Railway's Postgres variables; keep `db_name = tfole` and
   `dbfilter = ^tfole$`.
3. **Volume mounted at `/var/lib/odoo`.** The single most important line in this
   phase. That path is the filestore; without a volume every product image
   disappears on the next redeploy while the database keeps rows pointing at
   files that no longer exist.
4. **`workers = 0`.** Railway correlates one domain to one internal port and
   that port takes all of the domain's traffic. Multi-worker Odoo serves
   websockets on a separate port (8072), and there is no path-based split on a
   single hostname, so threaded mode — where the websocket rides on the main
   port — is the only configuration where the editor's save indicator and
   notifications work. The cost is a single process serving every request.
   A volume also cannot be shared across replicas, so horizontal scaling is out
   for the same reason.
5. **Bind to Railway's port.** The start command passes `--http-port=$PORT`.
   Odoo does not read `PORT` on its own, and a mismatch shows up as
   "Application failed to respond".
6. **Run `-u website_tfole` in the start command, not a pre-deploy command.**
   Railway's pre-deploy container runs with no volume mounted. A module update
   there writes attachments into a filesystem that is then thrown away while the
   database keeps the rows referencing them — corruption that surfaces later as
   missing assets. Start command updates, then serves.
7. `proxy_mode = True` (Railway terminates TLS), `list_db = False`, and a real
   `admin_passwd` from an environment variable — never committed.
8. **Custom domain.** Railway issues the certificate. Both the `CNAME` and the
   `TXT` record are required: with only the CNAME the domain returns 404 even
   after DNS resolves.
9. **Backups.** Railway volume backups for the filestore **plus** a scheduled
   `pg_dump`. A database dump without the filestore has no images. Test a
   restore before launch.
10. **Staging.** A second Railway environment in the same project, with its own
    database and its own volume.

**Done when:** a redeploy leaves product images intact and the site serves on
the custom domain over HTTPS.

---

## Phase 9 — Tests and CI

Tasks:
1. Playwright suite covering: shop loads, product page loads, add to cart,
   full checkout with COD, language switch, RTL layout snapshot.
2. Odoo's own test runner for any Python you add
   (`--test-enable --test-tags /website_tfole`).
3. GitHub Actions: spin up the compose stack, install the module, run the
   suite on every PR.
4. Deploy = merge to `main` → Railway builds the image and redeploys → the
   start command runs `-u website_tfole` against the mounted volume.

---

## Working agreement with Claude Code

- One phase per session. Don't let it run ahead.
- Every phase ends with a commit that installs cleanly from scratch:
  `make down && make up && make upgrade` must pass.
- Any time it proposes `position="replace"` on a `website_sale` template, ask
  what breaks on the next Odoo upgrade.
- If it can't find a template, it should grep the Odoo source in the container
  (`/usr/lib/python3/dist-packages/odoo/addons/`) rather than invent an ID.
