from odoo import http
from odoo.fields import Domain
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleTfole(WebsiteSale):
    """Filter the shop by recommended age.

    The age range lives in two integer fields on product.template rather than
    in a product attribute, so Odoo's own facet filtering does not know about
    it. This adds the filter at the one hook that shapes the shop's domain,
    and carries the parameters through pagination.
    """

    def _tfole_age_bounds(self):
        """Read and sanitise age_min / age_max from the query string.

        Returns (min_months, max_months) with None for "not given". Anything
        that is not a positive integer is ignored rather than raising: these
        values arrive from a URL and a visitor can type anything into it.
        """
        def as_months(key):
            raw = request.params.get(key)
            if raw in (None, ''):
                return None
            try:
                value = int(raw)
            except (TypeError, ValueError):
                return None
            return value if value >= 0 else None

        return as_months('age_min'), as_months('age_max')

    def _get_shop_domain(self, search, category, attribute_value_dict, search_in_description=True):
        """Keep the price-range slider consistent with the age filter.

        This hook does NOT drive the product listing - that goes through
        _search_with_fuzzy and product.template._search_get_detail. It feeds
        the min/max price computation, so without this the slider would span
        the whole catalogue while the grid showed a filtered subset.
        """
        domain = super()._get_shop_domain(
            search, category, attribute_value_dict, search_in_description
        )
        low, high = self._tfole_age_bounds()
        return domain & request.env['product.template']._tfole_age_domain(low, high)

    def _get_search_options(self, **kwargs):
        """Carry the age bounds into the options the product search reads."""
        options = super()._get_search_options(**kwargs)
        low, high = self._tfole_age_bounds()
        options['tfole_age_min'] = low
        options['tfole_age_max'] = high
        return options

    def _shop_get_query_url_kwargs(self, search, min_price, max_price, **kwargs):
        """Keep the age filter across pagination and sorting links."""
        result = super()._shop_get_query_url_kwargs(search, min_price, max_price, **kwargs)
        low, high = self._tfole_age_bounds()
        if low is not None:
            result['age_min'] = low
        if high is not None:
            result['age_max'] = high
        return result
