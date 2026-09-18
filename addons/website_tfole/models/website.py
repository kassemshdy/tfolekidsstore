from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    tfole_delivery_note = fields.Char(
        string="Delivery note",
        translate=True,
        help="One line shown on every product page, e.g. how long delivery "
             "takes. Deliberately empty by default: delivery terms are a "
             "Phase 6 decision, and the product page must not promise "
             "something nobody has agreed to. The block is hidden while this "
             "is empty.",
    )
