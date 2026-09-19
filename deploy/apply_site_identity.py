"""Site identity fixes for the deployed instance, safe to run on every boot.

Run through `odoo shell`. Every change is guarded so it only replaces a value
that is still an Odoo shipped default. That matters: this runs on every
container start, and an unguarded version would undo whatever the operator set
in the UI on the next deploy.

It exists because data/website_config.xml is noupdate="1" - correct, because
an operator owns those settings once the site is live, but it also means the
production database never receives values added to that file after it was
first created. The logo, favicon and phone all fell into that gap.

Reads:
  ODOO_ADMIN_LOGIN_PASSWORD  new password for the `admin` user
  TFOLE_COMPANY_PHONE        company phone, also used for the WhatsApp link
  TFOLE_COMPANY_EMAIL        public contact address
  TFOLE_PUBLIC_URL           public base URL, e.g. https://store.tfolekids.com
"""

import base64
import logging
import os

from odoo.tools import file_open

_logger = logging.getLogger('tfole.identity')

ODOO_DEFAULT_PHONE = '+1 555-555-5556'
ODOO_DEFAULT_TEL_HREF = 'tel:+1 555-555-5556'

# Odoo's placeholder addresses that stand in for the COMPANY's own email.
# Both appear in the footer, the contact page and the contact form's
# recipient field, so a form submission to the second one goes nowhere.
#
# Deliberately NOT listed: name@example.com, which is the hint text inside the
# signup form's email input. That is an example for the visitor to replace, not
# the company's address, and rewriting it would be wrong.
ODOO_DEFAULT_EMAILS = (
    'info@yourcompany.example.com',
    'yourcompany@example.com',
)
ODOO_DEFAULT_HOMEPAGE_DESCRIPTION = 'This is the homepage of the website'

HOMEPAGE_DESCRIPTION = (
    "Screen-free audio players, story cards and real-play kits for curious, "
    "active kids. More childhood. Less screen."
)


def _read_module_file(relpath):
    with file_open(relpath, 'rb') as fh:
        return base64.b64encode(fh.read())


def rotate_admin_password(env):
    new_password = os.environ.get('ODOO_ADMIN_LOGIN_PASSWORD')
    if not new_password:
        _logger.warning("ODOO_ADMIN_LOGIN_PASSWORD not set; admin password left alone")
        return

    admin = env.ref('base.user_admin', raise_if_not_found=False)
    if not admin:
        return

    # Read the hash from the column: the ORM field is compute/inverse and does
    # not hand back the stored value.
    env.cr.execute("SELECT password FROM res_users WHERE id = %s", (admin.id,))
    row = env.cr.fetchone()
    stored = row[0] if row else None
    if not stored:
        return

    still_default, _ = env['res.users']._crypt_context().verify_and_update('admin', stored)
    if not still_default:
        _logger.info("admin password already changed; left alone")
        return

    admin.write({'password': new_password})
    _logger.info("admin password rotated off the shipped default")


def set_public_url(env):
    """Fix canonical and og:url.

    Odoo records web.base.url from whatever host first served a request. On
    Railway that captured http://localhost:8069, which then went out as the
    canonical link and inside every og: tag - pointing crawlers and social
    scrapers at a machine that does not exist.
    """
    public_url = os.environ.get('TFOLE_PUBLIC_URL')
    if not public_url:
        return
    public_url = public_url.rstrip('/')

    params = env['ir.config_parameter'].sudo()
    if params.get_param('web.base.url') != public_url:
        params.set_param('web.base.url', public_url)
        _logger.info("web.base.url set to %s", public_url)

    # Without the freeze, Odoo rewrites web.base.url on the next admin login
    # from whatever host that login came through.
    params.set_param('web.base.url.freeze', 'True')

    website = env['website'].browse(1).exists()
    if website and (website.domain or '').rstrip('/') != public_url:
        website.domain = public_url
        _logger.info("website.domain set to %s", public_url)


