{
    'name': 'Tfole Store',
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Custom storefront for Tfole',
    'author': 'Tfole',
    'website': 'https://tfole.store',
    'license': 'LGPL-3',

    'depends': [
        'website',
        'website_sale',
    ],

    # Categories before products (products reference them by external ID),
    # products before images (the image records update rows the CSV created).
    'data': [
        'data/product.public.category.csv',
        'data/product.template.csv',
        'data/product_images.xml',
        'data/website_config.xml',
        'views/layout.xml',
        'views/shop.xml',
        'views/product.xml',
        'views/snippets/s_tfole_hero.xml',
        'views/snippets/s_tfole_age_finder.xml',
        'views/snippets/s_tfole_highlight.xml',
        'views/snippets/s_tfole_characters.xml',
        'views/snippets/s_tfole_ugc.xml',
        'views/snippets/s_tfole_contact_cta.xml',
        'views/snippets/s_tfole_faq.xml',
        'views/snippets/snippets.xml',
        'views/homepage.xml',
    ],

    # Three layers, loaded in this order. See CLAUDE.md for what belongs where.
    # The files are deliberately near-empty at Phase 1: this phase declares the
    # pipeline, Phase 2 fills it with the brand.
    'assets': {
        'web._assets_primary_variables': [
            'website_tfole/static/src/scss/primary_variables.scss',
        ],
        'web._assets_frontend_helpers': [
            ('prepend', 'website_tfole/static/src/scss/bootstrap_overridden.scss'),
        ],
        'web.assets_frontend': [
            'website_tfole/static/src/scss/theme.scss',
        ],
    },

    'installable': True,
    'application': False,
    'auto_install': False,
}
