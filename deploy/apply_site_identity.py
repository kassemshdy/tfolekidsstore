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
import re

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

HOMEPAGE_DESCRIPTION_AR = (
    "مشغّلات صوتية بلا شاشة، بطاقات قصص وصناديق لعب حقيقي "
    "للأولاد. طفولة أكتر. شاشة أقلّ."
)

# The homepage title falls back to the view name ("Home"), which Odoo does not
# translate. website_meta_title wins over that fallback and is translatable,
# and it is also where an operator would set it in the SEO dialog.
HOMEPAGE_TITLE = "Screen-free audio stories and real play | Tfole"

HOMEPAGE_TITLE_AR = "قصص صوتية ولعب حقيقي بلا شاشة | Tfole"


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


# Odoo's stock footer copy, matched as patterns rather than literal strings.
# An exact-string match failed here once already: the stored arch wraps the
# paragraph with a newline and indentation before the <br/>, which no
# hand-written constant is going to reproduce reliably.
ODOO_DEFAULT_ABOUT_RE = re.compile(
    r"<p>\s*We are a team of passionate people.*?</p>", re.DOTALL
)

TFOLE_ABOUT_TEXT = (
    "Tfole makes screen-free audio players and real-play kits for kids. "
    "Stories to listen to, adventures to live, and a box of things to do with "
    "your hands.<br/><br/>More childhood. Less screen."
)

TFOLE_ABOUT = "<p>%s</p>" % TFOLE_ABOUT_TEXT

TFOLE_ABOUT_TEXT_AR = (
    "طفولة تصنع مشغّلات صوتية بلا شاشة وصناديق لعب حقيقي للأولاد. "
    "قصص تنسمع، مغامرات تنعاش، وصندوق أشياء تنعمل بالإيد."
    "<br/><br/>طفولة أكتر. شاشة أقلّ."
)

ARABIC_CODE = 'ar_001'

# Labels this script writes into the footer. Odoo's own strings (Home, Contact
# us, Follow us) already come translated with the core .po files.
FOOTER_TERMS_AR = {
    'Shop': 'المتجر',
    'The Player': 'المشغّل',
    'The Activity Kit': 'صندوق الأنشطة',
}

# The stock "Useful Links" list. Four of its six entries are href="#", which
# are dead links on a live site.
ODOO_DEFAULT_LINKS_RE = re.compile(
    r'<li><a href="/">Home</a></li>\s*'
    r'<li><a href="#">About us</a></li>\s*'
    r'<li><a href="#">Products</a></li>\s*'
    r'<li><a href="#">Services</a></li>\s*'
    r'<li><a href="#">Legal</a></li>',
    re.DOTALL,
)


def _category_url(env, xmlid):
    """Resolve a shop category URL, or fall back to /shop.

    Category ids differ per database, so the URL is built from the record
    rather than written down - the same mistake that 404'd the homepage
    buttons.
    """
    categ = env.ref(xmlid, raise_if_not_found=False)
    if not categ:
        return '/shop'
    return '/shop/category/' + env['ir.http']._slug(categ)


def set_footer_copy(env):
    """Replace Odoo's stock About text and dead Useful Links.

    The footer is an oe_structure whose contents live in a stored view, so
    this edits that view rather than a template. Guarded on the exact stock
    strings, so an operator's own copy is never overwritten.
    """
    view = env.ref('website.footer_custom', raise_if_not_found=False)
    if not view:
        return

    arch = view.arch
    new_arch = ODOO_DEFAULT_ABOUT_RE.sub(lambda _m: TFOLE_ABOUT, arch)

    if ODOO_DEFAULT_LINKS_RE.search(new_arch):
        links = [
            ('/', 'Home'),
            ('/shop', 'Shop'),
            (_category_url(env, 'website_tfole.categ_tfole_audio'), 'The Player'),
            (_category_url(env, 'website_tfole.categ_tfole_box'), 'The Activity Kit'),
        ]
        replacement = '\n                                '.join(
            f'<li><a href="{href}">{label}</a></li>' for href, label in links
        )
        new_arch = ODOO_DEFAULT_LINKS_RE.sub(lambda _m: replacement, new_arch)

    if new_arch != arch:
        view.arch = new_arch
        _logger.info("footer copy replaced")

    _translate_footer_terms(env, view)


