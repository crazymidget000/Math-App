# Sprint 1 Report: Walking Skeleton

## Sprint goal

Get the whole pipeline working end to end before building real features: a Django app with user accounts, connected to PostgreSQL and deployed to staging, with a seed command that creates the grader accounts, the A/B test page and stats, and a backlog with a team GitHub Project set up for all four sprints.

## What shipped

- Framework and database setup: Django app connected to PostgreSQL ([Issue #3](https://github.com/crazymidget000/Math-App/issues/3))
- User accounts: sign up, log in, log out, and a placeholder `/play/` page ([Issue #4](https://github.com/crazymidget000/Math-App/issues/4))
- Staging deployment on Render ([Issue #5](https://github.com/crazymidget000/Math-App/issues/5))
- Seed command that creates the grader accounts ([Issue #6](https://github.com/crazymidget000/Math-App/issues/6), [PR #11](https://github.com/crazymidget000/Math-App/pull/11))
- A/B test page and statistics ([Issue #7](https://github.com/crazymidget000/Math-App/issues/7), [PR #10](https://github.com/crazymidget000/Math-App/pull/10))
- GitHub Project and product backlog with iterations for all four sprints ([Issue #8](https://github.com/crazymidget000/Math-App/issues/8))
- Team documentation and this sprint report ([Issue #9](https://github.com/crazymidget000/Math-App/issues/9)): `docs/mgt656/team.yaml` and `docs/mgt656/sprints/sprint-1.md`

## What currently works on staging

Staging URL: https://mathquest-staging.onrender.com/

- The home page loads and links to sign up and log in.
- Sign up, log in, and log out work with the PostgreSQL database.
- The seed command (`python manage.py seed`) was run on staging and created the grader accounts. Passwords come from the `SEED_ADMIN_PASSWORD` and `SEED_PLAYER_PASSWORD` environment variables set on Render, not from the repository.
- The `grader` player account logs in and lands on `/play/`, which shows a fresh hero (Level 1, 0 XP, 0 coins), as the plan requires.
- The `admin` account logs in to `/admin/`, where the Players are listed.
- The A/B test page is at `/f48c8ec`, with statistics at `/f48c8ec/stats`.

Login details for the grader accounts are in the "notes to user" field of the assignment submission, not in this repository.

Known limitations: the game itself is not built yet, so `/play/` is a placeholder. Production is not deployed; it is planned for Sprint 2. Staging runs on Render and may take a short time to wake up on the first request.

## Working with AI agents

One concrete example came up around secrets. While building the seed command, AI tool suggested putting the grader passwords directly in the code so the accounts would work immediately. This would have committed passwords to the repository, which breaks our rule that no passwords or API keys go in the repo.

What worked: the AI's code ran and created the accounts as asked, and teammate caught the problem during review before it was merged to `main`.

What did not work: the AI chose convenience over security. It did not warn us that hardcoded credentials stay in the Git history and are visible to anyone with repo access, even if they are deleted later.

What the team changed: we moved the secrets into environment variables. The seed command now reads `SEED_ADMIN_PASSWORD` and `SEED_PLAYER_PASSWORD`, which are set in Render instead of stored in the code, and `.env.example` contains only placeholder values (for example `OPENROUTER_API_KEY=sk-or-fake-key`). We also check AI-generated changes for hardcoded secrets before merging them.

## Backlog changes for Sprint 2

- All Sprint 1 user stories (#3 through #9) are closed.
- Added for Sprint 2: the actual math game on `/play/`, replacing the placeholder.
- Added for Sprint 2: production deployment.
- Carried forward: the AI tutor, already configured as a placeholder in `.env.example`, is planned for Sprint 2 or later.
