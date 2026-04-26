.PHONY: install format lint typecheck test check clean

install:
	uv sync --all-extras

format:
	uv run ruff format src tests

lint:
	uv run ruff check src tests --fix

typecheck:
	uv run pyright

test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/ -v --ignore=tests/test_integration.py

test-integration:
	uv run pytest tests/test_integration.py -v

check: format lint typecheck test-unit

clean:
	rm -rf dist build *.egg-info .pytest_cache .ruff_cache .pyright __pycache__
