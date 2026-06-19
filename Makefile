# Convenience targets for local development.

SHELL := /bin/bash
.DEFAULT_GOAL := help

UV ?= uv
BUN ?= bun

.PHONY: help
help:  ## show this help
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / { printf "  %-12s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: dev
dev:  ## run backend (uvicorn --reload) + frontend (vite dev) concurrently
	@trap 'kill 0' INT TERM EXIT; \
	$(UV) run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 & \
	cd frontend && $(BUN) run dev & \
	wait

.PHONY: test
test:  ## run the full test suite (Python + frontend)
	@LLM_PROVIDER=stub $(UV) run pytest -q
	@cd frontend && $(BUN) run test --run

.PHONY: lint
lint:  ## ruff + tsc + eslint
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy backend/app pipeline agents
	@cd frontend && $(BUN) run typecheck && $(BUN) run lint

.PHONY: format
format:  ## auto-format Python (ruff)
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

.PHONY: build
build:  ## docker compose build
	docker compose build

.PHONY: up
up:  ## docker compose up -d
	docker compose up -d

.PHONY: down
down:  ## docker compose down
	docker compose down

.PHONY: clean
clean:  ## remove processed/, __pycache__/, build artefacts
	rm -rf data/processed/* data/uploads/* data/mmr.db
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	find . -type d -name .mypy_cache -prune -exec rm -rf {} +
	find . -type d -name .ruff_cache -prune -exec rm -rf {} +
	rm -rf frontend/dist frontend/.vite coverage.xml .coverage

.PHONY: fixture
fixture:  ## regenerate the tiny test parquet (also committed)
	PYTHONPATH=. $(UV) run python tests/fixtures/_generate_tiny_master_df.py

.PHONY: smoke-groq
smoke-groq:  ## run the agent chain against real Groq on the tiny fixture
	PYTHONPATH=. $(UV) run python scripts/smoke_test_groq.py
