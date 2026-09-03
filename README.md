# Nimbus Hire

Nimbus Hire is an Applicant Tracking System built on the open-source (MIT licensed) SpotAxis codebase: organizations post jobs on a hosted careers site, candidates apply, and hiring teams move applicants through a pipeline with notes, ratings, interviews and notifications.

The project is being reworked into a lean, low-cost SaaS MVP. The assessment, target architecture, migration plan and roadmap are in [`docs/MVP_ARCHITECTURE_PLAN.md`](docs/MVP_ARCHITECTURE_PLAN.md).

## Stack

- Python 3.12, Django 5.2 (modular monolith, server-rendered templates)
- PostgreSQL 16
- gunicorn + WhiteNoise, packaged with the `Dockerfile`; deployed on Railway
- GitHub Actions for CI (ruff, Django checks, pytest, Docker build) and for the scheduled task ping

## Getting started

See [`LOCAL_DEVELOPMENT.md`](LOCAL_DEVELOPMENT.md) for a verified from-scratch setup. In short:

```bash
cp .env.example .env            # then set SECRET_KEY
uv sync --group dev
createdb spotaxis
uv run python manage.py migrate
uv run python manage.py seed_reference_data
uv run python manage.py runserver 8010
```

Open http://spotaxis.localhost:8010/. Company careers sites live at `http://<slug>.spotaxis.localhost:8010/`.

## Deployment

The app is a single container. Required environment variables in production:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django secret (required when `DEBUG` is off) |
| `DATABASE_URL` | PostgreSQL connection string |
| `SITE_SUFFIX` | e.g. `.spotaxis.com/`; the host part is the main site, companies get `<slug>` subdomains |
| `MAIN_HOSTS` | Extra hosts that should serve the main site (e.g. the Railway domain) |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | SMTP settings |
| `TASK_RUNNER_TOKEN` | Bearer token for `POST /internal/tasks/run` |
| `SENTRY_DSN` | Optional error reporting |

`railway.json` configures the Docker build and the `/healthz` health check.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Run `uv run ruff check .` and `uv run pytest` before opening a pull request; CI enforces both.

## License

MIT. See [`LICENSE`](LICENSE).
