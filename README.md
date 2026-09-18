# Tfole Store

Arabic-first eCommerce storefront on self-hosted **Odoo 19 Community**.

- `CLAUDE.md` — how to work in this repo (conventions, constraints, asset pipeline)
- `PLAN.md` — the phased build

## Quick start

```bash
cp .env.example .env     # optional; the defaults in docker-compose.yml match it
make up                  # starts Odoo + Postgres, creates the tfole database
```

Then open <http://localhost:8069>. Log in with `admin` / `admin`.

```bash
make logs                # tail the Odoo log
make upgrade             # apply manifest / data-file changes
make help                # every target
```

XML and QWeb edits under `addons/website_tfole/` apply on the next browser
refresh — Odoo runs with `--dev=xml,qweb,reload`. Manifest changes and new data
files still need `make upgrade`.

## Layout

| Path | Contents |
|---|---|
| `addons/website_tfole/` | The one custom module. Deliberately not a `theme_*` module |
| `config/odoo.conf` | Local development config. Production gets its own (Phase 8) |
| `data/` | Product CSVs and seed data, version-controlled |
| `tests/` | Playwright specs (Phase 9) |

The filestore lives in the `odoo-data` Docker volume, not in Postgres. A
database dump without it has no product images.
