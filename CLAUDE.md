# CLAUDE.md — Tfole Store

Custom Arabic-first eCommerce storefront on **self-hosted Odoo 19 Community**.
Read `PLAN.md` for the phased build. This file is the ground truth for *how* to
work in this repo.

---

## Environment

- Odoo **19.0 Community** (not Enterprise, not Odoo.sh, not Odoo Online)
- Postgres 16
- Everything runs in Docker via `docker-compose.yml`
- Custom addon path: `./addons` → mounted at `/mnt/extra-addons`
- Odoo source to read (never edit): `/usr/lib/python3/dist-packages/odoo/addons/`
- Database name: `tfole`

Commands:
```bash
make up        # start stack, create the tfole database if missing
make down      # stop, keeping database + filestore
make destroy   # stop and delete database + filestore
make logs      # tail odoo logs
make upgrade   # odoo -u website_tfole -d tfole --stop-after-init
make reinit    # drop the database and rebuild it from scratch
make shell     # odoo shell -d tfole
make psql
make test      # playwright
make help      # list every target
```

Odoo runs with `--dev=xml,qweb,reload`. XML and QWeb changes apply on refresh.
Python changes reload the worker. Manifest changes and new data files need
`make upgrade`.

`make upgrade`, `make init` and `make reinit` use a throwaway
`docker compose run` container, so they never fight the running server for port
8069. The running server picks up the change through Odoo's registry signalling.

---

## Hard constraints

1. **Community only.** Never propose Studio, or any module under `odoo/enterprise`.
   If a feature seems to need Enterprise, say so and propose a Community path.
2. **One module: `website_tfole`.** Not a `theme_*` module — theme modules use
   `theme.ir.ui.view` proxy records and theme-switching semantics we explicitly
   don't want. Views are written directly.
3. **Never edit Odoo core.** Extend via inheritance only.
4. **Arabic is the primary language.** Every template, every stylesheet, every
   email must work RTL.

---

## Template inheritance

Always inherit. Always use the narrowest XPath that works.

```xml
<template id="product_card" inherit_id="website_sale.products_item">
    <xpath expr="//div[hasclass('o_wsale_product_information')]" position="before">
        <!-- ... -->
    </xpath>
</template>
```

Rules:
- Prefer `position="before" | "after" | "inside" | "attributes"`.
- `position="replace"` is a last resort. It silently drops upstream changes on
  the next Odoo upgrade. If you use it, say why in the commit message.
- Never guess a template ID. Grep the container:
  `docker compose exec odoo grep -rn 'products_item' /usr/lib/python3/dist-packages/odoo/addons/website_sale/views/`
- Checkout templates (`website_sale.cart`, `.checkout`, `.payment`) are dense
  with JS hooks. Edit them conservatively and retest the full purchase flow.
- XML comments cannot contain a double hyphen. Writing `--dev` inside one is an
  `XMLSyntaxError` that fails the whole module install.

---

## SCSS and assets

Three layers, in this order:

| File | Bundle | Purpose |
|---|---|---|
| `static/src/scss/primary_variables.scss` | `web._assets_primary_variables` | Brand colours, fonts, radii, spacing. Loaded before Bootstrap compiles — changing a variable here restyles the whole site |
| `static/src/scss/bootstrap_overridden.scss` | `web._assets_frontend_helpers` (**prepend**) | Bootstrap internals the variable layer can't reach |
| `static/src/scss/theme.scss` | `web.assets_frontend` | Our own component styles |

In `__manifest__.py`:
```python
'assets': {
    'web._assets_primary_variables': [
        'website_tfole/static/src/scss/primary_variables.scss',
    ],
    'web._assets_frontend_helpers': [
        ('prepend', 'website_tfole/static/src/scss/bootstrap_overridden.scss'),
    ],
    'web.assets_frontend': [
        'website_tfole/static/src/scss/theme.scss',
        'website_tfole/static/src/js/*.js',
    ],
},
```

Style rules:
- **Logical properties only** in custom SCSS: `margin-inline-start`, not
  `margin-left`. `inset-inline-end`, not `right`. This is what makes RTL work.
- Set a variable before writing a rule. If you're writing `color: #E8572A` in
  `theme.scss`, it belongs in `primary_variables.scss` instead.
- Don't add a CSS framework. Bootstrap 5 ships with Odoo.
- Self-hosted fonts under `static/src/fonts/`. No external font CDNs.
- Mobile first — most traffic arrives from Instagram on a phone.

---

## Snippets

A snippet needs four things or it won't appear in the editor:
1. The template in `views/snippets/`
2. Registration in an inherit of `website.snippets`
3. A thumbnail image
4. `data-oe-*` attributes on editable content so it's editable in place

Options (colour variants, spacing) go in a `snippet_options` inherit.

---

## Data and translations

- Seed data and product CSVs live in `data/`, version-controlled. Reimporting a
  clean database must be one command.
- Wrap user-facing strings for translation. After adding strings, export the
  `.po`, translate, reimport — don't hardcode Arabic in templates that also
  serve English.
- Arabic typically needs larger font-size and line-height than Latin. Handle it
  per-language, not globally.

---

## Definition of done for any change

```bash
make down && make up && make upgrade   # installs clean from scratch
make test                              # playwright passes
```

Note that `make down` keeps the database. For a genuine from-scratch check use
`make destroy && make up && make upgrade`.

Plus: checked at 320px, 768px and 1440px, in **both** `ar` and `en`.

---

## Working style

- One `PLAN.md` phase per session. Don't run ahead into the next phase.
- Small commits. Each one should leave the module installable.
- When something is ambiguous — currency strategy, payment provider, whether a
  feature is Enterprise-only — stop and ask rather than picking for me.
- Don't add dependencies to `__manifest__.py` without flagging it.
