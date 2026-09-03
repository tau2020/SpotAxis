import pytest


@pytest.mark.django_db
def test_healthz_reports_ok(client):
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


@pytest.mark.django_db
def test_task_runner_rejects_missing_or_wrong_token(client, settings):
    settings.TASK_RUNNER_TOKEN = 'secret-token'
    assert client.post('/internal/tasks/run').status_code == 403
    assert client.post('/internal/tasks/run', HTTP_AUTHORIZATION='Bearer nope').status_code == 403


@pytest.mark.django_db
def test_task_runner_disabled_without_configured_token(client, settings):
    settings.TASK_RUNNER_TOKEN = None
    assert client.post('/internal/tasks/run', HTTP_AUTHORIZATION='Bearer anything').status_code == 403


@pytest.mark.django_db
def test_task_runner_runs_registered_tasks(client, settings):
    settings.TASK_RUNNER_TOKEN = 'secret-token'
    response = client.post('/internal/tasks/run', HTTP_AUTHORIZATION='Bearer secret-token')
    assert response.status_code == 200
    assert 'publish_scheduled_jobs' in response.json()['results']
