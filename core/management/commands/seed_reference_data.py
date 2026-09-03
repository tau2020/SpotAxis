"""Load the reference fixtures every environment needs (countries, currencies,
degrees, profiles, industries, form field types, vacancy lookups, plans).

Safe to run repeatedly: fixtures are keyed by primary key, so existing rows are
updated in place and nothing is duplicated. Runs on container start.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

FIXTURES = [
    'common_country',
    'common_currency',
    'common_degree',
    'common_employment_type',
    'common_gender',
    'common_marital_status',
    'common_profile',
    'companies_company_industry',
    'customfield_fieldclassification',
    'customfield_fieldtype',
    'vacancies_employment_experience',
    'vacancies_salary_type',
    'vacancies_vacancy_status',
    'vacancies_pubdate_search',
    'payments_servicecategory',
    'payments_services',
    'payments_package',
    'payments_priceslab',
]


class Command(BaseCommand):
    help = 'Load reference data fixtures (idempotent).'

    def handle(self, *args, **options):
        for name in FIXTURES:
            call_command('loaddata', name, verbosity=0)
        self.stdout.write(f'Loaded {len(FIXTURES)} reference fixtures.')
