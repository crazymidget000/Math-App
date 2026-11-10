# Math Quest: build plan

> **How to use this file with Cursor:** this file lives at `docs/plan.md`; add it as context in every Cursor chat (`@plan.md`). Build **one user story at a time** (see §12), on its own branch, and open a pull request for each. When this plan and the course project page disagree, the course page wins.

---

## 1. What we are building

**Math Quest** is a turn-based math battle game for children aged 6–10, played in the browser (phone or desktop).

- The player picks a **prince or princess** hero and travels through stages, fighting monsters.
- Each turn, the player gets a math question (e.g. `7 + 5 = ?`).
  - **Correct** → the hero attacks and the monster loses HP.
  - **Wrong** → the monster attacks and the hero loses HP. The game shows the correct answer, and the player can ask the **AI tutor** for a hint.
- The battle ends when either HP bar hits 0.
- Winning earns **XP and coins**. XP levels up the hero. Beating a stage's boss unlocks the next stage.
- Stages: **1 Addition → 2 Subtraction → 3 Multiplication → 4 Division → 5 Mixed**.

This follows our approved proposal (Proposal 2, "Math Quest"). Out of scope for the MVP: real-time combat, complex animation, multiplayer, open-world maps, equipment/shop/inventory, native mobile apps.

**Team:** inner-wrath (Alison Liu, Gina Moon, Jung Tae Ji, Phuong Vu, Shixuan Sun)
**Course:** MGT 656, Fall 2026 (Kyle Jensen)

---

## 2. Course requirements checklist (from the project page)

| # | Requirement | How Math Quest meets it |
|---|---|---|
| 1 | Framework: Django/Rails/Laravel/Phoenix/AdonisJS | **Django** |
| 2 | PostgreSQL or MySQL; staging and prod each have their own DB | **Postgres on Neon**, two separate databases |
| 3 | User accounts with the framework's standard auth | `django.contrib.auth`: username + password sign-up/login/logout |
| 4 | An AI feature via **OpenRouter**, called from the server only | AI tutor hints (§8) |
| 5 | Automated tests; never call the real LLM or external services | pytest-django; OpenRouter is always mocked |
| 6 | Public staging **and** production | Two Render web services (prod from Sprint 2) |
| 7 | 12-factor basics | Env vars for all config/secrets, `DATABASE_URL`, logs to stdout, no local-disk data, listen on `$PORT`, migrations |
| 8 | Idempotent seed command that creates demo data + grader accounts | `python manage.py seed` (§10) |
| 9 | Usable on phones and desktops | Pico.css + mobile-first battle layout |
| 10 | The A/B test page | `/f48c8ec` and `/f48c8ec/stats` (§9) |

**Technical-challenge items we're aiming for** (Kyle wants ~3 done *well*: tested, working in the deployed app, and handling failure):
1. **Live battles with htmx**: the battle updates without full page reloads.
2. **CI + CD**: tests and lint on every PR (merge blocked on failure). Merging to `main` auto-deploys staging, with a deliberate step to promote to production.
3. **AI: structured output + per-user usage limits**: the tutor returns JSON that the app validates and acts on, and each player gets a daily hint limit.
4. **Playwright end-to-end tests**: a real browser plays a full battle and checks the A/B page counting.

If time gets tight, #4 is the one to trim; the other three are core.

**Grading (60 points for the final submission):**
- 20: working app and the required items
- 20: technical challenge
- 10: A/B test (a working page **and** a correct `preferred` value after the bot run)
- 10: process and docs (backlog, pull requests, `technical.md`, retrospective)

The four sprints are graded separately: Sprint 1 is 10 points, and Sprints 2–4 are 15 each. Each sprint is graded on what shipped, the sprint report and how we worked. If the app or a grader account is broken when they grade, they tell us and we have **24 hours** to fix it. Questions go in the course GitHub Discussions.

**How the course expects us to work:** AI coding agents write most of the code, and that's expected. Our job is to direct them well: clear stories, careful review, and an app the whole team understands. Everyone on the team gets the same grade.

---

## 3. Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.12+ |
| Framework | Current stable Django (pin the version in `requirements.txt`) |
| DB driver / config | `psycopg[binary]`, `dj-database-url` |
| Web server | `gunicorn` bound to `0.0.0.0:$PORT` |
| Static files | `whitenoise` (no CDN dependency) |
| Interactivity | `htmx` (vendored into `static/js/htmx.min.js`) + `django-htmx` |
| CSS | Pico.css (vendored) + our own `static/css/game.css` |
| HTTP client for the LLM | `httpx` (with timeout) |
| Tests | `pytest`, `pytest-django`, `pytest-playwright` |
| Lint/format | `ruff` |
| Hosting | **Render** (app) + **Neon** (Postgres). We avoid Render's free Postgres because it's deleted after 30 days. |
| Art | Free **CC0** game art (e.g. Kenney.nl packs, or OpenGameArt filtered to CC0). Emoji placeholders until art is added. Credit every pack in `static/CREDITS.md`. |

