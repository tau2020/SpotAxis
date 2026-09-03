"""Host-name resolution shared by the subdomain middleware and the template
context processor.

The platform serves two kinds of hosts:

* the **main site** (``settings.MAIN_HOST`` or any host in
  ``settings.MAIN_HOSTS``): marketing pages, the job board, login and signup;
* a **company careers site**, addressed either by ``<slug>.<MAIN_HOST>`` or
  by a custom CNAME stored on :class:`common.models.Subdomain`.

Anything else is rejected with a 404 by the middleware.
"""
from dataclasses import dataclass

from django.conf import settings
from django.db.models import Q


@dataclass(frozen=True)
class HostInfo:
    host: str
    is_main: bool
    subdomain: object = None  # common.models.Subdomain or None

    @property
    def slug(self):
        return self.subdomain.slug if self.subdomain else None

    @property
    def has_cname(self):
        return bool(self.subdomain and self.subdomain.cname)

    @property
    def active_host(self):
        if not self.subdomain:
            return None
        if self.subdomain.cname:
            return self.subdomain.cname
        return f'{self.subdomain.slug}{settings.SITE_SUFFIX.rstrip("/")}'


def _bare(host):
    return host.split(':')[0].lower()


def resolve_host(request):
    """Return a :class:`HostInfo` for the request's Host header.

    The result is cached on the request so the middleware and the context
    processor share one database lookup.
    """
    cached = getattr(request, '_spotaxis_host', None)
    if cached is not None:
        return cached

    host = _bare(request.get_host())
    main_host = _bare(settings.MAIN_HOST)
    if host == main_host or host in settings.MAIN_HOSTS:
        info = HostInfo(host=host, is_main=True)
    else:
        info = _lookup_subdomain(host, main_host)
    request._spotaxis_host = info
    return info


def _lookup_subdomain(host, main_host):
    from common.models import Subdomain

    slug = None
    suffix = '.' + main_host
    if host.endswith(suffix):
        label = host[: -len(suffix)]
        if label and '.' not in label:
            slug = label

    query = Q(cname=host)
    if slug:
        query |= Q(slug=slug)
    subdomain = Subdomain.objects.filter(query).exclude(slug__isnull=True, cname__isnull=True).first()
    return HostInfo(host=host, is_main=False, subdomain=subdomain)
