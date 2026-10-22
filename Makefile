.PHONY: setup dev dev-web dev-api smoke test test-e2e browsers lint typecheck format build audit db-up db-down compose-check check team-check team-check-integration

setup:
	npm ci
	cd apps/api && uv sync --locked

team-check:
	python3 scripts/team_doctor.py

team-check-integration:
	python3 scripts/team_doctor.py --integration

dev:
	python3 scripts/dev.py

dev-web:
	npm run dev:web

dev-api:
	cd apps/api && uv run --frozen uvicorn forge_api.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log

smoke:
	python3 scripts/smoke.py

test:
	npm test
	cd apps/api && uv run --frozen pytest

test-e2e:
	npm run test:e2e

browsers:
	npm exec playwright install chromium firefox webkit

lint:
	npm run lint
	cd apps/api && uv run --frozen ruff check . ../../scripts
	cd apps/api && uv run --frozen ruff format --check . ../../scripts

typecheck:
	npm run typecheck
	cd apps/api && uv run --frozen mypy src tests migrations ../../scripts

format:
	npm run format
	cd apps/api && uv run --frozen ruff format . ../../scripts

build:
	npm run build

audit:
	npm run audit:dependencies
	cd apps/api && uv run --frozen pip-audit --skip-editable

compose-check:
	docker compose config --quiet

.PHONY: deployment-check
deployment-check:
	cd apps/api && uv run --frozen python ../../scripts/deployment_check.py

db-up:
	docker compose up --detach --wait --wait-timeout 90 postgres

db-down:
	docker compose down

check: lint typecheck test build compose-check

.PHONY: migrate migration-check dev-web-https test-postgres
migrate:
	cd apps/api && uv run --frozen alembic upgrade head

migration-check:
	cd apps/api && uv run --frozen alembic check

dev-web-https:
	npm run dev --workspace @forge/web -- --mode local-https

test-postgres:
	cd apps/api && uv run --frozen pytest tests/test_postgres.py tests/test_safe_edit_postgres.py