No React, no SPA, no game engine. Pages are server-rendered Django templates, and htmx swaps in HTML fragments.

---

## 4. Project layout

```
.
├── manage.py                  # Django command runner (stays at the root)
├── requirements.txt           # Python packages, pinned
├── pyproject.toml             # ruff + pytest settings
├── docker-compose.yml         # local Postgres
├── .env.example               # every env var, with fake values; real .env is gitignored
├── .python-version            # Python version Render uses
│
├── mathquest/                 # Django project config: settings.py, urls.py, wsgi.py
├── apps/                      # all feature code, one Django app per feature
│   ├── accounts/              # sign-up view/form, Player profile, hero picker
│   ├── game/                  # stages, monsters, battles, question generator, rules
│   │   ├── generator.py       # pure functions: make questions + answers (no DB)
│   │   ├── rules.py           # pure functions: damage, XP, level-up, unlocks
│   │   ├── services.py        # battle actions that touch the DB (start, answer, finish)
│   │   └── management/commands/seed.py
│   ├── tutor/                 # OpenRouter client, prompt, JSON validation, limits, fallbacks
│   └── abtest/                # A/B page, click endpoint, stats JSON, reset command
├── templates/                 # base.html, game/*.html, partials/*.html, abtest/page.html
├── static/                    # css/ (theme.css = all colors/fonts), js/, img/, CREDITS.md
├── tests/                     # unit + integration tests (pytest)
├── e2e/                       # Playwright tests
├── .github/workflows/ci.yml   # lint + tests on every PR
└── docs/                      # plan.md (this file) + mgt656/ graded docs (§13)
```

App code paths elsewhere in this plan (e.g. `game/rules.py`, `tutor/validate.py`) live under `apps/`. Python imports use the full path (`from apps.game import rules`), but app labels, table names and migrations still use the short name (`game`).

---

## 5. Data model

All models get `created_at` / `updated_at` where useful. Every model change goes through a **migration**.

**Player** (`accounts`): one per `User`
- `user` (OneToOne → `auth.User`)
- `hero`: choice `prince` | `princess`
- `hero_name` (short text, default "Hero")
- `level` (int, default 1), `xp` (int, default 0), `coins` (int, default 0)

> Privacy: kids sign up with a **username + password only**. Don't ask for email, real name, age or birthday. The sign-up page says "Ask a grown-up to help you sign up."

**Stage** (`game`)
- `order` (int, unique), `slug`, `name` (e.g. "Addition Meadow"), `operation`: `add` | `sub` | `mul` | `div` | `mixed`
- `description`, `background_image` (static path)

**Monster** (`game`)
- `stage` (FK), `order` (int within stage), `name`, `image` (static path)
- `max_hp` (int), `attack` (int), `is_boss` (bool)
- `xp_reward`, `coin_reward`
- `question_params` (JSON): tells the generator what to ask (see §6)

**Battle** (`game`)
- `player` (FK), `monster` (FK)
- `player_hp`, `player_max_hp`, `monster_hp`
- `status`: `active` | `won` | `lost` | `fled`
- `xp_awarded`, `coins_awarded`, `started_at`, `ended_at`

**Question** (`game`)
- `battle` (FK), `prompt` (e.g. "7 + 5"), `operand_a`, `operand_b`, `operation`
- `correct_answer` (int): **never sent to the browser**
- `player_answer` (int, nullable), `is_correct` (nullable bool), `answered_at`, `response_ms`
- `damage_dealt`, `damage_taken`

**HintRequest** (`tutor`)
- `player` (FK), `question` (FK), `created_at`
- `status`: `ok` | `fallback` | `limit_reached` | `error`
- `response_json`, `model`, `prompt_tokens`, `completion_tokens`

**ABVisitor** (`abtest`): one row per visitor, holding both the impression and the click
- `visitor_id` (UUID, unique; stored in a cookie)
- `variant`: `kudos` | `thanks`
- `impression_at` (datetime, set once at row creation)
- `clicked_at` (datetime, nullable, set at most once)

