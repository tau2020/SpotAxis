from django.conf import settings
from django.utils.translation import gettext as _

from activities.models import Notification
from candidates.models import Candidate
from companies.models import Company, Recruiter
from TRM.hosts import resolve_host
from TRM.settings import LOGO_CANDIDATE_DEFAULT, LOGO_COMPANY_DEFAULT


def debug_mode(request):
    return {'debug_mode': settings.DEBUG}


def project_name(request):
    return {'project_name': settings.PROJECT_NAME, 'HOSTED_URL': settings.HOSTED_URL}


def candidate_full_name(request):
    full_name = _('Your Name')
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile and getattr(profile, 'codename', '') == 'candidate':
            try:
                candidate = Candidate.objects.get(user=request.user)
                full_name = f'{candidate.first_name} {candidate.last_name}'
            except Candidate.DoesNotExist:
                pass
    return {'candidate_full_name': full_name}


def logo_company_default(request):
    return {'LOGO_COMPANY_DEFAULT': LOGO_COMPANY_DEFAULT}


def logo_candidate_default(request):
    return {'LOGO_CANDIDATE_DEFAULT': LOGO_CANDIDATE_DEFAULT}


def subdomain(request):
    """Describe which host the request arrived on.

    Kept as a plain function (it is also called directly from views) and as a
    context processor. Keys are the legacy names the templates expect.
    """
    info = resolve_host(request)
    return {
        'active_subdomain': info.slug,
        'active_host': info.active_host,
        'isRoot': info.is_main,
        'hasCNAME': info.has_cname,
    }


def user_profile(request):
    user_profile = None
    recruiter = None
    company = None

    info = resolve_host(request)
    if info.subdomain is not None:
        company = Company.objects.filter(subdomain=info.subdomain).first()

    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile:
            user_profile = profile.codename
        if company is not None:
            recruiter = Recruiter.objects.filter(user=request.user, company=company, user__is_active=True).first()

    return {'user_profile': user_profile, 'recruiter': recruiter, 'settings': settings}


def notifications(request):
    if not request.user.is_authenticated:
        return {}
    msgs = Notification.objects.filter(user=request.user)
    return {
        'notifications': msgs[:100],
        'unseen_notification_count': msgs.filter(seen=False).count(),
    }
