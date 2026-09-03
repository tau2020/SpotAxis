# Running SpotAxis locally

A verified, from-scratch local setup. Everything below was run end to end on
macOS (Apple Silicon); the Linux notes are called out where they differ.

## 1. Prerequisites

| Tool | Version | Why |
| --- | --- | --- |
| Python | 3.12+ | `pyproject.toml` requires `>=3.12` (Django 5.2). `.python-version` pins 3.12. |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | any recent | Dependency install, per `installguide.md`. |
| Docker | any recent | Runs MySQL. Skip if you already have MySQL **8.4+** locally. |
| Pango / GLib / cairo / gdk-pixbuf | — | Native libraries WeasyPrint loads at import time. Without them Django will not even start. |

MySQL **8.4 or newer** is required — Django 5.2 refuses to connect to 8.0.

Install the native libraries:

```bash
# macOS
brew install uv pango gdk-pixbuf libffi

# Debian / Ubuntu
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfontconfig1
```

## 2. Environment setup

```bash
cd SpotAxis
cp .env.example .env
```

Then put a real key in `.env` (the placeholder is deliberately not a valid secret):

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

`.env.example` ships safe local placeholders only — no production hosts, no real
credentials. The values that matter:

- `ENVIRONMENT='local_development'` turns `DEBUG` on.
- `site_suffix='.spotaxis.localhost:8010/'` — **the port must match the port you
  run the server on.** `TRM.middleware.SubdomainMiddleware` returns 404 for any
  host that is neither a registered company subdomain nor the host part of
  `site_suffix`, and the company / vacancy models build their public URLs from
  this same value.
- `email_backend` is Django's console backend, so signup and notification mail is
  printed to the `runserver` terminal instead of needing an SMTP account.
- Every third-party credential (PayPal, LinkedIn, Facebook, …) is blank. Nothing
  in the local flow needs them.

No `/etc/hosts` edit is needed: macOS and Linux both resolve `*.localhost` to
127.0.0.1, so `spotaxis.localhost` and `<company>.spotaxis.localhost` work as-is.
The middle label has to stay `spotaxis`, because `TRM.settings.ROOT_DOMAIN` is
hardcoded to `"spotaxis"` per environment.

## 3. Install

```bash
uv venv --python 3.12
uv pip install -r pyproject.toml
```

Activate with `source .venv/bin/activate`, or prefix commands with
`.venv/bin/python` as shown below.

## 4. Start the database

```bash
docker run -d --name spotaxis-mysql \
  -e MYSQL_ROOT_PASSWORD=spotaxis_root \
  -e MYSQL_DATABASE=TRM_local \
  -e MYSQL_USER=TRM_user \
  -e MYSQL_PASSWORD=spotaxis_local_pass \
  -p 3307:3306 \
  mysql:8.4
```

Port 3307 keeps it clear of any MySQL already on 3306. Wait for it to accept
connections, then create the schema and load the reference data:

```bash
until docker exec spotaxis-mysql mysqladmin ping -h127.0.0.1 -uroot -pspotaxis_root >/dev/null 2>&1; do sleep 1; done

.venv/bin/python manage.py migrate
PATH="$PWD/.venv/bin:$PATH" bash loaddata_from_apps.sh   # countries, currencies, plans, ...
.venv/bin/python manage.py createsuperuser
```

Only if you intend to run the test suite, also let the app user create test
databases:

```bash
docker exec -i spotaxis-mysql mysql -uroot -pspotaxis_root \
  -e "GRANT ALL PRIVILEGES ON \`test\_%\`.* TO 'TRM_user'@'%'; FLUSH PRIVILEGES;"
```

Restart later with `docker start spotaxis-mysql`.

## 5. Run SpotAxis

```bash
.venv/bin/python manage.py runserver 8010
```

Use 8010 (or change it in **both** the command and `site_suffix`). Port 8000 is a
common collision on a developer machine, and a mismatched `site_suffix` makes
every page 404 through the subdomain middleware.

## 6. Local URLs

| URL | What |
| --- | --- |
| http://spotaxis.localhost:8010/ | Main site / job board |
| http://spotaxis.localhost:8010/jobs/ | Public job search |
| http://spotaxis.localhost:8010/login/ | Login |
| http://spotaxis.localhost:8010/signup/talent/ | Candidate signup |
| http://spotaxis.localhost:8010/signup/employer/ | Employer signup |
| http://spotaxis.localhost:8010/admin/ | Django admin |
| http://spotaxis.localhost:8010/api/common/countries/ | REST API (see `*/api/urls.py`, `vacancies_api/`, `companies_api/`) |
| http://&lt;slug&gt;.spotaxis.localhost:8010/ | A company career site |