**Progress** is derived, not stored separately:
- A monster is *defeated* if the player has a `won` battle against it.
- Monster *n* in a stage unlocks when monster *n−1* is defeated (monster 1 is always unlocked once the stage is unlocked).
- Stage *n* unlocks when the stage *n−1* boss is defeated (stage 1 is always unlocked).

---

## 6. Math content (questions)

All questions are generated by **code**, never by the LLM. `game/generator.py` is a set of pure functions:

```python
generate_question(params: dict, rng: random.Random) -> GeneratedQuestion
# GeneratedQuestion(prompt="7 + 5", a=7, b=5, operation="add", answer=12)
```

Rules:
- Pass `rng` in so tests can use a seeded `random.Random(42)`.
- **Subtraction** answers are never negative (`a >= b`).
- **Division** is built backwards (`answer × divisor = dividend`), so answers are always whole numbers. No remainders in the MVP.
- Avoid repeating the same question twice in a row within one battle.
- Answers are whole numbers, and the answer box uses `inputmode="numeric"` for phone keypads.

**Stage and monster plan** (difficulty roughly follows US Common Core grades 1–4 fluency goals):

| Stage | Monster | `question_params` | ≈ Grade |
|---|---|---|---|
| 1 Addition | 1 Slime | `{"op":"add","max_sum":10}` | 1 |
| | 2 Goblin | `{"op":"add","max_sum":20}` | 1–2 |
| | 3 Troll | `{"op":"add","a_range":[10,99],"b_range":[1,9]}` | 2 |
| | Boss | `{"op":"add","a_range":[10,99],"b_range":[10,99],"max_sum":100}` | 2 |
| 2 Subtraction | 1 | `{"op":"sub","max_a":10}` | 1 |
| | 2 | `{"op":"sub","max_a":20}` | 1–2 |
| | 3 | `{"op":"sub","a_range":[20,99],"b_range":[1,9]}` | 2 |
| | Boss | `{"op":"sub","a_range":[20,100],"b_range":[10,99]}` | 2 |
| 3 Multiplication | 1 | `{"op":"mul","factors":[2,5,10],"other_max":10}` | 3 |
| | 2 | `{"op":"mul","factors":[3,4,6],"other_max":10}` | 3 |
| | 3 | `{"op":"mul","factors":[7,8,9],"other_max":10}` | 3 |
| | Boss | `{"op":"mul","a_range":[2,10],"b_range":[2,10]}` | 3 |
| 4 Division | 1 | `{"op":"div","divisors":[2,5,10],"quotient_max":10}` | 3 |
| | 2 | `{"op":"div","divisors":[3,4,6],"quotient_max":10}` | 3 |
| | 3 | `{"op":"div","divisors":[7,8,9],"quotient_max":10}` | 3 |
| | Boss | `{"op":"div","divisors":[2,3,4,5,6,7,8,9],"quotient_max":10}` | 3 |
| 5 Mixed | 1–3 + Boss | `{"op":"mixed","pool":[...]}`: picks randomly from earlier stages' params | review |

Stretch goal (only if Sprint 4 has room): a "Champion" difficulty toggle for grades 4–5 (multi-digit multiplication, 3-digit ÷ 1-digit).

---

## 7. Battle rules and flow

### Rules (`game/rules.py`, pure functions, fully unit-tested)
- Hero max HP = `100 + 10 × (level − 1)`.
- **Correct answer:** hero deals **20** damage. If the answer comes within **6 seconds**, it's a **critical hit** for 30 damage. Speed is a bonus, never a penalty, because timers stress young kids.
- **Wrong answer:** the monster deals `monster.attack` damage (15 for normal monsters, 20 for bosses). Then show "The answer was **12**" and the **Ask the Wizard** hint button.
- **Monster HP:** 60 / 80 / 100 for normal monsters, 140 for the boss. A battle lasts about 4–8 questions.
- **Win:** award `xp_reward` and `coin_reward`. Level up when `xp >= level × 100` (carry over the extra XP). Show "Level up!" when it happens.
- **Loss:** no penalty. Show "Try again!" with a retry button.
- **Flee:** the player can leave a battle. Status becomes `fled`, with no rewards.
- Coins are only a score counter in the MVP (no shop).

### URL map

