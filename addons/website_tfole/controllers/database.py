import logging

from odoo import http
from odoo.exceptions import AccessDenied
from odoo.tools import config

from odoo.addons.web.controllers.database import Database

_logger = logging.getLogger(__name__)


class TfoleDatabase(Database):
    """Take the database manager off the public host entirely.

    Odoo already refuses these operations when list_db is False, and again if
    the master password is wrong. Both gates work. But the manager page still
    renders at /web/database/manager, and every destructive route stays
    routable, which leaves the master password as the only thing between the
    internet and a database restore.

    On a single-database production host the manager is never needed, so the
    routes are closed rather than merely guarded.

    The switch is list_db itself: production sets it False and loses the
    manager, local development leaves it True and keeps it. That means no
    separate flag to forget, and `make up` behaves exactly as before.
    """

    def _tfole_db_management_blocked(self):
        return not config['list_db']

    def _tfole_refuse(self, route):
        _logger.warning(
            "Blocked database manager route %s: database management is "
            "disabled on this host.", route,
        )
        # AccessDenied rather than a 404: it is the same exception Odoo raises
        # for these routes, so nothing downstream has to learn a new shape.
        raise AccessDenied()

    def selector(self, **kw):
        if self._tfole_db_management_blocked():
            self._tfole_refuse('/web/database/selector')
        return super().selector(**kw)

    def manager(self, **kw):
        if self._tfole_db_management_blocked():
            self._tfole_refuse('/web/database/manager')
        return super().manager(**kw)

    def create(self, master_pwd, name, lang, password, **post):
        if self._tfole_db_management_blocked():
            self._tfole_refuse('/web/database/create')
        return super().create(master_pwd, name, lang, password, **post)

    def duplicate(self, master_pwd, name, new_name, neutralize_database=False):
        if self._tfole_db_management_blocked():
            self._tfole_refuse('/web/database/duplicate')
        return super().duplicate(master_pwd, name, new_name, neutralize_database)

    def drop(self, master_pwd, name):
        if self._tfole_db_management_blocked():
            self._tfole_refuse('/web/database/drop')
        return super().drop(master_pwd, name)

    def backup(self, master_pwd, name, backup_format='zip', filestore=True):
        if self._tfole_db_management_blocked():
            self._tfole_refuse('/web/database/backup')
        return super().backup(master_pwd, name, backup_format, filestore)

    def restore(self, master_pwd, backup_file, name, copy=False, neutralize_database=False):
        if self._tfole_db_management_blocked():
            self._tfole_refuse('/web/database/restore')
        return super().restore(master_pwd, backup_file, name, copy, neutralize_database)

    def change_password(self, master_pwd, master_pwd_new):
        if self._tfole_db_management_blocked():
            self._tfole_refuse('/web/database/change_password')
        return super().change_password(master_pwd, master_pwd_new)
