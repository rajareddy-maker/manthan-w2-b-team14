# GridPulse — every developer/CI action goes through these targets.
SHELL := /bin/bash
.DEFAULT_GOAL := help

VENV      := .venv
# Windows (Git Bash) venvs use Scripts/, Linux/macOS use bin/
VBIN      := $(VENV)/$(if $(filter Windows_NT,$(OS)),Scripts,bin)
PY        := $(VBIN)/python
COMPOSE   := docker compose
EXEC      := $(COMPOSE) exec -T airflow-scheduler
RUNPY     := /opt/gridpulse-venv/bin/python
DBT_FLAGS := --project-dir dbt_project --profiles-dir dbt_project
# LOCAL=1 runs dbt/GX in the local .venv instead of the Airflow container (used by CI).
ifdef LOCAL
  DBT := cd $(CURDIR) && $(VBIN)/dbt
  GXPY := $(PY)
  APPPY := $(PY)
else
  DBT := $(EXEC) bash -c 'cd /opt/gridpulse && /opt/gridpulse-venv/bin/dbt "$$@"' dbt
  GXPY := $(EXEC) $(RUNPY)
  APPPY := $(EXEC) bash -c 'cd /opt/gridpulse && $(RUNPY) "$$@"' py
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
	@if [ -d .git ]; then $(VBIN)/pre-commit install -f >/dev/null && echo "pre-commit installed"; fi

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
	$(VBIN)/ruff check .
	$(VBIN)/black --check .
	@if ls dbt_project/models/*/*.sql >/dev/null 2>&1; then $(VBIN)/sqlfluff lint dbt_project/models dbt_project/tests; else echo "sqlfluff: no models yet"; fi

.PHONY: format
format: ## Auto-format Python
	$(VBIN)/ruff check --fix .
	$(VBIN)/black .

.PHONY: test
test: ## Unit + dbt + stack integration tests with coverage (stack tests skip if the stack is down)
	$(VBIN)/pytest tests/unit tests/integration -m "not e2e" --cov --cov-report=term-missing --cov-report=xml:docs/evidence/coverage.xml

.PHONY: test-dbt
test-dbt: ## Crafted meter histories through landing -> bronze -> dbt build (DuckDB, no docker)
	$(VBIN)/pytest tests/integration -m dbt

.PHONY: test-integration
test-integration: ## Integration + e2e tests (needs make up)
	$(VBIN)/pytest tests/integration tests/e2e -m "integration or e2e"

.PHONY: generate
generate: ## Synthetic landing data + meter master seeds (DAYS=7 default)
	$(APPPY) -m ingestion.generator --days $(or $(DAYS),7)

.PHONY: bronze
bronze: ## Load every landing date into bronze Parquet (DT=YYYY-MM-DD for one date)
	$(APPPY) -m ingestion.extractors.landing_to_bronze $(if $(DT),--dt $(DT),--all)

.PHONY: dbt-build
dbt-build: ## dbt build (seeds + models + tests)
	$(DBT) build $(DBT_FLAGS)

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

.PHONY: backfill
backfill: ## Reprocess a date range via Airflow: make backfill START=2026-11-20 END=2026-11-26
	bash scripts/airflow_trigger_wait.sh gridpulse_backfill '{"start":"$(START)","end":"$(END)"}' 2400

.PHONY: dashboard
dashboard: ## Create/update the Superset dashboard as code
	python3 scripts/superset_dashboard.py

.PHONY: demo
demo: ## ONE command: setup, start stack, seed data, run the pipeline, print URLs
	@bash scripts/demo.sh

.PHONY: clean
clean: ## Stop stack, delete volumes and generated data
	$(COMPOSE) down -v --remove-orphans
	rm -rf data dbt_project/target dbt_project/logs .pytest_cache .ruff_cache htmlcov .coverage