| Method | URL | What it does | Login? |
|---|---|---|---|
| GET | `/` | Landing page (log in / sign up) | no |
| GET/POST | `/accounts/signup/` | Create user + Player, choose hero | no |
| GET/POST | `/accounts/login/`, POST `/accounts/logout/` | Django auth views | — |
| GET | `/play/` | World map: stages and monsters, locked/unlocked/defeated | yes |
| POST | `/play/monsters/<id>/battle/` | Start a battle (only if unlocked) → redirect to battle | yes |
| GET | `/battle/<id>/` | Battle screen with the current question | yes (owner only) |
| POST | `/battle/<id>/answer/` | Submit an answer; htmx → returns `partials/battle_state.html`; no-JS → redirect | yes (owner only) |
| POST | `/battle/<id>/hint/` | AI hint for the most recent wrong question; htmx partial | yes (owner only) |
| POST | `/battle/<id>/flee/` | Leave the battle | yes (owner only) |
| GET | `/profile/` | Hero, level, XP bar, coins, accuracy per stage | yes |
| GET | `/f48c8ec`, POST `/f48c8ec/click`, GET `/f48c8ec/stats` | A/B test (§9) | **no** |
| GET | `/admin/` | Django admin (edit stages/monsters, view battles) | staff |

### Answer handling (`game/services.py → answer_question(battle, player_answer)`)
1. Load the battle with `select_for_update()` inside `transaction.atomic()`, then check that it belongs to `request.user` (otherwise **404**) and that `status == active`.
2. Get the current unanswered `Question`. If it's already answered (double-click or resubmit), return the current state without changing anything.
3. Set `player_answer`, `is_correct`, `answered_at`, `response_ms` (measured server-side from question `created_at`).
4. Apply damage with `rules.py`, then check for a win or loss and award XP/coins on a win.
5. If the battle is still active, generate the next `Question`.
6. Return the new state, rendered with the same template for htmx and non-htmx requests.

The correct answer **never** appears in the HTML until after the player answers.

### Battle screen (mobile first)
- Top: monster image, name and HP bar. Middle: hero image and HP bar. Bottom: the big question text, a numeric input with autofocus, and an **Attack!** button.
- After each answer, a one-line message ("Critical hit! −30" or "Ouch! The goblin hits you −15. The answer was 12.").
- The **Ask the Wizard** button appears only after a wrong answer.
- Use CSS transitions for the HP bars (no animation library).

---

## 8. AI tutor ("Ask the Wizard")

**Goal:** after a wrong answer, explain *how* to solve it in kid-friendly words, **without giving away the answer**.

