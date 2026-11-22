API = cd apps/api &&
WEB = cd apps/web &&

.PHONY: up down dev test lint migrate seed security

up:
	docker compose up -d --wait postgres

down:
	docker compose down

dev: up
	$(API) uv run uvicorn app.main:app --reload --port 8000 & \
	$(WEB) npm run dev

test: up
	$(API) uv run pytest --cov=app

lint:
	$(API) uv run ruff check . && uv run ruff format --check . && uv run mypy
	$(WEB) npm run lint && npm run typecheck

migrate: up
	$(API) uv run alembic upgrade head

seed:
	$(API) uv run python -m scripts.seed

security:
	$(API) uv run bandit -q -r app && uv run pip-audit
	$(WEB) npm audit --omit=dev
