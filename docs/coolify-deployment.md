# Coolify deployment

This repository includes `deploy/coolify.compose.yml` for a Coolify Docker Compose resource. It runs Django and the Nginx gateway while allowing an existing reverse proxy to remain outside the resource.

Configure these resource variables in Coolify:

- `ENGLISH_PLATFORM_ENV_FILE`: the absolute path to the existing app's protected `.env` file on the target server. This keeps its Django secret in place rather than copying it into the Coolify UI.
- `ENGLISH_PLATFORM_STORAGE`: an absolute persistent-data directory on the target server. Back up the SQLite database and media before changing this path.
- `BUILD_PIP_INDEX_URL`: optional package index; defaults to PyPI.

The existing env file supplies `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS`; add `CSRF_TRUSTED_ORIGINS` there only if the deployment needs cross-origin administrative requests.

Select the compose file path `deploy/coolify.compose.yml`. The gateway publishes only `127.0.0.1:8080`; configure the host reverse proxy to pass HTTP traffic to that port. The app, database, and media remain on the target server. Do not add the database or uploaded media to Git.

Before taking over an existing installation, create and verify a backup, compare the application migration history, rehearse migrations on an isolated restored copy, and check that the existing reverse proxy continues to own public ports 80 and 443. The compose file intentionally contains no `down` or storage deletion operation.

The agent CLI uses an existing SSH identity and requires `ENGLISH_PLATFORM_SSH_TARGET` (for example `user@server`) and `ENGLISH_PLATFORM_REMOTE_DIR` in the local environment. It does not contain a host address or credential.