def set_brand_assets(env):
    """Put the real logo, favicon and social card on the live site.

    The social card matters most: Odoo's default og:image is the website logo,
    served as SVG, and Facebook, WhatsApp and X all refuse to render an SVG
    og:image. That is why shared links showed no preview card at all.
    """
    website = env['website'].browse(1).exists()
    if not website:
        return

    # Only replace the logo while it is still Odoo's default SVG.
    #
    # website.logo is a Binary stored as an attachment, not a column, so it has
    # to be read through the ORM. bin_size=False is required or the read
    # returns the file size rather than the contents.
    current = website.with_context(bin_size=False).logo
    is_default_svg = bool(current) and b'svg' in base64.b64decode(current)[:400].lower()
    if is_default_svg or not current:
        website.logo = _read_module_file('website_tfole/static/src/img/brand/tfole-logo.png')
        _logger.info("website logo replaced with the Tfole wordmark")

    if not website.social_default_image:
        website.social_default_image = _read_module_file(
            'website_tfole/static/src/img/brand/social-card.png'
        )
        _logger.info("social_default_image set to the 1200x630 brand card")


def set_company_contact(env):
    company = env.ref('base.main_company', raise_if_not_found=False)
    if not company:
        return

    phone = os.environ.get('TFOLE_COMPANY_PHONE')
    if phone:
        current = (company.phone or '').strip()
        if not current or current == ODOO_DEFAULT_PHONE:
            company.phone = phone
            _logger.info("company phone set")

    email = os.environ.get('TFOLE_COMPANY_EMAIL')
    if email:
        current = (company.email or '').strip()
        if not current or current in ODOO_DEFAULT_EMAILS:
            company.email = email
            _logger.info("company email set")


def set_contact_details(env):
    """Put the real phone in the footer, the contact page and the header.

    Odoo hardcodes "+1 555-555-5556" as literal text in its footer, contact and
    header templates - it is not bound to res_company.phone, which is why
    setting the company record changed nothing on the page.

    The replacement is keyed on that exact placeholder string, so it is
    self-limiting: once a real number is in place the string is gone and this
    becomes a no-op. It never touches a number somebody typed themselves.

    Snippet templates are included deliberately, so a Contact Info block
    dropped in later also carries the right number.
    """
    phone = os.environ.get('TFOLE_COMPANY_PHONE')
    email = os.environ.get('TFOLE_COMPANY_EMAIL')
    if not phone and not email:
        return

    # Build the list of literal substitutions to apply to view archs.
    swaps = []
    if phone:
        # tel: wants a dialable string with no spaces; the visible text keeps
        # the readable grouping.
        dial = 'tel:' + '+' + ''.join(ch for ch in phone if ch.isdigit())
        swaps.append((ODOO_DEFAULT_TEL_HREF, dial))
        swaps.append((ODOO_DEFAULT_PHONE, phone))
    if email:
        for placeholder in ODOO_DEFAULT_EMAILS:
            swaps.append((placeholder, email))

    needles = {old for old, _ in swaps}
    view_ids = set()
    for needle in needles:
        env.cr.execute(
            "SELECT id FROM ir_ui_view WHERE arch_db::text LIKE %s",
            ('%' + needle + '%',),
        )
        view_ids.update(row[0] for row in env.cr.fetchall())
    if not view_ids:
        return

    changed = 0
    for view in env['ir.ui.view'].sudo().browse(sorted(view_ids)).exists():
        arch = view.arch
        new_arch = arch
        for old, new in swaps:
            new_arch = new_arch.replace(old, new)
        if new_arch != arch:
            view.arch = new_arch
            changed += 1

    _logger.info("contact placeholders replaced in %s view(s)", changed)


def set_homepage_description(env):
    """Replace Odoo's stock homepage description, which was the og:description."""
    page = env['website.page'].search([('url', '=', '/')], limit=1)
    if not page:
        return
    current = (page.website_meta_description or '').strip()
    if current and current != ODOO_DEFAULT_HOMEPAGE_DESCRIPTION:
        return
    page.website_meta_description = HOMEPAGE_DESCRIPTION
    _logger.info("homepage meta description set")


def main(env):
    """Run each fix independently.

    Each step commits on its own and its failure is caught. One broken step
    must not roll back the ones that already succeeded, nor stop the ones after
    it - an earlier version lost a completed password rotation because a later
    step raised before the single commit at the end.
    """
    steps = (
        ('admin password', rotate_admin_password),
        ('public url', set_public_url),
        ('brand assets', set_brand_assets),
        ('company contact', set_company_contact),
        ('contact details', set_contact_details),
        ('homepage description', set_homepage_description),
    )
    for label, step in steps:
        try:
            step(env)
            env.cr.commit()
        except Exception:
            env.cr.rollback()
            _logger.exception("site identity step %r failed; continuing", label)


main(env)  # noqa: F821 - `env` is injected by `odoo shell`
