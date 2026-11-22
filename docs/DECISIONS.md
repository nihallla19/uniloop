# Decisions

## 2026-11-02

- **`system` schema created by Alembic env.py.** The version table lives in `system.alembic_version`, so `env.py` runs `CREATE SCHEMA IF NOT EXISTS system` before migrating, and migration 0001 uses `IF NOT EXISTS` for that one schema. All other DDL is verbatim from spec 5.3.
- **Role grants live in migration 0001**, guarded by `IF EXISTS baton_app`. Every future migration that adds a table must grant `baton_app` explicitly.
- **citext handle check is case-insensitive.** `handle ~ '^[a-z0-9_]...'` on a citext column accepts uppercase letters. The identity service must lower-case handles before insert. Tests cover the other pattern rules.
- **Vercel Services config** follows current docs: rewrite destinations are `{ "service": "<name>" }`, the API entrypoint is `app.main:app`, and FastAPI mounts routes under `/api/v1` because Vercel keeps the original path.
- **Local dev proxy.** `next.config.ts` rewrites `/api/*` to `localhost:8000` only when not on Vercel, so the browser stays same-origin locally too.
- **Design references supplied early** (owner's palette and the people4ocean screenshots), so a first pass of the visual design landed before Phase 3. The heading mint is darkened to `#4e8f86` to reach 3:1 on cream for large text; the reference mint fails WCAG.
- **GSAP + Lenis** are added for the preloader and scroll reveals, per the owner's global instruction. Both turn off under `prefers-reduced-motion`. Watch the 180 KB first-load JS budget (spec 8.6).
- **No passwords.** The owner asked for "forgot password". The spec uses email one-time codes, so there is no password to forget. The login page explains this and offers "Send a new code". Revisit only if the owner explicitly wants passwords.
- **Plain global CSS for now** instead of CSS Modules, to ship the first pass quickly. Split into modules if it grows.
- **Vercel account:** the owner chose their existing account (`banitsriram`, team "Banit's projects", Hobby) over a dedicated one. The project is `baton`. Hobby limits are shared with the owner's other projects.
- **First deploy landed on production.** Vercel assigns a new project's first deployment to production (`baton-blue.vercel.app`). It holds only the hello-world UI, sample data and a health route, with no secrets or database, and `noindex` is set. Later CLI deploys are previews. Production promotion still needs owner approval.
- **Rate-limit counters and code attempts use their own short transactions** so they persist even when the request fails and rolls back.
- **Every verify attempt counts**, the correct one included. That is simpler than counting only misses, and it still enforces "sixth attempt fails".
- **Verifying a code on an existing session sets `reauth_at`** instead of creating a new session. That is the hook for admin actions and account deletion later.
- **`uvicorn` is a dev dependency.** Without it, `uv run uvicorn` picked up a global Python 3.9 install. Vercel does not need it.
- **Product renamed Uniloop (user-facing only).** Repo, schemas, roles, cookie and `X-Baton-Client` header keep the Baton name; renaming them changes nothing users see and touches the spec contract.
- **Demo data (`scripts/seed_demo.py`)** is fictional, for presentations: `demo.*@example.edu` accounts, deterministic, removable with `--remove`, refuses to run in production. Present it as demo data, not real activity.
- **Catalog reads landed before the sell flow** so the demo has something to show. Search with a query returns one relevance-ranked page (no cursor yet); typo matching uses `word_similarity` > 0.4 on titles.
- **Server pages read the API through a Vercel service binding** (`API_INTERNAL_URL`), defaulting to `127.0.0.1:8000` locally. Pages are dynamic so the build never calls the API.
- **Test truncation re-seeds**: `TRUNCATE identity.users CASCADE` also clears `system.site_settings` via `updated_by`.
- **Demo mode (`DEMO_DATA=1`)** for showcasing without a hosted database: the web app serves the bundled fictional catalog (`apps/web/src/data/demo.json`, exported from a seeded local API) instead of calling FastAPI. Plain word search, offset paging, timestamps shifted to stay fresh. Set only on the Vercel production environment. Remove it once Neon is connected.
- **Demo photos** are 36 freely licensed Wikimedia Commons images (CC BY, CC BY-SA, CC0 or public domain), resized to 800x1000 WebP (metadata dropped) in `apps/web/public/demo/`, with photographer and licence credited on each listing page. Each was checked by eye; photos of identifiable people were rejected.
- **Vercel project renamed `uniloop`**, production domain `uniloop-app.vercel.app` (`uniloop.vercel.app` belongs to another project). The old `baton-blue.vercel.app` alias was removed.
