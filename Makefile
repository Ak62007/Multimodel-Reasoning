# Developer Makefile (per spec §12.2).
#
# Common workflows:
#   make dev      # uvicorn --reload + vite dev concurrently
#   make test     # full Python + frontend test suite
#   make lint     # ruff + tsc + eslint
#   make build    # docker compose build
#   make clean    # wipe build artefacts and data/processed/*

.PHONY: help dev backend frontend test lint build clean fmt mypy

help:
	@echo "MMR developer targets"
	@echo "  make dev       — uvicorn --reload + vite dev concurrently"
	@echo "  make backend   — uvicorn --reload"
	@echo "  make frontend  — vite dev"
	@echo "  make test      — python + frontend test suites"
	@echo "  make lint      — ruff + mypy + tsc + eslint"
	@echo "  make fmt       — ruff format ."
	@echo "  make build     — docker compose build"
	@echo "  make clean     — wipe build artefacts and data/processed/*"

dev:
	@command -v concurrently >/dev/null 2>&1 || npx --yes concurrently --version >/dev/null
	npx --yes concurrently -n backend,frontend -c blue,magenta \
		"$(MAKE) backend" \
		"$(MAKE) frontend"

backend:
	uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	uv run pytest -q
	cd frontend && npx vitest run

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	cd frontend && npm run lint && npm run typecheck

fmt:
	uv run ruff format .

mypy:
	uv run mypy

build:
	docker compose build

clean:
	rm -rf data/processed/* data/uploads/* data/mmr.db
	rm -rf frontend/dist frontend/.vite frontend/coverage
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
	rm -f coverage.xml .coverage
