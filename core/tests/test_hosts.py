import pytest
from django.http import Http404, HttpResponse
from django.test import RequestFactory

from common.models import Subdomain
from TRM.middleware import SubdomainMiddleware


def _run(host, path='/'):
    middleware = SubdomainMiddleware(lambda request: HttpResponse('ok'))
    request = RequestFactory().get(path, HTTP_HOST=host)
    middleware(request)
    return request


def bare_main_host(settings):
    return settings.MAIN_HOST.split(':')[0]


@pytest.mark.django_db
def test_main_host_uses_root_urlconf(settings):
    request = _run(settings.MAIN_HOST)
    assert request.urlconf == settings.ROOT_URLCONF
    assert request.subdomain is None


@pytest.mark.django_db
def test_company_slug_host_uses_subdomain_urlconf(settings):
    Subdomain.objects.create(slug='acme')
    request = _run(f'acme.{bare_main_host(settings)}')
    assert request.urlconf == settings.SUBDOMAIN_URLCONF
    assert request.subdomain.slug == 'acme'


@pytest.mark.django_db
def test_registered_cname_host_uses_subdomain_urlconf(settings):
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['jobs.acme.example']
    Subdomain.objects.create(slug='acme', cname='jobs.acme.example')
    request = _run('jobs.acme.example')
    assert request.urlconf == settings.SUBDOMAIN_URLCONF
    assert request.subdomain.cname == 'jobs.acme.example'


@pytest.mark.django_db
def test_unknown_company_host_is_404(settings):
    with pytest.raises(Http404):
        _run(f'nobody.{bare_main_host(settings)}')


@pytest.mark.django_db
def test_health_check_ignores_host(settings):
    request = _run(f'nobody.{bare_main_host(settings)}', path='/healthz')
    assert request.path == '/healthz'
