
# Sprint 2 Report: First Playable Game

## Sprint goal

Deploy the production app with a separate database, replace the placeholder game page with playable Stage 1 math battles, and start developing the AI tutor.

## What shipped

- Production deployment: a separate production environment on Render with a manual promotion workflow from `main` to the `production` branch ([Issue #12](https://github.com/crazymidget000/Math-App/issues/12), [PR #20](https://github.com/crazymidget000/Math-App/pull/20)).
- Math question generator: addition and subtraction questions based on each monster's difficulty settings ([Issue #13](https://github.com/crazymidget000/Math-App/issues/13), [PR #22](https://github.com/crazymidget000/Math-App/pull/22)).
- Core battle rules: damage calculations, critical hits, win/loss conditions, and level-ups ([Issue #14](https://github.com/crazymidget000/Math-App/issues/14), [PR #23](https://github.com/crazymidget000/Math-App/pull/23)).
- Playable Stage 1 battles: players can fight monsters by answering math questions, earn XP and coins, and unlock new monsters ([Issue #15](https://github.com/crazymidget000/Math-App/issues/15), [PR #24](https://github.com/crazymidget000/Math-App/pull/24)).
- World map: displays locked, unlocked, and defeated monsters and tracks player progression ([Issue #16](https://github.com/crazymidget000/Math-App/issues/16), [PR #26](https://github.com/crazymidget000/Math-App/pull/26)).
- AI tutor: the Ask the Wizard feature provides hints after incorrect answers using server-side OpenRouter integration, with predefined hints as a fallback ([Issue #18](https://github.com/crazymidget000/Math-App/issues/18), [PR #25](https://github.com/crazymidget000/Math-App/pull/25)).

## What currently works on staging

Staging URL: https://mathquest-staging.onrender.com/

Production URL: https://math-app-oyy0.onrender.com/

- Grader accounts work on both staging and production.
- Players can access the game through `/play/`, battle unlocked monsters, and answer math questions.
- Players can earn XP and coins and unlock new monsters by winning battles.
- The world map displays monster availability and player progression.
- The Ask the Wizard feature provides hints after incorrect answers.

Production uses a dedicated PostgreSQL database separate from staging. The manual promotion process is documented in the README.

Login details for the grader accounts are provided in the assignment submission, not in this repository.

## Testing

Automated tests were conducted for the question generator, battle rules, battle flow, and AI tutor. The AI tutor PR reported 124 passing tests and 37 passing subtests using PostgreSQL.

During manual QA, we encountered a server error and an issue with Stage 1 being locked. The team fixed these issues and verified that the game worked with the grader player account. The team also verified that the AI tutor displayed hints.

## Working with AI agents

During the development of the AI tutor, we used one AI agent to implement the feature and another to independently review the code. The reviewing agent identified invalid Unicode and database connection issues that the implementing agent had missed.

We fixed these issues and reran the tests. Using separate agents for implementation and review helped us identify problems that a single agent had overlooked.

## Team contributions

- BlackCloud0x: production deployment workflow and documentation.
- crazymidget000: question generator, core battle rules, playable Stage 1 battles, and deployment fixes.
- jaminii5959: world map and player progression.
- Shawnsun0813: AI tutor development and testing.
- jungtaeji: sprint documentation, manual QA, GitHub Project updates, and submission.

## Backlog changes for Sprint 3

- CI and branch protection were not completed during Sprint 2 and have been moved to Sprint 3 ([Issue #17](https://github.com/crazymidget000/Math-App/issues/17)).
- Remaining AI tutor features, including answer-leak detection, daily usage limits, and strategy icons, are planned for Sprint 3.
