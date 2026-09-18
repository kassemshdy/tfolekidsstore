# Tfole Store — developer entry points.
#
# Everything runs in Docker; nothing here assumes a local Odoo or Postgres.
# See CLAUDE.md for how to work in this repo and PLAN.md for the build phases.

COMPOSE     ?= docker compose
DB          ?= tfole
MODULE      ?= website_tfole
ODOO_URL    ?= http://localhost:$(shell grep -E '^ODOO_PORT=' .env 2>/dev/null | cut -d= -f2 | grep . || echo 8069)

# Modules installed when the database is first created. Installing our module
# pulls in its dependencies, so a fresh database is one command.
INIT_MODULES ?= website_tfole

# One-off Odoo container: no published ports, so it never fights the running
# server for 8069.
ODOO_RUN = $(COMPOSE) run --rm --no-deps -T odoo odoo --config=/etc/odoo/odoo.conf

.DEFAULT_GOAL := help
.PHONY: help up down destroy restart logs ps shell psql init upgrade reinit test wait

help: ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

up: ## Start the stack and create the database if it is missing
	$(COMPOSE) up -d
	@$(MAKE) --no-print-directory wait
	@$(MAKE) --no-print-directory init
	@echo "Odoo is up at $(ODOO_URL)"

down: ## Stop the stack, keeping the database and filestore
	$(COMPOSE) down

destroy: ## Stop the stack and delete the database AND the filestore
	$(COMPOSE) down -v

restart: ## Restart the Odoo container
	$(COMPOSE) restart odoo

logs: ## Tail the Odoo log
	$(COMPOSE) logs -f odoo

ps: ## Show container status
	$(COMPOSE) ps

wait: ## Block until Odoo answers on /web/health
	@echo "Waiting for Odoo..."
	@for i in $$(seq 1 60); do \
		if $(COMPOSE) exec -T odoo curl -sf http://localhost:8069/web/health >/dev/null 2>&1; then \
			echo "Odoo is responding."; exit 0; \
		fi; \
		sleep 2; \
	done; \
	echo "Odoo did not come up in time. Try: make logs"; exit 1

init: ## Create the database if it does not exist
	@if ! $(COMPOSE) exec -T db psql -U odoo -d postgres -tAc \
		"SELECT 1 FROM pg_database WHERE datname='$(DB)'" | grep -q 1; then \
		echo "Creating database '$(DB)' with: $(INIT_MODULES)"; \
		$(ODOO_RUN) -d $(DB) -i $(INIT_MODULES) --stop-after-init; \
	elif ! $(COMPOSE) exec -T db psql -U odoo -d $(DB) -tAc \
		"SELECT to_regclass('public.ir_module_module')" | grep -q ir_module_module; then \
		echo "Database '$(DB)' exists but Odoo never finished initialising it."; \
		echo "A previous 'make up' most likely failed partway. Run: make reinit"; \
		exit 1; \
	else \
		echo "Database '$(DB)' is ready."; \
	fi

upgrade: ## Update $(MODULE) in the running database
	$(ODOO_RUN) -d $(DB) -u $(MODULE) --stop-after-init

reinit: ## Drop the database and rebuild it from scratch
	-$(COMPOSE) exec -T db dropdb -U odoo --if-exists $(DB)
	@$(MAKE) --no-print-directory init

shell: ## Open an Odoo shell on $(DB)
	$(COMPOSE) exec odoo odoo shell --config=/etc/odoo/odoo.conf -d $(DB)

psql: ## Open psql on $(DB)
	$(COMPOSE) exec db psql -U odoo -d $(DB)

test: ## Run the Playwright suite
	@if [ -f tests/package.json ]; then \
		cd tests && npx playwright test; \
	else \
		echo "No Playwright suite yet — added in Phase 9 (see PLAN.md)."; \
	fi