def _translate_footer_terms(env, view):
    """Give the copy we just wrote an Arabic translation.

    The footer lives in a stored, editor-owned view, so its terms cannot ride
    in the module's .po - nothing there references this record. Writing the
    English arch leaves the new terms untranslated, and on an Arabic-default
    site that shows as English text in the footer.

    Odoo tracks arch_db translations per term, so this fills in only the terms
    this script introduced, and only where nobody has translated them already.
    """
    if not env['res.lang'].search_count([('code', '=', ARABIC_CODE)]):
        return

    translations, _context = view.get_field_translations('arch_db', [ARABIC_CODE])
    mapping = {}
    for row in translations:
        source = row['source']
        if row['value']:
            continue  # already translated - an operator's wording wins
        if source in FOOTER_TERMS_AR:
            mapping[source] = FOOTER_TERMS_AR[source]
        elif source == TFOLE_ABOUT_TEXT:
            mapping[source] = TFOLE_ABOUT_TEXT_AR

    if mapping:
        view.update_field_translations('arch_db', {ARABIC_CODE: mapping})
        _logger.info("footer copy translated (%d terms)", len(mapping))


def retire_default_carrier(env):
    """Unpublish Odoo's stock "Standard delivery".

    Odoo ships delivery.free_delivery_carrier published, priced at 0.00 and
    with cash on delivery disabled. On a live shop that offers customers free
    delivery nobody agreed to, and then refuses every payment method, because
    COD is gated on the chosen carrier allowing it.

    Guarded on it still looking like the stock record - stock name, zero
    price, COD off. If somebody has repurposed it as their real carrier, it is
    left alone.
    """
    carrier = env.ref('delivery.free_delivery_carrier', raise_if_not_found=False)
    if not carrier or not carrier.is_published:
        return

    looks_stock = (
        not carrier.allow_cash_on_delivery
        and not carrier.fixed_price
        and carrier.name == 'Standard delivery'
    )
    if not looks_stock:
        _logger.info("default carrier has been customised; left alone")
        return

    carrier.is_published = False
    _logger.info("unpublished Odoo's stock free delivery carrier")


def enable_arabic(env):
    """Make Arabic first-class on an already-installed database.

    data/website_config.xml handles a fresh install, but it is noupdate="1",
    so an existing production database never receives the language settings
    added to it later. Same gap the logo and phone fell into.

    Guarded: English stays the default if somebody has already chosen a
    default other than English, and the language list is only extended, never
    replaced.
    """
    arabic = env.ref('base.lang_ar', raise_if_not_found=False)
    english = env.ref('base.lang_en', raise_if_not_found=False)
    if not arabic or not arabic.active:
        return

    website = env['website'].browse(1).exists()
    if not website:
        return

    if arabic not in website.language_ids:
        website.language_ids = [(4, arabic.id)]
        _logger.info("Arabic added to the website languages")

    # Only promote Arabic while the default is still the English Odoo
    # installed with. A deliberate choice of any other default is respected.
    if english and website.default_lang_id == english:
        website.default_lang_id = arabic
        _logger.info("Arabic set as the default website language")


def set_homepage_description(env):
    """Give the homepage its own title and description, in both languages.

    website_meta_description was Odoo's stock "This is the homepage of the
    website", which was also the og:description. website_meta_title overrides
    the untranslatable view name the <title> otherwise falls back to.

    Both fields are translatable, so each language is written separately -
    writing only English would leave the Arabic site showing English metadata.
    """
    page = env['website.page'].search([('url', '=', '/')], limit=1)
    if not page:
        return

    langs = ['en_US']
    if env['res.lang'].search_count([('code', '=', ARABIC_CODE)]):
        langs.append(ARABIC_CODE)

    copy = {
        'en_US': (HOMEPAGE_TITLE, HOMEPAGE_DESCRIPTION),
        ARABIC_CODE: (HOMEPAGE_TITLE_AR, HOMEPAGE_DESCRIPTION_AR),
    }

    # Decide before writing anything. Writing the English value propagates to
    # the other languages, so a guard read after that write would always see
    # the English text and skip the Arabic.
    wanted = {}
    for lang in langs:
        localised = page.with_context(lang=lang)
        description = (localised.website_meta_description or '').strip()
        wanted[lang] = (
            # Only fill a title nobody has set; Odoo ships this field empty.
            not (localised.website_meta_title or '').strip(),
            not description or description == ODOO_DEFAULT_HOMEPAGE_DESCRIPTION,
        )

    # English first: it is the source language, and writing it overwrites the
    # other languages' values.
    for lang in langs:
        localised = page.with_context(lang=lang)
        title, description = copy[lang]
        set_title, set_description = wanted[lang]
        if set_title:
            localised.website_meta_title = title
        if set_description:
            localised.website_meta_description = description

    _logger.info("homepage metadata set (%s)", ', '.join(langs))


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
        ('footer copy', set_footer_copy),
        ('default carrier', retire_default_carrier),
        ('arabic', enable_arabic),
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
