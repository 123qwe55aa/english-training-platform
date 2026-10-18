# Hello, Friends · English Training Platform

A teacher-led English learning platform with custom courses, learner progress, classroom replays, media materials, and an agent-friendly teacher workflow. The example interface uses a golden retriever, a border collie, and Grandpa.

## Features

- Public, read-only learner pages controlled by teacher publication settings.
- Staff-only editing through Django admin.
- Student-specific plans, completed classes, lesson mastery, recordings, rewards, and badges.
- Reusable courses with structured text, video, audio, picture-book, PDF, dialogue, and quiz blocks.
- Agent CLI for discovering tools, preparing lessons, importing materials, recording teacher-confirmed progress, and awarding points. There is no public write API or embedded chat assistant.
- SQLite and uploaded media stored outside the source tree.

## Local setup

Use Python 3.12 and install `requirements.txt`. Set a local-only `SECRET_KEY`, then run:

```sh
python manage.py migrate
python manage.py runserver
```

Run Django tests with `SECRET_KEY=test-only python manage.py test` and browser-module tests with `node --test tests/*.test.mjs`.

## Container deployment

`docker-compose.yml` is the standalone deployment with Django, Nginx, and Caddy. For an existing reverse proxy managed elsewhere, Coolify can use [`deploy/coolify.compose.yml`](deploy/coolify.compose.yml); configuration is documented in [Coolify deployment](docs/coolify-deployment.md). Set secrets through the deployment environment and mount database/media storage from a persistent host path. Never commit `.env`, SQLite databases, uploaded files, recordings, or backups.

See [architecture](docs/architecture.md), [teacher workflow](docs/teacher-workflow.md), and [agent tools](docs/agent-tools.md) for the application boundaries and usage.
