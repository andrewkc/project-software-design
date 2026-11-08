"""Train and evaluate the offline demand model without touching the database."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.ml_train import train_and_save


class Command(BaseCommand):
    help = "Entrena y evalúa el modelo experimental de demanda para la demo."

    def add_arguments(self, parser):
        parser.add_argument("--output", type=Path,
                            default=Path(__file__).resolve().parents[3] / "media" / "ml_models")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        try:
            report = train_and_save(options["output"], seed=options["seed"])
        except (ValueError, OSError) as error:
            raise CommandError(str(error)) from error
        result = report["evaluation"]["test_all"]
        self.stdout.write(
            f"Modelo {report['state']} guardado en {options['output'] / report['artifact']}; "
            f"MAE prueba={result['model_mae']} vs base={result['baseline_mae']}; "
            f"criterio demanda={'aprobado' if report['demand_quality_gate'] else 'no aprobado'}"
        )
