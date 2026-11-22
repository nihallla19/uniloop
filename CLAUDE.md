# Baton

Source of truth: `BATON_BUILD_SPEC.md` (read it fully before changing anything).
Record decisions in `docs/DECISIONS.md`, phase notes in `docs/PROGRESS.md`.

## Local run

```bash
docker compose up -d --wait postgres     # Postgres 17 with baton_migrator / baton_app roles
cp .env.example apps/api/.env            # first time only
make migrate                             # alembic upgrade head (direct URL, migrator role)
make seed                                # categories, pickup points, settings
cd apps/api && uv run python -m scripts.seed_demo   # FICTIONAL demo data (--remove to delete)
cd apps/api && uv run uvicorn app.main:app --reload --port 8000   # --reload picks up code changes
cd apps/web && npm run dev               # http://localhost:3000, /api proxied to :8000
```

## Checks

```bash
make test       # pytest against real Postgres (baton_test DB)
make lint       # ruff, mypy, eslint, tsc
make security   # bandit, pip-audit, npm audit
```

## Rules of thumb
- Schema-qualify every table. No `SET search_path`, no prepared statements (Neon pooler).
- Never run migrations from app code or the Vercel build.
- No inline `style=""` in server-rendered markup (CSP). Use classes or client CSSOM.
- Animation: GSAP + Lenis (owner's global preference); always honour reduced motion.
