# Production image for Railway.
#
# Railway has no bind mounts, so website_tfole is baked into the image and a
# push rebuilds it. The local stack (docker-compose.yml) still bind-mounts
# ./addons for hot reload; this file is only for deployment.

FROM odoo:19

USER root

# The module. Everything Odoo needs to serve the site lives here.
COPY ./addons /mnt/extra-addons

# Runtime entrypoint. Writes the config from environment variables, applies
# module changes, then serves - see the script for why it is done at start
# rather than in a Railway pre-deploy command.
COPY ./deploy/start.sh /usr/local/bin/tfole-start
RUN chmod +x /usr/local/bin/tfole-start \
 && chown -R odoo:odoo /mnt/extra-addons

USER odoo

# The odoo image's entrypoint execs an unrecognised command as-is, so this
# runs our script rather than odoo directly.
CMD ["/usr/local/bin/tfole-start"]
