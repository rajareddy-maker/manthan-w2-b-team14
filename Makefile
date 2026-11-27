# GridPulse — every developer/CI action goes through these targets.
SHELL := /bin/bash
.DEFAULT_GOAL := help

VENV      := .venv
PY        := $(VENV)/bin/python
COMPOSE   := docker compose
EXEC      := $(COMPOSE) exec -T airflow-scheduler
RUNPY     := /opt/gridpulse-venv/bin/python
DBT_FLAGS := --project-dir dbt_project --profiles-dir dbt_project
# LOCAL=1 runs dbt/GX in the local .venv instead of the Airflow container (used by CI).
ifdef LOCAL
  DBT := cd $(CURDIR) && $(VENV)/bin/dbt
  GXPY := $(PY)
else
  DBT := $(EXEC) bash -c 'cd /opt/gridpulse && /opt/gridpulse-venv/bin/dbt "$$@"' dbt
  GXPY := $(EXEC) $(RUNPY)
endif

.PHONY: help
help: ## List targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-16s %s\n",$$1,$$2}'

.PHONY: env
env: ## Create .env with random secrets if missing
	@bash scripts/init_env.sh

$(PY):
	python3 -m venv $(VENV)

.PHONY: setup
setup: env $(PY) ## Local venv with pinned deps + pre-commit hooks
	$(PY) -m pip install -q --upgrade pip==25.1.1
	$(PY) -m pip install -q -r requirements-dev.txt -c constraints.txt
	@if [ -d .git ]; then $(VENV)/bin/pre-commit install -f >/dev/null && echo "pre-commit installed"; fi

.PHONY: lock
lock: ## Regenerate constraints.txt from the local venv
	@{ echo "# Full resolved lock (pip freeze) of requirements-dev.txt on the local venv. Regenerate: make lock"; $(PY) -m pip freeze; } > constraints.txt

.PHONY: system-check
system-check: ## Check host prerequisites
	@bash scripts/system_check.sh

.PHONY: build
build: env ## Build the Airflow and Superset images
	$(COMPOSE) build

.PHONY: up
up: env ## Start the stack and wait until every service is healthy
	$(COMPOSE) up -d --build --wait --wait-timeout 600

.PHONY: down
down: ## Stop the stack (keeps volumes)
	$(COMPOSE) down

.PHONY: logs
logs: ## Follow logs (SERVICE=name to filter)
	$(COMPOSE) logs -f --tail 100 $(SERVICE)

.PHONY: ps
ps: ## Show service status
	$(COMPOSE) ps

.PHONY: smoke
smoke: ## Verify every service end to end
	@bash scripts/smoke_test.sh

.PHONY: lint
lint: ## ruff + black --check + sqlfluff
	$(VENV)/bin/ruff check .
	$(VENV)/bin/black --check .
	@if ls dbt_project/models/*/*.sql >/dev/null 2>&1; then $(VENV)/bin/sqlfluff lint dbt_project/models dbt_project/tests; else echo "sqlfluff: no models yet"; fi

.PHONY: format
format: ## Auto-format Python
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/black .

.PHONY: test
test: ## Unit tests with coverage (integration tests: make test-integration)
	$(VENV)/bin/pytest tests/unit --cov --cov-report=term-missing --cov-report=xml:docs/evidence/coverage.xml

.PHONY: test-integration
test-integration: ## Integration + e2e tests (needs make up)
	$(VENV)/bin/pytest tests/integration tests/e2e -m "integration or e2e"

.PHONY: dbt-debug
dbt-debug: ## dbt debug
	$(DBT) debug $(DBT_FLAGS)

.PHONY: dbt-run
dbt-run: ## dbt run
	$(DBT) run $(DBT_FLAGS)

.PHONY: dbt-test
dbt-test: ## dbt test
	$(DBT) test $(DBT_FLAGS)

.PHONY: gx-validate
gx-validate: ## Run Great Expectations checkpoints (SUITE=sample by default)
	$(GXPY) data_quality/gx/run_checkpoint.py --suite $(or $(SUITE),sample)

.PHONY: export-backlog
export-backlog: ## docs/scrum/product_backlog.md -> .xlsx
	$(PY) scripts/export_backlog.py

.PHONY: demo
demo: ## ONE command: setup, start stack, seed data, run the pipeline, print URLs
	@bash scripts/demo.sh

.PHONY: clean
clean: ## Stop stack, delete volumes and generated data
	$(COMPOSE) down -v --remove-orphans
	rm -rf data dbt_project/target dbt_project/logs .pytest_cache .ruff_cache htmlcov .coverage
