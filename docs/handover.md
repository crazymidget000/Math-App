# Handover notes

Context for the next working session. The full spec is [`plan.md`](plan.md). This file records
what has actually been built and decided so far. **No secrets belong here**: the repo is public.

## Session 1: Mon Nov 9, 2026 (Phuong + Cursor agent)

### Where we are

Sprint 1 item "framework app with user accounts, connected to Postgres, deployed to staging" is
**done** (stories S1-1 and S1-2, plus most of S1-3).

| Thing | Value |
|---|---|
| Repo | https://github.com/crazymidget000/Math-App (public, branch `main`) |
| Staging | https://mathquest-staging.onrender.com (Render, free instance) |
| Production | not created yet (Sprint 2) |
| Database (staging) | Neon project `young-bread-82152344`, branch `staging` |
| Database (production) | Same Neon project, branch `production` (empty, reserved for Sprint 2) |
| Local database | Postgres 17 in Docker (`docker compose up -d`) |
| Sprint 1 deadline | Wed Nov 11, 11:59pm ET |

### What was built

- **Django 6.1 project** `mathquest/` with settings read entirely from environment variables
  (`SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`). Render's own
  hostname is added to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` automatically. Logs go to
  stdout; static files are served by whitenoise; gunicorn is the web server.
- **Apps** under `apps/`: `accounts` (working), and `game`, `tutor`, `abtest` (empty shells for
  later stories).
- **Accounts (S1-2):**
  - `Player` model (`apps/accounts/models.py`): `user` (one-to-one), `hero` (prince/princess),
    `hero_name`, `level`, `xp`, `coins`, timestamps. Migration `0001_initial`.
  - Sign-up (`/accounts/signup/`): username, password twice, hero choice. No email field. Shows
    "Ask a grown-up to help you sign up." Creates the `User` and `Player` together, then logs in.
  - Login and logout use Django's built-in views. Logout is a POST form.
  - `/play/` is a login-required placeholder showing the player's name, level, XP and coins.
- **Frontend:** Pico.css and htmx are vendored in `static/` (credited in `static/CREDITS.md`).
  `static/css/theme.css` is the only place colors and fonts are defined; `game.css` uses its
  variables. Pages are forced to the light theme (`data-theme="light"` on `<html>`), because
  Pico's dark mode was overriding our colors.
- **Tests:** 13 pytest tests (`tests/`) covering sign-up, login, logout, the `/play/` redirect,
  and a check that the database is Postgres. They run against the Docker Postgres.
- **Tooling:** ruff (lint + format) and pytest are configured in `pyproject.toml`. No CI yet.

### Decisions made

- **Local Postgres runs in Docker**, not on Neon, so local work never touches staging data.
- **Neon over Supabase**: Supabase's free tier pauses idle projects and needs a manual restore,
  and its direct connection doesn't work from Render. Neon wakes automatically.
- **Neon branches** separate staging from production, rather than two separate databases.
  Both branches use the default `neondb` database.
- **Neon's extra features are off** (Neon Auth, Data API, `neon.ts` config). Django is the
  backend; Neon only stores data.
- **Layout reorganized** ([PR #1](https://github.com/crazymidget000/Math-App/pull/1)): feature
  apps live in `apps/`, and the plan moved to `docs/plan.md`. App labels are still short
  (`accounts`, `game`, ...), so table names and migrations didn't change. Imports use
  `apps.<name>`.
- **Extra package `python-dotenv`** (not in the plan) loads `.env` locally. The team should
  agree on it (plan rule 7) or it can be removed.

### Render staging settings

| Setting | Value |
|---|---|
| Build command | `pip install -r requirements.txt && python manage.py collectstatic --noinput` |
| Start command | `python manage.py migrate --noinput && gunicorn mathquest.wsgi --bind 0.0.0.0:$PORT` |
| Environment variables | `DATABASE_URL` (Neon staging, pooled), `SECRET_KEY`, `DEBUG=False` |
| Python version | From `.python-version` (3.14) |

### Local `.env` (gitignored)

`DATABASE_URL` points at Docker. The Neon connection strings are stored as
`NEON_STAGING_DATABASE_URL`, `NEON_PRODUCTION_DATABASE_URL` and their `_UNPOOLED` versions, ready
to paste into Render. Copy `.env.example` to get started on a new machine.

### Known issues and loose ends

1. **Render auto-deploy doesn't fire.** Auto-Deploy is set to "On Commit", but merging PR #1
   didn't trigger a deploy; it had to be deployed manually. The likely cause is that the service
   was created from the public repo URL rather than through a connected GitHub account, so
   GitHub never notifies Render. Fix options:
   - The `crazymidget000` account owner installs Render's GitHub app and grants it access to
     `Math-App`, then the service is reconnected to the repo.
   - Or add a GitHub Action that calls Render's deploy hook on every push to `main`, with the
     hook URL stored as a repo secret.

   Until then, **deploy manually after each merge**.
2. **Rotate the Neon staging password.** It was pasted into chat and a screenshot. Use
   `neon roles reset-password` (or the console), then update Render's `DATABASE_URL` and the
   local `.env`.
3. **Test account `staging_check`** exists on staging. Delete it from `/admin/` once the seed
   command creates the admin account.
4. **`neon init` rewrites `.env`** (it replaces `DATABASE_URL` and adds Node.js files). Don't
   rerun it without checking `.env` afterwards. The Neon plugin/MCP for Cursor is installed at
   the user level.
5. **Postgres versions differ:** Docker runs 17, Neon runs 18. That's harmless for now; bump the
   Docker image to `postgres:18` if it ever matters (doing so requires `docker compose down -v`).
6. **Teammates need access:** the repo owner should add all five members as collaborators.

### Open questions from reviewing the plan

- Answer-leak check (`\b{answer}\b`) will reject harmless hints when the answer is small (1, 2)
  and won't catch spelled-out numbers ("twelve").
- The A/B click form uses Django's CSRF token, so the course bot must keep cookies between the
  page load and the click. Check the course page for how the bot behaves.
- Stage 5 `pool` contents are unspecified; S2-2 says "addition" but covers Stages 1–2; the
  locked-monster response should be one fixed code (403 or 404).
- Still needed: teammates' course nicknames and GitHub usernames (for `team.yaml` and the A/B
  page), the OpenRouter key and model, and CC0 art packs.

### Next steps (rest of Sprint 1)

1. **S1-4, seed command:** `python manage.py seed`, idempotent, creates `grader` and `admin` from
   `SEED_GRADER_PASSWORD` / `SEED_ADMIN_PASSWORD`. Then append `&& python manage.py seed` to
   Render's start command and set both variables in Render.
2. **S1-5, A/B page:** `/f48c8ec`, `POST /f48c8ec/click`, `/f48c8ec/stats` per plan §9, with
   tests. Needs the teammates' nicknames.
3. **S1-6, GitHub Project:** a board with four sprint iterations and the backlog as issues
   labeled `user story`.
4. **S1-7, docs:** `docs/mgt656/team.yaml` and `docs/mgt656/sprints/sprint-1.md`.
5. Fix the Render auto-deploy (known issue 1).

Work rule from now on: one story per branch per pull request (plan §15).

### Commit history

| Commit | What |
|---|---|
| `aaecfb8` | S1-1 + S1-2: Django skeleton, Postgres, env config, accounts |
| `4492a03` | Force light theme so theme colors apply; tidy nav and error list |
| `a3fb0a5` | Ignore Neon CLI link file and `node_modules` |
| `efe37ef` / `e675470` | Reorganize layout into `apps/` and `docs/` (PR #1) |

### Quick start for the next session

```bash
cd "/Users/vuphuong/Desktop/Math app"
git pull
docker compose up -d            # Docker Desktop must be running
source .venv/bin/activate
pytest                          # expect 13 passed
python manage.py runserver      # http://localhost:8000
```
