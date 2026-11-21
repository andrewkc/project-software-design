"""Reconcile signed notifications and pending test orders independently of browsers."""

from django.core.management.base import BaseCommand

from core.payments import run_reconciliation


class Command(BaseCommand):
    help = "Process payment events, poll pending test orders and release expired reservations"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        count = run_reconciliation(options["limit"])
        self.stdout.write(f"Reconciled {count} payment checks")
