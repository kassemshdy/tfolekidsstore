from odoo import api, fields, models, _
from odoo.fields import Domain


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Age range -----------------------------------------------------------
    #
    # Stored in months rather than years so the catalogue can express both
    # "6-18 months" and "3-5 years" with one pair of fields. The label picks
    # the unit; nothing downstream has to know which was meant.
    #
    # Two integers rather than a Selection because a fixed list of brackets
    # ("0-2", "3-5") stops being true the moment a product spans one, and
    # migrating a Selection later is more painful than migrating data.

    tfole_age_min_months = fields.Integer(
        string="Minimum age (months)",
        help="Lower bound of the recommended age range, in months. "
             "Leave both age fields at 0 to hide the badge.",
    )
    tfole_age_max_months = fields.Integer(
        string="Maximum age (months)",
        help="Upper bound of the recommended age range, in months. "
             "0 means open-ended and renders as a '+'.",
    )
    tfole_age_label = fields.Char(
        string="Age range",
        compute='_compute_tfole_age_label',
        help="Human-readable age range shown on the shop and product pages.",
    )

    # What's in the box ---------------------------------------------------
    tfole_box_contents = fields.Html(
        string="What's in the box",
        translate=True,
        sanitize=True,
        help="Short list of what the customer actually receives. Shown on the "
             "product page when set, hidden when empty.",
    )

    @api.depends('tfole_age_min_months', 'tfole_age_max_months')
    def _compute_tfole_age_label(self):
        for product in self:
            product.tfole_age_label = product._tfole_format_age_range()

    def _tfole_format_age_range(self):
        """Render the age range, choosing months or years by the upper bound.

        Returns False when no range is set, so templates can simply test the
        field rather than compare against an empty string.
        """
        self.ensure_one()
        low = self.tfole_age_min_months
        high = self.tfole_age_max_months

        if not low and not high:
            return False

        # Open-ended: "3+ years". Use the lower bound to pick the unit, since
        # there is no upper bound to read it from.
        if not high:
            if low < 24:
                return _("%(months)s+ months", months=low)
            return _("%(years)s+ years", years=low // 12)

        # A range that ends at or inside the first two years reads better in
        # months; past that, years. Mixed ranges round the lower bound into
        # years so the two numbers always share a unit.
        if high <= 24:
            return _("%(low)s-%(high)s months", low=low, high=high)
        return _("%(low)s-%(high)s years", low=low // 12, high=high // 12)

    # Age filtering on the shop ------------------------------------------

    @api.model
    def _tfole_age_domain(self, low, high):
        """Domain matching products whose age range overlaps [low, high].

        Overlap, not containment: a 12-36 month toy belongs in a "0-2 years"
        bracket as much as in a "2-5 years" one.

        tfole_age_max_months = 0 means open-ended ("3+ years"), so there is no
        upper bound to compare and it always satisfies the lower test.

        Products with no range set match nothing, which is deliberate: an
        unset range is unknown, not universal.
        """
        domain = Domain.TRUE
        if high is not None:
            domain &= Domain('tfole_age_min_months', '<=', high)
        if low is not None:
            domain &= (
                Domain('tfole_age_max_months', '>=', low)
                | Domain('tfole_age_max_months', '=', 0)
            )
        return domain

    def _search_get_detail(self, website, order, options):
        """Add the age filter to the domain the shop listing actually uses."""
        detail = super()._search_get_detail(website, order, options)
        low = options.get('tfole_age_min')
        high = options.get('tfole_age_max')
        if low is None and high is None:
            return detail
        detail['base_domain'] = list(detail['base_domain']) + [
            self._tfole_age_domain(low, high)
        ]
        return detail
