from django.conf import settings
from django.http import Http404
from django.urls import set_urlconf
from django.utils.cache import patch_vary_headers

from TRM.hosts import resolve_host

# Paths that must answer on any host (platform health checks hit the container
# directly, without the public host name).
HOST_AGNOSTIC_PATHS = ('/healthz', '/healthz/', '/internal/tasks/run', '/internal/tasks/run/')


class SubdomainMiddleware:
    """Route company careers sites to ``settings.SUBDOMAIN_URLCONF``.

    * Main site host -> ``ROOT_URLCONF``.
    * ``<slug>.<main host>`` or a registered CNAME -> ``SUBDOMAIN_URLCONF``
      with ``request.subdomain`` set.
    * Unknown host -> 404.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in HOST_AGNOSTIC_PATHS:
            return self.get_response(request)

        info = resolve_host(request)
        request.subdomain = None
        if info.is_main:
            set_urlconf(None)
            request.urlconf = settings.ROOT_URLCONF
        elif info.subdomain is not None:
            request.subdomain = info.subdomain
            set_urlconf(settings.SUBDOMAIN_URLCONF)
            request.urlconf = settings.SUBDOMAIN_URLCONF
        else:
            raise Http404('Unknown host')

        response = self.get_response(request)
        patch_vary_headers(response, ('Host',))
        return response


class MediumMiddleware:
    """Remember the first external referrer of a session as the traffic source
    ("medium") so applications can be attributed to it."""

    MAX_REFERRER_LENGTH = 512

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        referrer = request.META.get('HTTP_REFERER', '')
        if referrer and 'referral_source' not in request.session:
            host = request.get_host().split(':')[0]
            if host not in referrer:
                request.session['referral_source'] = referrer[: self.MAX_REFERRER_LENGTH]
        return self.get_response(request)
