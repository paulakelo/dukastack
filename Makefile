.PHONY: help setup demo build chaos docs dagster lint test fmt clean

PYTHON ?= python3.11
VENV ?= .venv
BIN = $(VENV)/bin

help:
	@echo "dukastack Makefile targets:"
	@echo "  make setup    - Create virtualenv and install dependencies"
	@echo "  make demo     - Generate history and advance 14 days with dbt builds"
	@echo "  make build    - Run dbt build (snapshots, models, tests)"
	@echo "  make chaos    - Inject chaos scenarios C1-C6 and run tests"
	@echo "  make docs     - Generate and serve dbt documentation"
	@echo "  make dagster  - Start Dagster UI"
	@echo "  make lint     - Run ruff and sqlfluff linters"
	@echo "  make test     - Run pytest suite"
	@echo "  make fmt      - Format Python and SQL files"

setup:
	@if command -v uv >/dev/null 2>&1; then \
		uv venv --clear --python $(PYTHON) $(VENV); \
		uv pip install --python $(BIN)/python -e ".[dev]"; \
	else \
		$(PYTHON) -m venv $(VENV); \
		$(BIN)/pip install --upgrade pip; \
		$(BIN)/pip install -e ".[dev]"; \
	fi
	@if [ -f $(BIN)/pre-commit ]; then $(BIN)/pre-commit install; fi
	@echo "Setup complete. Activate with: source $(VENV)/bin/activate"

demo:
	rm -f data/*.duckdb* data/*.json data/*.parquet
	$(BIN)/python -m simulator.cli generate --days 30
	$(BIN)/dbt build --project-dir dbt --profiles-dir dbt
	@for i in $$(seq 1 14); do \
		echo "Advancing simulated day $$i/14..."; \
		$(BIN)/python -m simulator.cli advance; \
		$(BIN)/dbt build --project-dir dbt --profiles-dir dbt; \
	done

build:
	$(BIN)/dbt build --project-dir dbt --profiles-dir dbt

chaos:
	$(BIN)/python -m simulator.cli chaos

docs:
	$(BIN)/dbt docs generate --project-dir dbt --profiles-dir dbt
	$(BIN)/dbt docs serve --project-dir dbt --profiles-dir dbt

dagster:
	DAGSTER_HOME=$$(pwd)/.dagster $(BIN)/dagster dev -f orchestration/dukastack_dagster/definitions.py

lint:
	$(BIN)/ruff check .
	$(BIN)/sqlfluff lint dbt/models

test:
	$(BIN)/pytest tests/

fmt:
	$(BIN)/ruff format .
	$(BIN)/sqlfluff fix dbt/models

clean:
	rm -rf data/*.duckdb* data/*.parquet dbt/target/ dbt/dbt_packages/ .pytest_cache/ .ruff_cache/
