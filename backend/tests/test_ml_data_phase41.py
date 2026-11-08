"""Validate synthetic data, leakage boundaries and the offline evaluation contract."""

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date

import pytest
from django.core.management import call_command

from core import ml_data


@pytest.fixture(scope="module")
def generated():
    return ml_data.generate(seed=42)


def test_shape_and_store_product_coverage(generated):
    rows, lots, _, metadata = generated
    assert len(rows) == 3 * 4 * 180
    assert len(lots) == 12 * 20 * 2
    assert Counter(row["store_id"] for row in rows) == {"S1": 720, "S2": 720, "S3": 720}
    assert len({row["product_id"] for row in rows}) == 12
    assert metadata["seed"] == 42


def test_one_target_per_product_day_even_with_two_lots(generated):
    rows, lots, _, _ = generated
    assert len({(row["date"], row["product_id"]) for row in rows}) == len(rows)
    assert all(len([lot for lot in lots if lot["product_id"] == product and
                    lot["received_date"] == rows[0]["date"]]) == 2
               for product in {row["product_id"] for row in rows})


def test_reproducible_same_seed_and_variable_other_seed(generated):
    assert ml_data.generate(42) == generated
    assert ml_data.generate(43)[0] != generated[0]
    assert ml_data.generate(44)[0] != generated[0]


def test_exact_temporal_splits_and_lot_isolation(generated):
    rows, lots, allocations, _ = generated
    assert Counter(row["split"] for row in rows) == {"train": 1296, "validation": 432, "test": 432}
    split_by_date = {row["date"]: row["split"] for row in rows}
    assert len(split_by_date) == 180
    assert split_by_date["2025-04-18"] == "train"
    assert split_by_date["2025-04-19"] == "validation"
    assert split_by_date["2025-05-24"] == "validation"
    assert split_by_date["2025-05-25"] == "test"
    lot_split = {lot["lot_id"]: lot["split"] for lot in lots}
    assert all(lot_split[item["lot_id"]] == split_by_date[item["date"]] for item in allocations)
    assert all(lot["split"] == split_by_date[lot["received_date"]] for lot in lots)


def test_holdout_protocol_keeps_unseen_store_and_product_separate(generated):
    rows, _, _, metadata = generated
    train_for_model = [row for row in rows if row["split"] == "train" and
                       row["store_id"] != ml_data.HOLDOUT_STORE and
                       row["product_id"] != ml_data.HOLDOUT_PRODUCT]
    assert train_for_model
    assert all(row["store_id"] != ml_data.HOLDOUT_STORE and
               row["product_id"] != ml_data.HOLDOUT_PRODUCT for row in train_for_model)
    report = ml_data.evaluate_holdouts(rows)
    assert report["unseen_store"]["rows"] == 144
    assert report["unseen_product"]["rows"] == 36
    assert report["seen_groups"]["rows"] == 252
    assert metadata["holdout_protocol"]["training_rule"].startswith("exclude")


def test_allocated_sales_equal_observed_and_never_exceed_latent(generated):
    rows, _, allocations, _ = generated
    by_day = defaultdict(int)
    for item in allocations:
        by_day[(item["date"], item["product_id"])] += item["sold_steps"]
    for row in rows:
        assert by_day[(row["date"], row["product_id"])] == row["observed_sales_steps"]
        assert 0 <= row["observed_sales_steps"] <= row["latent_demand_steps"]
        assert row["observed_sales_steps"] <= row["stock_steps"]
        assert row["stockout"] == int(row["observed_sales_steps"] < row["latent_demand_steps"])
    assert any(row["stockout"] for row in rows)


def test_lot_conservation_and_fefo_allocation(generated):
    _, lots, allocations, _ = generated
    sold_by_lot = Counter()
    for item in allocations:
        sold_by_lot[item["lot_id"]] += item["sold_steps"]
    by_id = {lot["lot_id"]: lot for lot in lots}
    assert all(lot["received_steps"] == sold_by_lot[lot["lot_id"]] + lot["unsold_steps"]
               for lot in lots)
    assert all(lot["unsold_steps"] >= 0 for lot in lots)
    assert all(by_id[item["lot_id"]]["received_date"] <= item["date"] <=
               by_id[item["lot_id"]]["sales_close_date"] for item in allocations)
    # If the later lot sold, the earlier sellable lot must have been exhausted that day.
    by_day = defaultdict(list)
    for item in allocations:
        by_day[(item["date"], item["product_id"])].append(item)
    assert all([by_id[item["lot_id"]]["sales_close_date"] for item in batch] ==
               sorted(by_id[item["lot_id"]]["sales_close_date"] for item in batch)
               for batch in by_day.values())


