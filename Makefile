.PHONY: install dev lint type test run serve clean

install:
	pip install -e ".[ingest,dev]"

dev: install
	pre-commit install || true

lint:
	ruff check src tests
	ruff format --check src tests

type:
	mypy

test:
	pytest -q

# End-to-end smoke run against the bundled fixture document and the fake
# code tool. Requires no network and no LLM endpoint.
smoke:
	dv run tests/fixtures/sample_doc.md --config config/default.yaml --fake

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build
	find . -name '__pycache__' -type d -exec rm -rf {} +
