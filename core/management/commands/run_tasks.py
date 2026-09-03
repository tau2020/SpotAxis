from django.core.management.base import BaseCommand

from core import tasks


class Command(BaseCommand):
    help = 'Run all registered periodic tasks once.'

    def handle(self, *args, **options):
        for name, result in tasks.run_all().items():
            self.stdout.write(f'{name}: {result}')
