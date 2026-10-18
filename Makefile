.PHONY: help setup demo demo-fail demo-recover build chaos docs docs-serve dagster queries lint test fmt clean

PYTHON ?= python3.11
VENV ?= .venv
BIN = $(VENV)/bin

help:
	@echo "dukastack Makefile targets:"
	@echo "  make setup        - Create virtualenv and install dependencies"
	@echo "  make demo         - Generate seeded 30-day history and run full warehouse build"
	@echo "  make demo-fail    - Inject bad dataset causing test failure and blocking marts"
	@echo "  make demo-recover - Remove bad dataset, re-run build, and verify recovery"
	@echo "  make build        - Run dbt build (snapshots, models, tests)"
	@echo "  make chaos        - Inject chaos scenarios C1-C6 and run tests"
	@echo "  make docs         - Generate dbt documentation artifacts"
	@echo "  make docs-serve   - Serve dbt documentation locally"
	@echo "  make dagster      - Start Dagster UI"
	@echo "  make queries      - Execute sample queries and update docs/sample_queries.md"
	@echo "  make lint         - Run ruff and sqlfluff linters"
	@echo "  make test         - Run pytest suite"
	@echo "  make fmt          - Format Python and SQL files"
	@echo "  make clean        - Remove generated data and build artifacts"

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
	$(BIN)/python -m simulator.cli generate --days 30 --seed 42
	$(BIN)/dbt build --project-dir dbt --profiles-dir dbt
	@echo ""
	@echo "========================================================================"
	@echo "dukastack demo warehouse ready!"
	@echo "  - dbt Docs: Run 'make docs-serve' (opens at http://localhost:8080 or port shown)"
	@echo "  - Dagster UI: Run 'make dagster'   (opens at http://localhost:3000)"
	@echo "========================================================================"

demo-fail:
	$(BIN)/python scripts/demo_chaos.py fail

demo-recover:
	$(BIN)/python scripts/demo_chaos.py recover

build:
	$(BIN)/dbt build --project-dir dbt --profiles-dir dbt

chaos:
	$(BIN)/python -m simulator.cli chaos

docs:
	$(BIN)/dbt docs generate --project-dir dbt --profiles-dir dbt

docs-serve:
	$(BIN)/dbt docs serve --project-dir dbt --profiles-dir dbt

dagster:
	mkdir -p .dagster
	DAGSTER_HOME=$$(pwd)/.dagster $(BIN)/dagster dev -f orchestration/dukastack_dagster/definitions.py

queries:
	$(BIN)/python scripts/render_sample_queries.py

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
