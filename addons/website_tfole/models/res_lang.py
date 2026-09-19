import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

ARABIC_NAME = 'العربية'


class ResLang(models.Model):
    _inherit = 'res.lang'

    @api.model
    def _tfole_install_arabic(self):
        """Activate Arabic and load the translations for installed modules.

        Called from a data file, so it runs on install AND on every module
        update. The expensive half is guarded: _update_translations re-imports
        every installed module's Arabic .po, which is slow, so it only runs
        the first time, when the language was not already active.
        """
        code = 'ar_001'
        already_active = bool(self.search([('code', '=', code)], limit=1))

        lang = self.with_context(active_test=False).search([('code', '=', code)], limit=1)
        if not lang:
            _logger.warning("language %s not found; skipping", code)
            return False

        if not already_active:
            lang.active = True
            _logger.info("activated %s, loading translations", code)
            modules = self.env['ir.module.module'].search([('state', '=', 'installed')])
            modules._update_translations([code])

        # Odoo ships the ar_001 name with a leading space and full vowel
        # diacritics. That string is what the language switcher prints, so
        # normalise it to the plain spelling a reader expects.
        if lang.name != ARABIC_NAME:
            lang.name = ARABIC_NAME
        return True
