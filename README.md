# Math Quest

A turn-based math battle game for kids aged 6–10. Django + Postgres + htmx.
See [`plan.md`](plan.md) for the full build plan.

## Local setup

You need Python 3.12+ and Docker Desktop.

```bash
# 1. Start Postgres (runs in the background, data persists between restarts)
docker compose up -d

# 2. Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Config: copy the example and set SECRET_KEY to any long random string
cp .env.example .env

# 4. Database tables, an admin user, and run
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://localhost:8000.

## Checks (same as CI)

```bash
ruff check .
ruff format --check .
pytest
```

Tests run against the Docker Postgres, so it must be up (`docker compose up -d`).
Stop it with `docker compose down`; add `-v` to also wipe the data.

## Deploying to Render (staging)

Web service settings:

| Setting | Value |
|---|---|
| Build command | `pip install -r requirements.txt && python manage.py collectstatic --noinput` |
| Start command | `python manage.py migrate --noinput && gunicorn mathquest.wsgi --bind 0.0.0.0:$PORT` |
| Auto-deploy | On, from `main` |

Environment variables: `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL` (Neon staging connection
string). Render's own hostname is added to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
automatically; set those two variables only for extra custom domains. The Python version
comes from `.python-version`.

## Project layout

- `mathquest/`: settings and URLs
- `accounts/`: sign-up, `Player` profile, hero choice
- `game/`: stages, monsters, battles (world map placeholder for now)
- `tutor/`: AI tutor (Sprint 2+)
- `abtest/`: A/B test page (S1-5)
- `templates/`, `static/`: pages, Pico.css, htmx, and `css/theme.css` (all colors and fonts)
- `tests/`: pytest tests
