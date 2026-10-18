# Hello, Friends — English Learning Platform

A teacher-led English learning platform built as a Django monolith. It supports public student learning pages, private teacher editing, reusable courses and materials, student-specific progress/rewards, session recordings, and a Codex-friendly JSON management interface. The interface uses original golden retriever, border collie, and Grandpa illustrations.

## Run with containers

Requirements: Docker Engine with the Compose plugin.

```sh
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
# Put the generated value in SECRET_KEY in .env before startup. The sample uses DEBUG=true for local HTTP; set DEBUG=false for a public deployment.
docker compose build
docker compose run --rm app python manage.py migrate
docker compose run --rm app python manage.py collectstatic --noinput
docker compose run --rm app python manage.py createsuperuser
docker compose up -d
```

Open `http://localhost:8080/`. The first visit has no learner data; create students, courses, lessons and materials from `/admin/`. Data, uploaded media and collected static files persist in the `app_data` Docker volume. Use `docker compose down` to stop the stack; do not add `-v` unless you intend to delete that volume.

For a public domain with automatic HTTPS, set `SITE_DOMAIN`, `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in `.env`, point DNS to the host, then run `docker compose --profile public up -d`. Ensure ports 80 and 443 are reachable. TLS and certificate storage are managed by Caddy. The app container is not directly published; Nginx serves static assets and guards media paths.

## Architecture

See [architecture and data boundaries](docs/architecture.md), [teacher workflow](docs/teacher-workflow.md), and [Codex tools](docs/agent-tools.md).

## Codex skill

The reusable skill source is [`skills/english-teaching-platform/SKILL.md`](skills/english-teaching-platform/SKILL.md). From this repository, install it with your Codex skill manager or copy that folder into your Codex skills directory. The skill never contains deployment credentials or a personal host. For remote operations, configure `ENGLISH_PLATFORM_SSH_HOST` and `ENGLISH_PLATFORM_REMOTE_DIR` in your private shell environment; for local development, use `--local`.

## Privacy and content

Do not commit `.env`, database files, uploaded recordings, student work, teacher evidence, backups, or private audit exports. Public pages may expose any student/material you deliberately publish; teacher notes and evidence should remain private. Third-party course scripts, videos, audio and trademarks remain subject to their respective owners' terms.

## License

Application code and original illustrations are released under the MIT License. This does not grant rights to third-party learning materials or uploaded learner recordings.