def test_lag_features_only_use_past_observed_sales(generated):
    rows, _, _, _ = generated
    history = defaultdict(list)
    for row in sorted(rows, key=lambda item: (item["date"], item["product_id"])):
        past = history[row["product_id"]]
        assert row["lag7_sales_sum"] == sum(past[-7:])
        assert row["lag14_sales_sum"] == sum(past[-14:])
        assert row["lag7_days"] == min(7, len(past))
        assert row["lag14_days"] == min(14, len(past))
        past.append(row["observed_sales_steps"])


def test_feature_contract_excludes_labels_and_hidden_parameters(generated):
    rows, _, _, metadata = generated
    assert set(ml_data.FEATURE_FIELDS).issubset(rows[0])
    assert ml_data.TARGET_FIELD not in ml_data.FEATURE_FIELDS
    assert "observed_sales_steps" not in ml_data.FEATURE_FIELDS
    assert "stockout" not in ml_data.FEATURE_FIELDS
    assert "interest" not in rows[0] and "elasticity" not in rows[0]
    assert metadata["simulator"]["hidden_parameters_not_features"]


def test_baseline_is_causal_and_mae_matches_hand_calculation():
    rows = [{"lag7_days": 0, "lag7_sales_sum": 0, "latent_demand_steps": 3,
             "observed_sales_steps": 2, "stockout": 1},
            {"lag7_days": 2, "lag7_sales_sum": 4, "latent_demand_steps": 1,
             "observed_sales_steps": 1, "stockout": 0}]
    assert ml_data.baseline_metrics(rows) == {"rows": 2, "mae_steps_per_day": 2.0,
                                              "stockout_days": 1, "unobserved_demand_steps": 1}
    with pytest.raises(ValueError):
        ml_data.baseline_metrics([])


def test_scenario_metrics_define_revenue_waste_and_safety(generated):
    rows, lots, _, metadata = generated
    report = ml_data.scenario_metrics(rows, lots, metadata)
    assert set(report) == {"train", "validation", "test"}
    for split, metrics in report.items():
        assert metrics["sold_steps"] > 0
        assert metrics["unsold_steps_at_close"] >= 0
        assert float(metrics["revenue_pen"]) > 0
        assert float(metrics["margin_pen"]) > 0
        assert 0 <= metrics["mean_realized_discount_pct"] <= 30
        assert metrics["stock_violations"] == metrics["price_violations"] == 0
        assert metrics["sold_steps"] == sum(row["observed_sales_steps"] for row in rows
                                            if row["split"] == split)


def test_rejects_invalid_generator_arguments():
    for seed in (-1, True, 1.5, "42"):
        with pytest.raises(ValueError):
            ml_data.generate(seed=seed)
    with pytest.raises(ValueError):
        ml_data.generate(start_date="2025-01-01")
    with pytest.raises(ValueError):
        ml_data.split_for_day(180)


def test_written_artifacts_are_identical_and_hash_verified(tmp_path):
    first = ml_data.write_dataset(tmp_path / "first", seed=42)
    second = ml_data.write_dataset(tmp_path / "second", seed=42)
    assert first == second
    for filename, details in first["files"].items():
        data = (tmp_path / "first" / filename).read_bytes()
        assert data == (tmp_path / "second" / filename).read_bytes()
        assert hashlib.sha256(data).hexdigest() == details["sha256"]
    assert json.loads((tmp_path / "first" / "manifest.json").read_text(encoding="utf-8")) == first
    assert first["validation_state"] == "SYNTHETIC_BASELINE_ONLY"
    with (tmp_path / "first" / "demand.csv").open(encoding="utf-8", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 2160


def test_stress_command_writes_three_independent_runs(tmp_path):
    call_command("generate_ml_demo", output=tmp_path, stress=True, verbosity=0)
    manifests = [json.loads((tmp_path / f"seed-{seed}" / "manifest.json").read_text(encoding="utf-8"))
                 for seed in (42, 43, 44)]
    assert [item["seed"] for item in manifests] == [42, 43, 44]
    assert len({item["files"]["demand.csv"]["sha256"] for item in manifests}) == 3
    assert all(item["baseline"]["test"]["rows"] == 432 for item in manifests)
