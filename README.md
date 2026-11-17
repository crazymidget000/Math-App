# Math Quest

A turn-based math battle game for kids aged 6–10. Django + Postgres + htmx.
See [`docs/plan.md`](docs/plan.md) for the full build plan.

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

## Addition and subtraction generator

`apps/game/generator.py` implements the Stage 1–2 monster parameter sets in
[`docs/plan.md`](docs/plan.md), section 6. Pass a monster's `question_params` and
reuse a `random.Random` instance:

```python
from random import Random
from apps.game.generator import generate_question

rng = Random(42)  # Seed for reproducible tests; use Random() during normal play.
question = generate_question({"op": "add", "max_sum": 10}, rng)
# question has prompt, a, b, operation, and answer fields.
```

Ranges and maximums are inclusive. Without explicit operand ranges, operands
start at zero. Subtraction answers are nonnegative. Invalid or impossible
parameters raise `ValueError`. The battle service keeps the answer on the server
until the player answers and avoids consecutive duplicate questions.

The generator tests cover all eight Stage 1–2 configurations and run with pytest,
or independently without Django, Postgres, or third-party packages:

```bash
python -m unittest discover -s tests -p test_generator.py
```

## Playing Stage 1

Run `python manage.py migrate` after updating the code. The game migrations create
Addition Meadow and its four monsters automatically, including on Render where
the start command already runs migrations. Sign up or log in, open `/play/`, and
choose **Battle Slime**. Answer the question and press **Attack!**. Correct answers
deal 20 damage (30 within six seconds); mistakes cost 15 HP, or 20 against the boss.
There is no time limit. Defeating a monster unlocks the next one.

You can resume an active battle, leave it, or retry after losing. A win awards XP
and coins once per battle; replaying a completed monster is allowed. Stage 1 rewards
are 40/50/60/100 XP and 10/15/20/40 coins. HP and question difficulty follow the plan.
Later stages are separate stories and are not yet available.

Battle state is stored on the server. Answer submissions include the question ID
so repeated or stale submissions cannot attack twice. Services lock the player
and battle inside a transaction, and only the owning player can access a battle.
The page works both with htmx updates and ordinary form submissions.

```bash
pytest tests/test_rules.py tests/test_battle.py tests/test_battle_concurrency.py
```

The concurrency tests require PostgreSQL; SQLite does not exercise row locks.

## Ask the Wizard (Sprint 2)

After a wrong answer, **Ask the Wizard** offers a short explanation for that specific
question. The hint is labelled with the old question while the next question remains
playable. It works with htmx and ordinary form submissions, including after losing a battle.
Hints are saved per question, so repeat requests reuse the result rather than calling AI again.

Run `python manage.py migrate` for the new hint table. Configure `OPENROUTER_API_KEY` and
`OPENROUTER_MODEL` in your local `.env` or the Render service's environment variables.
Choose a model supporting JSON object output. `AI_TIMEOUT_SECONDS` defaults to `8`.
The server calls OpenRouter; neither the key nor raw provider errors are sent to the browser.
Only the question's operands, operation and numeric player answer enter the user prompt.

Missing credentials, provider errors, timeouts, or invalid JSON use a predefined hint.
This means a working fallback alone does **not** verify the real OpenRouter integration.
The response is checked for required fields, allowed strategies, up to four steps and
160-character text bounds. Answer-leak detection, daily limits and strategy icons remain
Sprint 3 work; the model is instructed not to state the answer, without a leakage guarantee.

```bash
pytest tests/test_tutor.py tests/test_tutor_concurrency.py
```

These tests mock OpenRouter and never spend API credits. To verify on staging after deployment:
log in, enter a battle, submit a wrong answer, then select **Ask the Wizard**. Confirm its
question label matches the wrong question and answering the next question still works.
Check once with the configured model and once with credentials absent in a local environment
to exercise the fallback; do not remove shared staging credentials just for this check.

## Staging (Render)

Web service settings:

| Setting | Value |
|---|---|
| Build command | `pip install -r requirements.txt && python manage.py collectstatic --noinput` |
| Start command | `python manage.py migrate --noinput && python manage.py seed && gunicorn mathquest.wsgi --bind 0.0.0.0:$PORT` |
| Auto-deploy | On, from `main` |

Environment variables: `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL` (Neon staging connection
string), `SEED_GRADER_PASSWORD`, `SEED_ADMIN_PASSWORD`.

`python manage.py seed` creates or updates the `grader` (fresh player) and `admin` (staff +
superuser) accounts with those passwords. It is safe to run on every deploy: it never
duplicates accounts, keeps the grader's game progress, and only changes a password when the
environment variable changes. Render's own hostname is added to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
automatically; set those two variables only for extra custom domains. The Python version
comes from `.python-version`.

## Production

Production is a second Render web service, `mathquest-production`, with its own database (the
Neon `production` branch). It deploys from the git branch **`production`**, never from `main`,
and its auto-deploy is off. Nobody pushes to `production` by hand.

| | Staging | Production |
|---|---|---|
| Render service | `mathquest-staging` | `mathquest-production` |
| Git branch | `main` | `production` |
| Neon branch (`DATABASE_URL`) | `staging` | `production` |
| How it deploys | after merging to `main` | "Promote to production" workflow |

Settings are the same as staging (build command, start command, variable names), except:
`DATABASE_URL` is the Neon **production** connection string, `SECRET_KEY` is different, and
auto-deploy is off. `SEED_GRADER_PASSWORD` and `SEED_ADMIN_PASSWORD` match staging, so the
grader accounts work on both.

### Promoting to production

1. Check the change works on staging first.
2. On GitHub, open **Actions → Promote to production → Run workflow**, type `promote`, and run it.
3. The workflow ([`.github/workflows/promote.yml`](.github/workflows/promote.yml)) fast-forwards
   `production` to the current `main`, then calls Render's deploy hook. The run summary shows
   which commit was promoted and by whom.
4. Watch the deploy in Render, then check the production site.

The workflow refuses to run if `production` has commits that aren't on `main`. It needs the
repository secret `RENDER_PRODUCTION_DEPLOY_HOOK` (Render: service **Settings → Deploy Hook**).

**Production freeze:** don't promote, change production variables or reset its database during
the announced A/B bot window (plan §12).

## Project layout

```
mathquest/      Django config: settings, URLs, WSGI entry point
apps/           All feature code, one folder per feature
  accounts/       sign-up, login, Player profile, hero choice
  game/           question generator, battle rules, playable Stage 1
  tutor/          AI tutor "Ask the Wizard" (Sprint 2+)
  abtest/         A/B test page (S1-5)
templates/      HTML pages, one subfolder per app
static/         CSS, JS, images; css/theme.css holds every color and font
tests/          pytest tests
docs/           plan.md (the build plan) and course docs
```

Root files are tool config: `manage.py` (Django commands), `requirements.txt`,
`pyproject.toml` (ruff + pytest), `docker-compose.yml` (local Postgres), `.env.example`,
`.python-version` (used by Render).
