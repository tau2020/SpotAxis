"""Tenant isolation for team-management endpoints (Phase 0 security fixes)."""
import pytest

from common.models import Subdomain, User
from companies.models import Company, Recruiter

MEMBER, MANAGER, ADMIN = 1, 2, 3


def make_company(slug):
    return Company.objects.create(name=slug.title(), subdomain=Subdomain.objects.create(slug=slug))


def make_recruiter(company, username, membership):
    user = User.objects.create_user(username=username, email=f'{username}@example.com', password='pw')
    recruiter = Recruiter.objects.create(user=user, membership=membership)
    recruiter.company.add(company)
    return recruiter


@pytest.fixture
def acme(db):
    return make_company('acme')


@pytest.fixture
def beta(db):
    return make_company('beta')


def acme_host(settings):
    return f'acme.{settings.MAIN_HOST.split(":")[0]}'


@pytest.mark.django_db
def test_anonymous_cannot_change_permissions(client, settings, acme):
    member = make_recruiter(acme, 'acme-member', MEMBER)
    response = client.post('/ajax/updatepermissions/', {'id': member.id, 'perm': ADMIN}, HTTP_HOST=acme_host(settings))
    assert response.status_code == 302
    member.refresh_from_db()
    assert member.membership == MEMBER


@pytest.mark.django_db
def test_admin_of_other_company_cannot_change_permissions(client, settings, acme, beta):
    member = make_recruiter(acme, 'acme-member', MEMBER)
    intruder = make_recruiter(beta, 'beta-admin', ADMIN)
    client.force_login(intruder.user)
    response = client.post('/ajax/updatepermissions/', {'id': member.id, 'perm': ADMIN}, HTTP_HOST=acme_host(settings))
    assert response.status_code == 404  # scoped lookup: the member is invisible to another company
    member.refresh_from_db()
    assert member.membership == MEMBER


@pytest.mark.django_db
def test_plain_member_cannot_change_permissions(client, settings, acme):
    member = make_recruiter(acme, 'acme-member', MEMBER)
    other = make_recruiter(acme, 'acme-other', MEMBER)
    client.force_login(member.user)
    response = client.post('/ajax/updatepermissions/', {'id': other.id, 'perm': ADMIN}, HTTP_HOST=acme_host(settings))
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_change_permissions_within_own_company(client, settings, acme):
    admin = make_recruiter(acme, 'acme-admin', ADMIN)
    member = make_recruiter(acme, 'acme-member', MEMBER)
    client.force_login(admin.user)
    response = client.post('/ajax/updatepermissions/', {'id': member.id, 'perm': MANAGER}, HTTP_HOST=acme_host(settings))
    assert response.status_code == 200
    assert response.json()['success'] is True
    member.refresh_from_db()
    assert member.membership == MANAGER


@pytest.mark.django_db
def test_invalid_permission_value_rejected(client, settings, acme):
    admin = make_recruiter(acme, 'acme-admin', ADMIN)
    member = make_recruiter(acme, 'acme-member', MEMBER)
    client.force_login(admin.user)
    response = client.post('/ajax/updatepermissions/', {'id': member.id, 'perm': 99}, HTTP_HOST=acme_host(settings))
    assert response.status_code == 400


@pytest.mark.django_db
def test_admin_of_other_company_cannot_remove_member(client, settings, acme, beta):
    member = make_recruiter(acme, 'acme-member', MEMBER)
    intruder = make_recruiter(beta, 'beta-admin', ADMIN)
    client.force_login(intruder.user)
    response = client.post('/ajax/removemember/', {'id': member.id}, HTTP_HOST=acme_host(settings))
    assert response.status_code == 404  # scoped lookup: the member is invisible to another company
    member.user.refresh_from_db()
    assert member.user.is_active is True


@pytest.mark.django_db
def test_admin_cannot_remove_self(client, settings, acme):
    admin = make_recruiter(acme, 'acme-admin', ADMIN)
    client.force_login(admin.user)
    response = client.post('/ajax/removemember/', {'id': admin.id}, HTTP_HOST=acme_host(settings))
    assert response.status_code == 404
    assert response.json()['success'] is False
    admin.user.refresh_from_db()
    assert admin.user.is_active is True


@pytest.mark.django_db
def test_ownership_cannot_move_to_member_of_other_company(client, settings, acme, beta):
    owner = make_recruiter(acme, 'acme-owner', ADMIN)
    acme.user = owner.user
    acme.save()
    outsider = make_recruiter(beta, 'beta-member', MEMBER)
    client.force_login(owner.user)
    response = client.post('/ajax/changeownership/', {'id': outsider.id}, HTTP_HOST=acme_host(settings))
    assert response.status_code == 404
    assert response.json()['success'] is False
    acme.refresh_from_db()
    assert acme.user == owner.user
