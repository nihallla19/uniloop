# Uniloop

Campus resale marketplace: students pass on what they no longer need. Live demo: https://uniloop-app.vercel.app

The listings, students and conversations in the demo are **fictional demo data**.

- `apps/web`: website (Next.js, TypeScript, GSAP and Lenis)
- `apps/api`: backend (Python FastAPI, Postgres)
- `docs/`: decisions and progress notes (Baton was the working name)

## Quickest way to run it: website only, demo data

Needs [Node.js](https://nodejs.org) 20 or newer. No database needed.

```bash
cd apps/web
npm install
DEMO_DATA=1 npm run dev
```

Open http://localhost:3000. On Windows PowerShell, use `$env:DEMO_DATA=1; npm run dev`.

## Full app: website, API and database

Needs Node.js, [Docker Desktop](https://www.docker.com/products/docker-desktop/) and [uv](https://docs.astral.sh/uv/).

```bash
docker compose up -d --wait postgres      # local database
cp .env.example apps/api/.env
cd apps/api
uv sync
uv run alembic upgrade head               # create tables
uv run python -m scripts.seed             # categories and settings
uv run python -m scripts.seed_demo        # fictional demo listings
uv run uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd apps/web
npm install
npm run dev
```

Sign in with any `@example.edu` address. The 6-digit code is printed in the API terminal.

## Tests

```bash
cd apps/api && uv run pytest
```

## Credits

Demo photos are from Wikimedia Commons under CC BY, CC BY-SA, CC0 or public-domain licences. Each listing page credits the photographer and licence.
