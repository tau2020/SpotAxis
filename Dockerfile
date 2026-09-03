FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Native libraries for WeasyPrint (PDF), Pillow and psycopg.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfontconfig1 libcairo2 libgdk-pixbuf-2.0-0 \
        libjpeg62-turbo zlib1g fonts-dejavu-core curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.7.8 /uv /uvx /bin/

WORKDIR /app

# Install dependencies first so the layer is cached across code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# Collect static assets at build time so the image is self-contained.
RUN SECRET_KEY=build-only DEBUG=false DATABASE_URL=postgres://x:x@localhost/x \
    python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_reference_data && gunicorn TRM.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --threads 2 --timeout 60 --access-logfile - --error-logfile -"]
