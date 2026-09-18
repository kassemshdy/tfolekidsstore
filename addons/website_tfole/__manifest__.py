{
    'name': 'Tfole Store',
    'version': '19.0.0.1.0',
    'category': 'Website/Website',
    'summary': 'Arabic-first storefront for Tfole',
    'author': 'Tfole',
    'website': 'https://tfole.store',
    'license': 'LGPL-3',

    # PHASE 0 PLACEHOLDER.
    #
    # Odoo 19 refuses an addons directory that contains no module with both
    # __init__.py and __manifest__.py (odoo/tools/config.py::_is_addons_path),
    # so /mnt/extra-addons is skipped entirely until this file exists. This
    # manifest is the minimum that makes the bind mount valid and `make
    # upgrade` meaningful.
    #
    # Phase 1 replaces it with the real thing: depends on website_sale and
    # declares the three asset bundles documented in CLAUDE.md.
    'depends': [
        'website',
    ],

    'data': [
        'views/dev_smoke.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