### Call
- Server-side only, in `tutor/client.py`, via `httpx` to OpenRouter's chat completions endpoint.
- Config from env: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` (pick a small, cheap model that supports structured/JSON output), `AI_DAILY_HINT_LIMIT` (default 10), `AI_TIMEOUT_SECONDS` (default 8).
- **No free text from the child ever goes into the prompt.** The prompt is built only from the question (`a`, `b`, `operation`) and the child's numeric answer. That blocks prompt injection and keeps content safe.

### Prompt (outline)
- System: "You are a kind wizard helping a 6–10 year old with math. Use short sentences and simple words. Never state the final answer. Encourage them. Respond only with JSON matching the schema."
- User: `{"question": "7 + 5", "child_answer": 11, "operation": "add"}`

### Required JSON output
```json
{
  "encouragement": "Good try! You're very close.",
  "steps": ["Start at 7.", "Count up 5 more on your fingers: 8, 9, 10...", "What number do you land on?"],
  "strategy": "counting_on"
}
```

### Validation (`tutor/validate.py`); this is the "structured output that drives app behavior" part
- Parse the JSON. Reject it if it isn't JSON, has missing keys, has more than 4 `steps`, or has any step longer than 160 characters.
- `strategy` must be one of a fixed list (`counting_on`, `make_ten`, `count_back`, `skip_count`, `arrays`, `fact_family`, `other`). The app uses it to show a matching picture or icon next to the hint.
- **Reject if the correct answer appears** as a standalone number anywhere in the text (regex `\b{answer}\b`).
- On any rejection, timeout, HTTP error or missing API key, use a **canned fallback hint** for that operation (e.g. "Try making 10 first!"). The game never breaks when the AI is down.

### Usage limits
- Each `HintRequest` row is logged with its token counts.
- Before calling the LLM, count today's hints for the player. At `AI_DAILY_HINT_LIMIT` or more, return a friendly "The wizard is resting until tomorrow" message plus the canned hint, and log `status=limit_reached`.
- Only one hint per question (a repeat request returns the stored hint).

### Tests
- The OpenRouter client is always mocked (`monkeypatch` or `respx`). Tests cover: a valid response, malformed JSON, an answer leaked in the text, a timeout, the limit being reached, and the "only one hint per question" rule.

---

## 9. A/B test page (graded: 10 points, no practice run)

Team nickname: **inner-wrath**, so the path is `/f48c8ec`.
Check: `printf %s inner-wrath | shasum` → starts with `f48c8ec`. Never use `echo`, which adds a newline and gives the wrong hash.

### `GET /f48c8ec`
- Public: **200 without login**, no pop-ups or cookie banners, and not wrapped by any login-required middleware.
- Use a **standalone minimal template** (not `base.html`), so no stray nav buttons appear.
- Lists all team members' **course nicknames** (fill these in; see §14).
- Contains **exactly one** `<button id="abtest">` whose text is exactly `kudos` or `thanks` (lowercase, rendered by the server, no JavaScript).
- Visitor logic:
  1. Read the `ab_vid` cookie. If it's missing or unknown, create an `ABVisitor` with a new UUID and a random variant (`secrets.choice(["kudos","thanks"])`), with `impression_at = now`. **That row creation is the impression.** Set the cookie (1-year max-age, `SameSite=Lax`, `HttpOnly`).
  2. If the cookie matches an existing row, render that row's variant and **record nothing**. Reloads and redirects never count again.
- The button sits inside `<form method="post" action="/f48c8ec/click">{% csrf_token %}…</form>`.

### `POST /f48c8ec/click`
- Look up the visitor by cookie. If it exists and `clicked_at` is null, set `clicked_at = now` (atomic update: `filter(clicked_at__isnull=True).update(...)`).
- Always redirect (303) back to `/f48c8ec`. The redirect must not create a new impression or change the variant (step 2 above guarantees that).
- With no cookie or an unknown visitor, redirect without counting anything.

### `GET /f48c8ec/stats`
- Public JSON, computed live from the database:
```json
{"preferred": "kudos", "kudos": {"impressions": 212, "clicks": 63}, "thanks": {"impressions": 207, "clicks": 21}}
```
- Click rate = clicks / impressions (0 if there are no impressions). `preferred` is the variant with the higher rate; on a tie, return `"kudos"`.

### Before the bot run (after Sprint 4)
- `python manage.py reset_ab --yes` deletes all `ABVisitor` rows. Run it on **production** right before the announced window, because our own test visits count.
- Test it ourselves first: open several private windows, click in some of them, and check that the stats match.

---

## 10. Seed command: `python manage.py seed`

- **Idempotent**: uses `update_or_create` / `get_or_create` everywhere, so it's safe to run any number of times. Run it after every database reset and on every deploy.
- Creates/updates all 5 stages and their monsters from §6.
- Creates grader accounts. Passwords come from **env vars**, never from the repo:

| Kind | Username | Password env var | State |
|---|---|---|---|
| Player (new) | `grader` | `SEED_GRADER_PASSWORD` | Fresh hero, stage 1 only |
| Player (advanced) | `grader-pro` | `SEED_GRADER_PASSWORD` | Stages 1–4 bosses defeated (seeded `won` battles), level 5 |
| Admin | `admin` | `SEED_ADMIN_PASSWORD` | `is_staff` + `is_superuser`, for `/admin/` |

- Use fake data only, no 2FA and no email verification. Use passwords we use nowhere else.
- Submission notes format (paste into each sprint's "Notes" field):
```
Access:
https://<staging-url>/accounts/login/
player: grader / <password>
player (advanced): grader-pro / <password>
admin: admin / <password>   (admin site at /admin/)

Notes:
<anything half-done this sprint>
```

---

## 11. Config, deploy, CI/CD

### Environment variables (`.env.example` lists them all with fake values)
`SECRET_KEY`, `DEBUG` (False in staging/prod), `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `AI_DAILY_HINT_LIMIT`, `AI_TIMEOUT_SECONDS`, `SEED_GRADER_PASSWORD`, `SEED_ADMIN_PASSWORD`.

### 12-factor checklist
- [ ] Settings read from `os.environ`, with **no secrets in git** (`.env` is in `.gitignore`)
- [ ] `DATABASES = {"default": dj_database_url.config(conn_max_age=600)}`
- [ ] `LOGGING` sends everything to the console (stdout)
- [ ] Static files served by whitenoise, with no user uploads
- [ ] `gunicorn mathquest.wsgi --bind 0.0.0.0:$PORT`
- [ ] All schema changes made with migrations

### Render + Neon
- **Neon:** one project with two databases (or branches), `mathquest_staging` and `mathquest_prod`. Each environment gets its own `DATABASE_URL`.
- **Render staging** web service: auto-deploys on every push to `main`.
  - Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
  - Start: `python manage.py migrate --noinput && python manage.py seed && gunicorn mathquest.wsgi --bind 0.0.0.0:$PORT`
