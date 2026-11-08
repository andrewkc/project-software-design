"""Exercise the offline model, its held-out evaluation, and artifact checks."""

import json

import numpy as np
import pytest
from django.core.management import call_command

from core import ml_data, ml_train


@pytest.fixture(scope="module")
def trained():
    return ml_train.train_model(seed=42)


def test_training_uses_only_past_seen_groups(trained):
    bundle, report = trained
    assert report["rows_fit"] == 756
    assert report["state"] == "EXPERIMENTAL"
    assert bundle["feature_fields"] == ml_train.MODEL_FIELDS
    assert "product_id" not in bundle["feature_fields"]
    categories = bundle["transformer"].named_transformers_["categorical"].categories_
    assert "S3" not in categories[0]
    assert report["evaluation"]["validation_seen"]["rows"] == 252
    assert report["evaluation"]["test_all"]["rows"] == 432
    assert report["evaluation"]["test_unseen_product"]["rows"] == 36
    assert report["evaluation"]["test_unseen_store"]["rows"] == 144


def test_model_beats_baseline_on_temporal_and_unseen_groups(trained):
    _, report = trained
    assert report["demand_quality_gate"] is True
    assert set(report["evaluation"]) == {
        "validation_seen", "test_all", "test_seen", "test_unseen_product",
        "test_unseen_store", "stress_seed_43", "stress_seed_44",
        "stress_seed_45", "stress_seed_46", "stress_seed_47",
    }
    assert all(result["model_mae"] <= result["baseline_mae"]
               for result in report["evaluation"].values())


def test_predictions_are_finite_nonnegative_and_work_for_new_store(trained):
    bundle, _ = trained
    rows, _, _, _ = ml_data.generate(42)
    unseen = next(row for row in rows if row["split"] == "test" and row["store_id"] == "S3")
    values = ml_train.predict(bundle, [unseen, {**unseen, "store_id": "NEW", "product_id": "NEW-ITEM"}])
    assert values.shape == (2,)
    assert np.isfinite(values).all() and (values >= 0).all()


def test_price_increase_never_increases_prediction(trained):
    bundle, report = trained
    rows, _, _, _ = ml_data.generate(42)
    sample = [row for row in rows if row["split"] == "test"][:100]
    assert report["monotonic_price_violations"] == 0
    assert ml_train.monotonic_price_violations(bundle, sample) == 0


def test_rejects_missing_or_nonfinite_features(trained):
    bundle, _ = trained
    row = ml_data.generate(42)[0][0]
    with pytest.raises(ValueError, match="missing model features"):
        ml_train.predict(bundle, [{key: value for key, value in row.items()
                                   if key != "price_ratio"}])
    with pytest.raises(ValueError, match="non-finite"):
        ml_train.predict(bundle, [{**row, "price_ratio": float("nan")}])
    with pytest.raises(ValueError, match="schema mismatch"):
        ml_train.predict({**bundle, "feature_fields": ("bad",)}, [row])
    with pytest.raises(ValueError, match="no rows"):
        ml_train.predict(bundle, [])


def test_artifact_reload_preserves_prediction_and_checks_hash(tmp_path):
    report = ml_train.train_and_save(tmp_path, seed=42)
    artifact = tmp_path / report["artifact"]
    report_path = tmp_path / "demand-seed-42.json"
    assert artifact.is_file() and report_path.is_file()
    loaded, saved = ml_train.load_trained(artifact, report_path)
    assert saved["artifact_sha256"] == report["artifact_sha256"]
    rows = ml_data.generate(42)[0][-10:]
    assert (ml_train.predict(loaded, rows) >= 0).all()
    assert saved["evaluation"] == report["evaluation"]
    bad = {**saved, "artifact_sha256": "0" * 64}
    report_path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        ml_train.load_trained(artifact, report_path)


def test_command_trains_offline_and_writes_report(tmp_path):
    call_command("train_ml_demo", output=tmp_path, verbosity=0)
    artifact = tmp_path / "demand-seed-42.joblib"
    report_path = tmp_path / "demand-seed-42.json"
    _, report = ml_train.load_trained(artifact, report_path)
    assert report["demand_quality_gate"] is True
    assert report["state"] == "EXPERIMENTAL"


def test_same_seed_repeats_metrics_and_invalid_seed_is_rejected(trained):
    _, first = trained
    _, second = ml_train.train_model(seed=42)
    assert first["evaluation"] == second["evaluation"]
    with pytest.raises(ValueError):
        ml_train.train_model(seed=-1)
