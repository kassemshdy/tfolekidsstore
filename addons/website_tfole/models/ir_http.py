from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _slug(cls, value):
        """Keep the internal reference out of product URLs.

        Odoo builds a slug from ``display_name``, and ``product.template``
        prefixes that with ``[default_code]`` whenever an internal reference is
        set. A product with SKU TF-001 therefore lands on
        ``/shop/tf-001-wooden-stacking-rings-2`` instead of
        ``/shop/wooden-stacking-rings-2``.

        ``_compute_display_name`` already honours a ``display_default_code``
        context key, so the fix is to set it rather than to reimplement naming.

        This is overridden here, at the single chokepoint, rather than on
        ``product.template._compute_website_url``, because the sitemap builds
        its URLs by calling ``_slug`` directly
        (``website_sale/controllers/main.py::sitemap_products``). Patching only
        the computed field would leave the sitemap advertising the old URLs and
        every crawled link taking a redirect.

        The reference is untouched everywhere else: backend lists, sales orders
        and pickings still read ``[TF-001] Wooden Stacking Rings``.

        Old links keep working. ``_unslug`` resolves a product from the
        trailing ID and ignores the text before it, so previously shared
        ``/shop/tf-001-...`` URLs still reach the product and Odoo redirects
        them to the canonical form.
        """
        if getattr(value, '_name', None) == 'product.template':
            # name_search passes a plain (id, name) tuple, which has no _name
            # and no context to set - hence the guard above.
            value = value.with_context(display_default_code=False)
        return super()._slug(value)