- **Render production** web service (Sprint 2): deploys from a `production` branch (or auto-deploy off plus a deploy hook). Promoting means a deliberate step, either merging `main` into `production` or running a manual "Promote to production" GitHub Action that calls the deploy hook.
- Free instances sleep when idle, which is fine (the A/B bot wakes the app first).

### CI (`.github/workflows/ci.yml`)
- Triggers on `pull_request` and pushes to `main`.
- Steps: set up Python, install requirements, `ruff check .`, `ruff format --check .`, `pytest` against a **Postgres service container**.
- The Playwright job installs Chromium and runs `pytest e2e/` (Sprint 4).
- Branch protection on `main`: require the CI checks to pass and 1 teammate review before merging.

### Testing strategy (goes into `docs/mgt656/technical.md`)
- **Unit:** `generator.py` (seeded RNG, answer correctness, no negatives, whole-number division), `rules.py` (damage, crits, level-up, unlocks), `tutor/validate.py`.
- **Integration (Django test client):** sign-up/login, battle start permissions (locked monster → 403/404, someone else's battle → 404), answering (correct/wrong/double submit), hint endpoint with a mocked LLM, A/B page counting (new visitor, reload, click, second click, click redirect), stats JSON, seed idempotency (run twice → same counts).
- **E2E (Playwright):** sign up → pick a hero → win a stage 1 battle (the test reads correct answers from the test DB), plus A/B: new browser context = new visitor, impressions/clicks counted once.
- **Mocked:** OpenRouter, always. **Not tested:** visual styling and the real LLM's wording quality (we check its structure, not its content).

---

## 12. Sprint plan and backlog

GitHub Project setup (Sprint 1): one Project linked to the repo, an **Iteration** field with 4 iterations dated to the deadlines, and the built-in workflows on ("auto-add new issues", "item closed → Done").

| Iteration | Dates | Deadline (11:59pm ET) |
|---|---|---|
| Sprint 1 | Nov 3 – Nov 11 | Wed Nov 11 |
| Sprint 2 | Nov 12 – Nov 18 | Wed Nov 18 |
| Sprint 3 | Nov 19 – Dec 2 | Wed Dec 2 |
| Sprint 4 | Dec 3 – Dec 11 | Fri Dec 11 (then A/B run on prod) |
| Final | — | Fri Dec 18: final submission + retrospective |

Every backlog item is a GitHub issue labeled **`user story`**, in the form "As a …, I want …, so that …" with acceptance criteria. The criteria must be precise enough to hand to Cursor, because they are its spec. Split bigger stories into **sub-issues**.

Sprint rules:
- **At the start of each sprint**, put the stories we commit to in that sprint's iteration on the board.
- Unfinished stories move to the next iteration; **never delete them**.
- Milestones are optional and only for product goals that span sprints (e.g. "MVP"), **not** for sprints.
- **No** story points, velocity or burndown charts.

**Submitting every sprint (one teammate submits on the course site, as a team assignment):**
- [ ] Repo URL
- [ ] Staging URL
- [ ] Production URL (Sprint 2 onward; the A/B run uses this one)
- [ ] Notes in the format from §10: login page plus a username and password for each kind of user, and anything half-done. Grader accounts must work on **both** staging and production.
- [ ] Sprint report committed to `main` in the repo (it does **not** go in the notes)

### Sprint 1: Walking skeleton (due Wed Nov 11)
**Goal:** the whole pipeline works end to end on staging. No game yet.

Course checklist for Sprint 1: framework app with user accounts, connected to Postgres, deployed to **staging** · seed command creates the grader accounts · A/B page and `/f48c8ec/stats` work on staging · first user stories in the backlog, plus a GitHub Project with iterations for **all four** sprints · `team.yaml` and `sprint-1.md` on `main`. Production can wait until Sprint 2. Graded on: the skeleton working on staging, the report, and the backlog.

- **S1-1: Project skeleton.** As a developer, I want a Django project wired to Postgres via `DATABASE_URL`, so that every environment is configured the same way.
  - AC: `mathquest` project plus `accounts`, `game`, `tutor` and `abtest` apps exist; settings come from env; `.env.example` exists; `ruff` passes; `pytest` runs (with at least one smoke test); README explains local setup.
- **S1-2: Accounts.** As a player, I want to sign up, log in and log out with a username and password, so that my progress is saved.
  - AC: sign-up creates a `User` + `Player` (hero choice prince/princess); no email field; login/logout work; a logged-in player sees a placeholder `/play/` page; logged-out users are redirected to login; tests cover sign-up and login.
- **S1-3: Deploy to staging.** As a grader, I want a public staging URL, so that I can check our work.
  - AC: Render staging service connected to the Neon staging DB; `DEBUG=False`; migrations run on deploy; the site loads at the public URL.
- **S1-4: Seed command.** As a grader, I want ready-made accounts, so that I can log in immediately.
  - AC: `python manage.py seed` creates `grader` and `admin` from env passwords; running it twice doesn't duplicate anything (test); it runs on staging.
- **S1-5: A/B test page + stats.** As the course bot, I want `/f48c8ec` and `/f48c8ec/stats` to follow the spec in §9, so that the A/B experiment is measured correctly.
  - AC: every bullet in §9, with tests for: first visit = 1 impression; reload = no new impression; click = 1 click; second click = still 1; click redirect = no new impression and same variant; stats JSON shape and `preferred` logic.
- **S1-6: Project management setup.** As a team, we want a GitHub Project with 4 iterations and a starting backlog (§12 stories as issues), so that the work is planned.
- **S1-7: Docs.** `docs/mgt656/team.yaml` and `docs/mgt656/sprints/sprint-1.md` on `main`.

### Sprint 2: First playable battle + production + AI started (due Wed Nov 18)
**Goal:** a kid can beat Stage 1 monsters on staging, production exists with its own database, and the AI tutor is started.

Course checklist for Sprint 2: production deployed with its own DB · first user stories shipped through **reviewed pull requests** · **AI feature started** · `sprint-2.md` on `main`.

- **S2-1: Production environment.** Render prod service + Neon prod DB, with a deliberate promote step; seed runs on prod.
- **S2-2: Question generator (add/sub).** As a player, I get addition questions that match each monster's difficulty. AC: unit tests with a seeded RNG for every Stage 1–2 param set.
- **S2-3: Battle rules.** `rules.py` with damage, crits, win/loss, all unit-tested.
- **S2-4: Battle flow (Stage 1).** As a player, I can start a battle against an unlocked Stage 1 monster, answer questions, and win or lose. AC: §7 answer handling, owner-only access, double-submit safe, correct answer hidden until answered.
- **S2-5: World map.** As a player, I see stages and monsters marked locked/unlocked/defeated, and can only battle unlocked ones.
- **S2-6: CI.** GitHub Actions runs ruff + pytest with Postgres on every PR; branch protection on `main`.
- **S2-7: AI tutor, first slice (required: "AI feature started").** As a player who got an answer wrong, I can tap **Ask the Wizard** and get a hint. AC: `tutor/client.py` calls OpenRouter server-side with the key from env; `tutor/validate.py` checks the JSON (§8) and falls back to a canned hint on any failure; `POST /battle/<id>/hint/` works on staging; tests mock OpenRouter (valid, malformed, timeout). The answer-leak check, daily limit and strategy icons come in Sprint 3.
- **S2-8: Docs.** `sprint-2.md`.

### Sprint 3: Full game + AI tutor (due Wed Dec 2)
**Goal:** all stages are playable, the AI tutor works, battles feel live, and **every** technical-challenge item has started.

Course checklist for Sprint 3: core features **and** the AI feature work on staging · technical-challenge items started **and listed in `technical.md`** · `sprint-3.md` on `main`.

- **S3-1: Stages 2–4 (sub, mul, div).** Generator params + seed data for all monsters in §6.
- **S3-2: XP, coins, level-up, stage unlocks.** Rewards on a win, a "Level up!" message, the next stage unlocking after a boss win.
- **S3-3: Live battles with htmx.** As a player, my answer updates the HP bars and question without a full page reload. AC: htmx partial for answer/hint; still works with JS off (form POST + redirect); tests for both paths.
- **S3-4: AI tutor complete ("Ask the Wizard").** Finish everything in §8 on top of the Sprint 2 slice: answer-leak check, `strategy` driving the hint icon, one hint per question, kid-safe prompt, plus mocked tests for each.
- **S3-5: Daily AI hint limit.** `AI_DAILY_HINT_LIMIT` enforced per player, with a friendly message when it's reached.
- **S3-6: CD.** Merge to `main` → staging deploy (already on); add the "Promote to production" step and document it.
- **S3-7: Hero art + mobile layout.** CC0 hero/monster images, a battle screen usable on a phone, and `CREDITS.md`.
- **S3-8: Playwright started.** Set up `pytest-playwright` and one E2E test: the A/B page in fresh browser contexts (impression counted once, click counted once). The full battle E2E and running it in CI come in Sprint 4.
- **S3-9: Docs.** `sprint-3.md`, plus `technical.md` listing **all four** technical-challenge items with their current status, main files and PRs.

### Sprint 4: Polish, mixed stage, E2E (due Fri Dec 11)
**Goal:** a polished MVP on production, ready for the A/B run.

Course checklist for Sprint 4: all features and technical-challenge items **finished and on production** (not just staging) · `technical.md` **complete** · `sprint-4.md` on `main`.

- **S4-1: Stage 5 Mixed.** Mixed-operation monsters and boss.
- **S4-2: Profile page.** Hero, level, XP bar, coins, accuracy per stage (from `Question` rows).
- **S4-3: Playwright E2E complete.** Sign up → win a battle, plus the A/B test from S3-8; runs in CI.
- **S4-4: Advanced grader account.** `grader-pro` seeded with stages 1–4 cleared.
- **S4-5: A/B run readiness.** `reset_ab` command, a manual check on prod, then reset right before the announced window.
- **S4-6: Promote everything to production.** Run the promote step, then check every feature and every grader login on the production URL.
- **S4-7: Docs.** `sprint-4.md` and the final `technical.md`. For each item: what it is, main file paths + PRs, how to see it working, then the testing strategy (what we test at each level, what we mock, what we don't test and why).

**Production freeze for the A/B run:** after the Sprint 4 deadline, the bot runs against production during an announced window of a few hours. **Keep production up and unchanged through that window**: no promotes, no env var changes, no DB resets. Run `reset_ab` before the window starts, read `/f48c8ec/stats` afterwards, and only then resume deploys. Staging deploys from `main` can continue.

### Final (due Fri Dec 18)
- `retrospective.md` (~half a page): what went well, what we'd do differently, and **how our way of working with AI agents changed** over the project.
- Final submission on the course site: repo, staging and production URLs, plus notes.

---

## 13. `docs/mgt656/` folder (graded from `main` at each deadline)

```
docs/mgt656/
  team.yaml
  technical.md         # each technical-challenge item: what, main files + PRs, how to see it; testing strategy
  sprints/
    sprint-1.md ... sprint-4.md
    img/               # screenshots only; link to videos rather than committing them
  retrospective.md     # final: what went well, what we'd do differently, how our AI-agent workflow changed
```

Never put passwords or keys anywhere in the repo, docs included.

`team.yaml`:
```yaml
framework: django
database: postgres
members:
  - nickname: blushing-leopard   # Phuong Vu
    github: TODO
  - nickname: TODO               # Alison Liu
    github: TODO
  - nickname: TODO               # Gina Moon
    github: TODO
  - nickname: TODO               # Jung Tae Ji
    github: TODO
  - nickname: TODO               # Shixuan Sun
    github: TODO
```

**Sprint report template** (~half a page each):
```markdown
# Sprint N
## Goal
## What shipped
- <story> — #<issue>, PR #<pr>
## What works on staging now
## Working with our AI agents
One concrete thing that worked or didn't, and what we changed.
## Backlog changes for next sprint
```

---

## 14. Open items to fill in

- [ ] Course nicknames + GitHub usernames for Alison, Gina, Jung Tae and Shixuan (needed for `team.yaml` **and** the A/B page member list)
- [ ] Repo URL, staging URL and (Sprint 2) production URL
- [ ] OpenRouter key from Kyle → Render env vars (staging + prod), never in git
- [ ] Pick the OpenRouter model and set `OPENROUTER_MODEL`
- [ ] Choose CC0 art packs and record them in `static/CREDITS.md`

---

## 15. Team working rules (Cursor + GitHub)

1. **One story = one branch = one PR.** Branch names look like `s2-4-battle-flow`.
2. Each PR description includes `Closes #<issue>`, **what the agent produced**, and **what we changed or rejected**. Kyle grades this.
3. A teammate reviews every PR before it merges. CI must be green.
4. Give Cursor the story's acceptance criteria as its spec, and ask it to **write tests first** for `generator.py`, `rules.py`, `tutor/validate.py` and the A/B views.
5. Never commit secrets, `.env` or real passwords. Grader passwords live only in Render env vars and the submission notes.
6. Never call the real OpenRouter from tests.
7. Don't let the agent add packages, a JS framework or a game engine without the team agreeing first.
8. Keep `main` deployable, since staging auto-deploys from it.
