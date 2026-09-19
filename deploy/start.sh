#!/bin/bash
#
# Container start for Railway.
#
# Two things here are deliberate and easy to get wrong:
#
# 1. The Odoo config is WRITTEN AT START from environment variables rather
#    than committed. admin_passwd and the database password are secrets;
#    a committed config file would put them in git history.
#
# 2. The module update runs HERE, in the start command, not in a Railway
#    pre-deploy command. Pre-deploy containers run with no volume mounted,
#    so `odoo -u` there would write attachments into a filesystem that is
#    thrown away while the database keeps the rows referencing them. That
#    corruption surfaces later as missing images and broken assets.

set -euo pipefail

# Railway mounts volumes owned by root, and the odoo image runs as uid 100.
# Without this the very first write to the filestore fails with
# "PermissionError: [Errno 13] Permission denied: '/var/lib/odoo/filestore'"
# part-way through installing `base`, and the deploy crash-loops.
#
# So the container starts as root purely to take ownership of the mount, then
# re-execs itself as odoo. Nothing below this block ever runs as root.
#
# The chown is recursive because a volume may already hold root-owned files
# from an earlier boot. That is O(number of files); for a filestore of this
# size it is not measurable, but it is worth knowing if the catalogue ever
# grows into tens of thousands of images.
if [ "$(id -u)" = "0" ]; then
    echo "[tfole] taking ownership of /var/lib/odoo"
    chown -R odoo:odoo /var/lib/odoo
    echo "[tfole] dropping to uid 100 (odoo)"
    exec setpriv --reuid=100 --regid=101 --init-groups "$0" "$@"
fi

: "${PORT:=8069}"
: "${ODOO_ADMIN_PASSWD:?ODOO_ADMIN_PASSWD must be set}"

# Railway's Postgres service exposes these through a service reference.
: "${PGHOST:?PGHOST must be set (reference the Postgres service)}"
: "${PGPORT:=5432}"
: "${PGUSER:?PGUSER must be set}"
: "${PGPASSWORD:?PGPASSWORD must be set}"
: "${PGDATABASE:?PGDATABASE must be set}"

CONF=/tmp/odoo.conf

cat > "$CONF" <<CONFEOF
[options]
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
data_dir = /var/lib/odoo

db_host = ${PGHOST}
db_port = ${PGPORT}
db_user = ${PGUSER}
db_password = ${PGPASSWORD}
db_name = ${PGDATABASE}

; Serve only this database and never show a database picker.
dbfilter = ^${PGDATABASE}\$

; The database manager is off on the public host. admin_passwd is still set
; so that nothing falls back to Odoo's default of "admin".
list_db = False
admin_passwd = ${ODOO_ADMIN_PASSWD}

; Railway terminates TLS and reaches the container over its private network,
; so Odoo must trust the forwarded headers and bind to all interfaces.
proxy_mode = True
http_interface = 0.0.0.0

; Threaded mode. Railway routes one domain to one port for all of that
; domain's traffic, and multi-worker Odoo serves websockets on a separate
; port that cannot be split onto the same hostname. workers = 0 keeps the
; websocket on the main port, which is what the editor's save indicator and
; notifications need.
workers = 0
max_cron_threads = 1

without_demo = True
log_level = info
CONFEOF

echo "[tfole] applying module state to database '${PGDATABASE}'"
# -i and -u together: on a fresh database -i creates and installs it, on an
# existing one -i is a no-op and -u applies the changes in this build.
odoo --config="$CONF" \
     --database="$PGDATABASE" \
     -i website_tfole -u website_tfole \
     --stop-after-init

echo "[tfole] starting Odoo on port ${PORT}"
exec odoo --config="$CONF" --http-port="$PORT"
