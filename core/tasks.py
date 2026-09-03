"""Registry of periodic tasks.

There is no worker process. Tasks are idempotent functions that run in a
request (``POST /internal/tasks/run``) triggered by an external scheduler
(GitHub Actions or a Railway cron service), or from ``manage.py run_tasks``.
Each task must be cheap enough to finish well inside a request timeout.
"""
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

_TASKS = {}


def task(name):
    def register(fn):
        _TASKS[name] = fn
        return fn

    return register


def run_all():
    results = {}
    for name, fn in _TASKS.items():
        try:
            results[name] = fn() or 'ok'
        except Exception:  # noqa: BLE001 - one failing task must not stop the others
            logger.exception('Task %s failed', name)
            results[name] = 'error'
    return results


@task('publish_scheduled_jobs')
def publish_scheduled_jobs():
    """Publish open vacancies whose publication date has arrived and
    unpublish those whose unpublish date has passed."""
    from vacancies.models import Vacancy

    today = timezone.localdate()
    published = 0
    for job in Vacancy.objects.filter(status__codename='open', pub_date__lte=today, unpub_date__gt=today, expired=True):
        job.publish()
        published += 1
    unpublished = 0
    for job in Vacancy.objects.filter(status__codename='open', unpub_date__lte=today - timedelta(days=0), expired=False):
        job.unublish()
        unpublished += 1
    return f'published={published} unpublished={unpublished}'
