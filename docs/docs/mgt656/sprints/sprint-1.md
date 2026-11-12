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

One concrete example came from verifying the seed command on staging. After finishing the seed command and opening PR #11, team used ChatGPT to draft a handoff message for the teammate who manages Render. The message listed exact steps: set `SEED_ADMIN_PASSWORD` and `SEED_PLAYER_PASSWORD`, run `python manage.py seed` twice to check that no duplicates are created, and confirm both grader accounts can log in.

What worked: the checklist was specific and complete, and the teammate who owns the Render deployment (Phuong Vu) followed it and reported that the seed worked and both grader accounts could log in.

What did not work: the message was full of jargon (environment variables, running a management command), and the teammate who sent it said they did not understand what it meant, so they could not judge whether it was correct before sending it.

What the team changed: the person who owns the deployment ran the steps and posted the actual results (which account lands where, what each page shows) in the team chat, so the team verified against real behavior instead of trusting the AI-written steps. We will keep asking AI to explain its instructions in plain language, and we will confirm results on staging ourselves before checking off an issue.

## Backlog changes for Sprint 2

- All Sprint 1 user stories (#3 through #9) are closed.
- Added for Sprint 2: the actual math game on `/play/`, replacing the placeholder.
- Added for Sprint 2: production deployment.
- Carried forward: the AI tutor, already configured as a placeholder in `.env.example`, is planned for Sprint 2 or later.