`http://localhost:8010/` returns 404 on purpose — the host must match
`site_suffix`. For a career site, create a `Subdomain` in the admin, attach it to
a `Company`, and browse to its slug.

## 7. Test accounts

Seeded in the local database. All local-only placeholders — none of these exist
anywhere but your machine. Log in with the **username**, not the email (the login
field is styled as an email input, but `User.USERNAME_FIELD` is `username`).

| Role | Username | Password | Where to log in |
| --- | --- | --- | --- |
| Superuser | `admin` | `admin12345` | http://spotaxis.localhost:8010/admin/ |
| Candidate | `candidate` | `SpotAxis!234` | http://spotaxis.localhost:8010/login/ |
| Recruiter | `employer` | `SpotAxis!234` | the company subdomain, below |

The recruiter owns a demo company, **Acme Robotics**, whose career site and
dashboard live on its own subdomain:

    http://acmeroboticsemBO.spotaxis.localhost:8010/

Sessions are per-host, so log in as `employer` **on that subdomain**, not on
`spotaxis.localhost`. Once there: `/profile/company/`, `/team/`, `/billing/`,
`/profile/employer/`, and `/job/edit/` (create a job opening).

As `candidate` on the main site: `/profile/`, `/appliedjobs/`, `/applylater/`,
`/notifications/`.

Recreate any of these with:

```bash
.venv/bin/python manage.py createsuperuser
```

or by signing up at `/signup/talent/` or `/signup/employer/` — new accounts land
inactive, and the activation link is printed to the `runserver` console by the
email backend.

Note that the `admin` superuser has no candidate/recruiter profile, so logging it
into the **front-end** `/login/` form leads to a 500 at `/redirect/`, which
branches on `profile.codename`. Use `/admin/` for the superuser and the role
accounts for the app itself.

## 8. Checks

```bash
.venv/bin/python manage.py check                            # clean
.venv/bin/python manage.py test common companies vacancies candidates payments
```

## 9. Known limitations

These are pre-existing to the codebase, not artifacts of the local setup:

- **8 failing tests in `common/tests/test_models.py`.** They assert the `User`
  model uses `email` as `USERNAME_FIELD` and has a `_username` field; the model
  uses `username`. Stale tests, unrelated to the environment. The other 7 pass.
- **`makemigrations --check` reports drift** for `common.Subdomain`'s Meta
  options. `common/models.py` has a `__str__` dedented out of the class body
  (line 473), which leaves the `class Meta` below it unreachable.
- **`collectstatic` needs `static_root` set** in `.env`. Not required locally —
  `DEBUG` serves static files straight from `TRM/static`.
- **Sessions are per-host.** `session_cookie_domain` is empty because a shared
  `.spotaxis.localhost` cookie is not honoured by every browser, so logging in on
  the main site does not carry to a company subdomain — log in again there. The
  upstream `CrossDomainSessionMiddleware` that would have handled this is
  commented out in `TRM/settings.py`.
- **A user with no profile 500s at `/redirect/`.** `common.views.redirect_after_login`
  branches on `profile.codename`; a bare superuser has none. Pre-existing.
- **Generated career-site links hardcode whatever port is in `site_suffix`.**
  `Company.getcompanyurl()` and the vacancy models concatenate the slug with
  `site_suffix`, so if you change the runserver port you must change it there
  too or those links point at the wrong port.
- **Third-party integrations are inert**: PayPal checkout, OAuth social login,
  and the resume parser's Selenium paths all need real credentials or a browser
  driver. `zinnia` (blog) and `helpdesk` are commented out of `INSTALLED_APPS`
  upstream and stay that way.
- **Outbound email is console-only** by design; nothing leaves the machine.

## What was changed to make this run

Three source files, all backwards compatible with the production configuration:

- `TRM/__init__.py` — adds Homebrew's library directory to
  `DYLD_FALLBACK_LIBRARY_PATH` on macOS so WeasyPrint's `dlopen` finds Pango and
  GLib. It is set in-process because System Integrity Protection strips `DYLD_*`
  from the environment whenever `/bin/sh` or `/usr/bin/env` spawns the
  interpreter, which makes exporting it from a shell unreliable. Also aliases
  `django.utils.encoding.smart_text` to `smart_str`; `django-tagging` 0.5.0 still
  imports the name Django removed in 4.0, and it breaks the app registry.
- `TRM/middleware.py` — the main-site host check now strips a port off
  `SITE_SUFFIX` before comparing it to the request host, so `site_suffix` can
  carry the local port. No-op when `SITE_SUFFIX` has no port.
- `TRM/context_processors.py` — `active_host` is derived from `SITE_SUFFIX`
  instead of a hardcoded `.com`. Produces the identical string under the
  production default.

Dependencies in `pyproject.toml` / `uv.lock` were not touched.
