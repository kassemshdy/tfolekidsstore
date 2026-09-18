# data/

Raw material for the catalogue: supplier sheets, exports from the old Odoo
Online database, photo dumps — anything that gets *converted into* the
module's data files.

**The canonical, version-controlled catalogue does not live here.** Odoo only
loads data files listed in `__manifest__.py`, and those paths must resolve
inside the module directory, so the real files are:

| File | Contents |
|---|---|
| `addons/website_tfole/data/product.public.category.csv` | eCommerce categories |
| `addons/website_tfole/data/product.template.csv` | Products: name, SKU, price, categories, sales description |
| `addons/website_tfole/data/product_images.xml` | Product images (CSV cannot carry a binary) |
| `addons/website_tfole/data/website_config.xml` | Company and website identity |

Editing a CSV there and running `make upgrade` reimports it — that is the
one-command rebuild. `make reinit` rebuilds the whole database from scratch.

Keeping this directory is still worth it: a 3,000-row supplier export is not
something you want in the module, and the conversion step deserves to be
reproducible.
