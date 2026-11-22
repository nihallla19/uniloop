# Progress

## 2026-11-22: Production login fix (Turnstile widget, env)

**Changed**
- Web login now renders the Turnstile widget (explicit render, no new dependency) and sends `turnstile_token` with request-code. The API already required it, so production sign-in could never have passed. The token resets after each request so "Send a new code" works.
- Vercel `uniloop` Production env: added `APP_ENV`, `APP_ORIGIN=https://uniloop-app.vercel.app`, `ALLOWED_EMAIL_DOMAINS=dsu.edu.in`. Before this, a missing `APP_ORIGIN` made every POST fail CSRF ("Please refresh the page").

**Tests run**
- `tsc`, eslint clean. Local browser with Cloudflare's always-pass test key: widget renders, button unlocks, token is sent. Full flow not run (Docker down).

**Blockers**
- Owner to add the secrets in Vercel: database URLs, peppers, cron secret, Resend key and `EMAIL_FROM`, Turnstile keys, R2, image base URL. Then migrate, seed and redeploy.

## 2026-11-02: Catalog reads (Phase 3 part 1), demo data, Uniloop rename

**Changed**
- API: `GET /catalog/bootstrap`, `GET /listings` (keyset pagination, category, price sorts, full-text and typo search, block filtering, search rate limit), `GET /listings/{id}` (spec 5.5 visibility, derived sold count, labelled details).
- Web: home feed, `/search` (URL state, category chips, sort, show more) and `/listing/[id]` all read the API. Listings show as a grid. User-facing name is now Uniloop.
- `scripts/seed_demo.py`: 24 fictional students, 44 listings, favourites and 12 conversations.

**Tests run**
- `pytest`: 58 passed (9 new catalog tests: live-only feed, pagination with no gaps or duplicates, price sort, typo search, SQL injection strings, bad inputs, visibility, blocks, public-browsing switch).
- Pages render, with clean fallbacks when the API is down.

**Not done**
- Photos (media pipeline), the sell flow's write side, favourites UI, storefront pages.

## 2026-11-02: Phase 2 (identity and security core), Phase 0 deploy

**Changed**
- Security: app-wide CSRF (header and origin), Postgres rate limits (HMAC buckets, `Retry-After`), server-side sessions (hashed tokens, `__Host-` cookie, 15-minute last-seen throttle, live status check), Turnstile verification, login codes (HMAC with pepper, 10 minutes, single use, 5 attempts).
- Identity routes: request and verify code (signup with name, terms and age), logout, logout-all, `/me`, profile patch, preferences get and put (strict model), sessions list and revoke. Global budget of 95 login emails a day. Malformed path ids return 404.
- Web login is now three steps: email, code, then details for first-time users.
- Linked Vercel project `baton` on the owner's existing account and deployed.

**Tests run**
- `pytest`: 49 passed. New auth tests cover signup, returning sign-in, enumeration, domain and `+` rules, code reuse, expiry and invalidation, the sixth attempt, 429s, CSRF, suspended sessions, logout, session isolation, mass assignment, handle conflicts, strict preferences and error leakage.
- Phase 0 gate passed on `baton-dju3ischh-banit-s-projects.vercel.app`: `/` and `/api/v1/health` both return 200.
- Local browser: full signup flow through to an authenticated `/me`.

**Blockers**
- Phase 2 gate ("login works on preview") needs a Neon database, a Resend sender and a Turnstile widget. All are human setup.
- No GitHub repo yet, so CI has not run.
- First deploy is on production (see DECISIONS). Owner to decide whether to keep it.

## 2026-11-02 — Phase 0 and Phase 1 (local), first design pass

**Changed**
- Repo skeleton, FastAPI app (config validation, NullPool engine, error format, request-id JSON logs, security headers), `/api/v1/health` and cron-protected `/api/v1/health/ready`.
- Alembic migration 0001 with the full spec 5.3 schema and spec 5.7 grants. Idempotent seed (spec 5.9, DEV placeholders) and `create_admin` promotion script.
- docker-compose (Postgres 17 and MinIO), Makefile, `.env.example`, CI workflow, manual `migrate.yml`, Dependabot.
- Next.js 16 web app: home, login (email code), sell form shell. Brand mark, GSAP preloader, Lenis smooth scroll, owner palette.

**Tests run**
- `pytest`: 30 passed. Covers the table inventory against the spec, role permissions (no DDL, append-only moderation log, no `alembic_version` access), every 5.3 constraint family, downgrade/upgrade on seeded data, health and cron 401s.
- ruff and mypy (strict) clean. tsc, eslint and `next build` clean. Checked in the browser.

**Blockers**
- Phase 0 gate (preview deploy) waits on the owner confirming the Vercel account (`vercel whoami` = `banitsriram`) and creating the GitHub repo.
- Section 0.2 values are still placeholders.
- Listings and auth APIs are not built yet, so the UI uses sample data and the login shows a "not live yet" message.
