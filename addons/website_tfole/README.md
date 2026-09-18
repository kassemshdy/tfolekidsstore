# website_tfole

The single Odoo module behind the Tfole storefront. Deliberately **not** a
`theme_*` module — see CLAUDE.md for why.

```
data/     catalogue and site configuration, loaded in manifest order
static/   SCSS layers and product images
views/    QWeb templates
```

At Phase 1 this installs `website` + `website_sale`, seeds a placeholder
catalogue, and declares the three SCSS asset layers. The SCSS files are
intentionally near-empty: Phase 2 fills them with the brand.
