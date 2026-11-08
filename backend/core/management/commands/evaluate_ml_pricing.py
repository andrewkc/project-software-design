"""Compare candidate price policies without changing operational offers."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core import ml_pricing_eval, ml_train


class Command(BaseCommand):
    help = "Evalúa ofertas de precio del modelo en escenarios sintéticos aislados."

    def add_arguments(self, parser):
        model_dir = Path(__file__).resolve().parents[3] / "media" / "ml_models"
        parser.add_argument("--model-dir", type=Path, default=model_dir)
        parser.add_argument("--output", type=Path, default=model_dir / "pricing-evaluation.json")

    def handle(self, *args, **options):
        root = options["model_dir"]
        try:
            bundle, training = ml_train.load_trained(
                root / "demand-seed-42.joblib", root / "demand-seed-42.json")
            results = [ml_pricing_eval.compare_price_policies(bundle, seed=seed)
                       for seed in (42, 43, 44, 45, 46, 47)]
        except (ValueError, OSError) as error:
            raise CommandError(str(error)) from error
        output = {"model_sha256": training["artifact_sha256"],
                  "model_state": training["state"],
                  "scenarios": results,
                  "all_scenarios_safe": all(item["price_violations"] == 0 for item in results),
                  "expected_unsold_no_worse": all(
                      item["model_expected_unsold_no_worse_than_hold"] for item in results),
                  "status": "OFFLINE_SYNTHETIC_EVALUATION_ONLY"}
        options["output"].parent.mkdir(parents=True, exist_ok=True)
        options["output"].write_text(json.dumps(output, ensure_ascii=False, indent=2,
                                               sort_keys=True) + "\n", encoding="utf-8")
        self.stdout.write(f"{options['output']}: {sum(item['scenarios'] for item in results)} "
                          f"escenarios; seguridad={'sí' if output['all_scenarios_safe'] else 'no'}; "
                          f"sobrantes esperados no mayores={'sí' if output['expected_unsold_no_worse'] else 'no'}")
