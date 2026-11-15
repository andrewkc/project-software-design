"""Apply the owner-approved demo pricing policy once per day."""

from django.core.management.base import BaseCommand

from core import pricing_service


class Command(BaseCommand):
    help = "Analiza y aplica precios de bodegas demo que eligieron modo automático."

    def handle(self, *args, **options):
        result = pricing_service.run_automatic_pricing()
        self.stdout.write("Bodegas: {stores}; aplicadas: {applied}; mantener: {kept}; "
                          "obsoletas: {stale}".format(**result))
