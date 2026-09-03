import hmac

from django.conf import settings
from django.db import connection
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from core import tasks


@require_GET
def healthz(request):
    """Liveness/readiness probe: verifies the database answers."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:  # noqa: BLE001
        return JsonResponse({'status': 'error', 'database': 'unreachable'}, status=503)
    return JsonResponse({'status': 'ok'})


@csrf_exempt
@require_POST
def run_tasks(request):
    """Run all registered periodic tasks. Authenticated by a bearer token."""
    expected = settings.TASK_RUNNER_TOKEN
    supplied = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        return HttpResponseForbidden('invalid task token')
    return JsonResponse({'results': tasks.run_all()})
