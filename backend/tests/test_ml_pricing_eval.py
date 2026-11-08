"""Check independent, read-only comparisons against the synthetic demand law."""

import json

import pytest
from django.core.management import call_command

from core import ml_pricing_eval, ml_train


@pytest.fixture(scope="module")
def bundle():
    return ml_train.train_model(42)[0]


@pytest.mark.parametrize("seed", [42, 44, 45])
def test_expected_unsold_and_price_bounds_hold_across_scenarios(bundle, seed):
    result = ml_pricing_eval.compare_price_policies(bundle, seed=seed)
    assert result["scenarios"] >= 25
    assert result["price_violations"] == 0
    assert result["model_expected_unsold_no_worse_than_hold"]
    assert result["totals"]["model"]["unsold"] <= result["totals"]["hold"]["unsold"]
    assert result["model_discount_actions"] <= result["scenarios"]
    assert "not observed" in result["limitation"]


def test_command_writes_report_without_touching_operational_db(tmp_path):
    ml_train.train_and_save(tmp_path, seed=42)
    output = tmp_path / "pricing.json"
    call_command("evaluate_ml_pricing", model_dir=tmp_path, output=output, verbosity=0)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "OFFLINE_SYNTHETIC_EVALUATION_ONLY"
    assert report["model_state"] == "EXPERIMENTAL"
    assert report["all_scenarios_safe"]
    assert report["expected_unsold_no_worse"]
    assert len(report["scenarios"]) == 6
    assert sum(item["scenarios"] for item in report["scenarios"]) >= 150
