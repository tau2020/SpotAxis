# Running SpotAxis locally

Verified from scratch on macOS (Apple Silicon); Linux differences are noted.

## 1. Prerequisites

| Tool | Version | Why |
| --- | --- | --- |
| Python | 3.12+ | `pyproject.toml` requires `>=3.12`; `.python-version` pins 3.12. |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | 0.7+ | Dependency install and lockfile. |
| PostgreSQL | 16+ | The application database. Homebrew, Docker, or any local install. |
| Pango / GLib / cairo / gdk-pixbuf | — | Native libraries WeasyPrint loads at import time for PDF export. |

```bash
# macOS
brew install uv postgresql@16 pango gdk-pixbuf libffi
brew services start postgresql@16

# Debian / Ubuntu
sudo apt install postgresql libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfontconfig1 libcairo2 libgdk-pixbuf-2.0-0
```

Docker alternative for the database:

```bash
docker run -d --name spotaxis-postgres -e POSTGRES_USER=spotaxis -e POSTGRES_PASSWORD=spotaxis \
  -e POSTGRES_DB=spotaxis -p 5432:5432 postgres:16
# then set DATABASE_URL=postgres://spotaxis:spotaxis@localhost:5432/spotaxis in .env
```

## 2. Environment

```bash
cp .env.example .env
python3 -c "from secrets import token_urlsafe; print(token_urlsafe(50))"   # paste as SECRET_KEY
```

Everything is driven by environment variables (see `.env.example`). The ones that matter locally:

- `DATABASE_URL` — defaults to `postgres://localhost:5432/spotaxis`.
- `SITE_SUFFIX=.spotaxis.localhost:8010/` — company careers sites live at `<slug>.spotaxis.localhost:8010`; the host part is the main site. **The port must match the port you run the server on.**
- `EMAIL_BACKEND` — console backend prints all mail to the terminal.

No `/etc/hosts` edit is needed: macOS and Linux resolve `*.localhost` to 127.0.0.1.

## 3. Install and initialise

```bash
uv sync --group dev                      # creates .venv with app + dev dependencies
createdb spotaxis                        # or use the Docker container above
uv run python manage.py migrate
PATH="$PWD/.venv/bin:$PATH" bash loaddata_from_apps.sh   # countries, currencies, degrees, plans, ...
uv run python manage.py createsuperuser
```

## 4. Run

```bash
uv run python manage.py runserver 8010
```

| URL | What |
| --- | --- |
| http://spotaxis.localhost:8010/ | Main site / job board |
| http://spotaxis.localhost:8010/jobs/ | Public job search |
| http://spotaxis.localhost:8010/login/ | Login (use the **username**, not the email) |
| http://spotaxis.localhost:8010/signup/talent/ | Candidate signup |
| http://spotaxis.localhost:8010/signup/employer/ | Employer signup |
| http://spotaxis.localhost:8010/admin/ | Django admin |
| http://spotaxis.localhost:8010/healthz | Health check (JSON) |
| http://&lt;slug&gt;.spotaxis.localhost:8010/ | A company careers site and its recruiter dashboard |

`http://localhost:8010/` returns 404 on purpose: the host must be the main host or a registered company subdomain. New accounts land inactive; the activation link is printed to the terminal by the console email backend.

Sessions are per host, so log in to a company on **its** subdomain.

## 5. Checks

```bash
uv run ruff check .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest -q
```

Pre-commit hooks (ruff, whitespace, private-key detection):

```bash
uv run pre-commit install
```

## 6. Scheduled tasks

There is no worker process. Periodic work (publishing/unpublishing jobs on their scheduled dates) runs through `python manage.py run_tasks`, or over HTTP with `POST /internal/tasks/run` and `Authorization: Bearer $TASK_RUNNER_TOKEN`. In production a GitHub Actions schedule calls the endpoint every five minutes (`.github/workflows/scheduled-tasks.yml`).

## 7. Docker

```bash
docker build -t spotaxis .
docker run --rm -p 8000:8000 -e DATABASE_URL=postgres://host.docker.internal:5432/spotaxis \
  -e SECRET_KEY=dev -e DEBUG=true -e SITE_SUFFIX=.spotaxis.localhost:8000/ spotaxis
```

The image runs migrations on start and serves with gunicorn; static files are collected at build time and served by WhiteNoise.

## 8. Known limitations (pre-existing)

- **Uploaded files are stored on local disk** (`./media`). Object storage arrives in Phase 1 of the MVP plan.
- **Third-party integrations are inert**: social login, social sharing and PayPal checkout were removed or disabled; billing returns post-MVP.
- **Superuser without a profile**: logging a bare superuser into the front-end `/login/` form 500s at `/redirect/`. Use `/admin/` for the superuser and a recruiter/candidate account for the app.
- **Generated careers-site links use the port in `SITE_SUFFIX`**; change both together.
