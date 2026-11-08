"""Generate offline synthetic training and evaluation data, without touching the DB."""

from pathlib import Path

from django.core.management.base import BaseCommand

from core.ml_data import write_dataset


class Command(BaseCommand):
    help = "Genera datos sintéticos separados de las bodegas demo (fase 4.1)."

    def add_arguments(self, parser):
        parser.add_argument("--output", type=Path,
                            default=Path(__file__).resolve().parents[3] / "media" / "ml_synthetic")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--stress", action="store_true", help="Genera semillas 42, 43 y 44")

    def handle(self, *args, **options):
        seeds = (42, 43, 44) if options["stress"] else (options["seed"],)
        for seed in seeds:
            output = options["output"] / f"seed-{seed}"
            try:
                manifest = write_dataset(output, seed=seed)
            except ValueError as error:
                from django.core.management.base import CommandError
                raise CommandError(str(error)) from error
            test = manifest["baseline"]["test"]
            self.stdout.write(f"{output}: {manifest['files']['demand.csv']['rows']} días-producto; "
                              f"MAE base prueba={test['mae_steps_per_day']}; "
                              f"demanda no observada={test['unobserved_demand_steps']}")
