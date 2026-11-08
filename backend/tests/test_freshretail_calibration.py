"""Check real-data calibration boundaries and synthetic/real provenance."""

import hashlib
import json

import duckdb
import pytest

from core import calibrate_freshretail, ml_data


def test_profile_matches_source_and_is_not_a_label():
    profile = ml_data.load_calibration()
    assert profile["rows"] == 4_500_000
    assert profile["stores"] == 898
    assert profile["products"] == 865
    assert profile["discount_valid_rows"] + profile["discount_invalid_rows"] == profile["rows"]
    assert sum(profile["discount_bucket_counts"]) == profile["discount_valid_rows"]
    assert len(profile["source_sha256"]) == 64
    assert 0 < profile["stockout_open_hour_fraction"] < profile["stockout_day_fraction"] < 1
    assert "expiry" in profile["interpretation"]["missing"][0]


def test_calibrated_simulator_is_reproducible_and_keeps_assumptions_separate():
    profile = ml_data.load_calibration()
    first = ml_data.generate(42)
    assert first == ml_data.generate(42)
    rows, lots, _, metadata = first
    assert metadata["calibration"]["source_sha256"] == profile["source_sha256"]
    assert "synthetic" in metadata["simulator"]["expiry_factor"]
    assert all(0.7 <= row["price_ratio"] <= 1 for row in rows)
    assert all(lot["received_steps"] > 0 for lot in lots)
    hidden = metadata["simulator"]["hidden_parameters_not_features"]
    assert len({item["original_price"] for item in hidden}) >= 8
    assert len({round(item["unit_cost"] / item["original_price"], 2) for item in hidden}) >= 8
    assert all(0 < item["unit_cost"] < item["original_price"] for item in hidden)
    assert "unit_cost" not in rows[0] and "original_price" not in rows[0]


def test_calibrated_discounts_and_stockouts_are_in_realistic_range():
    profile = ml_data.load_calibration()
    real_discounted = 1 - profile["discount_bucket_counts"][0] / profile["discount_valid_rows"]
    for seed in (42, 43, 44):
        rows, _, _, _ = ml_data.generate(seed)
        simulated_discounted = sum(row["price_ratio"] < 1 for row in rows) / len(rows)
        simulated_stockouts = sum(row["stockout"] for row in rows) / len(rows)
        assert abs(simulated_discounted - real_discounted) < 0.06
        assert abs(simulated_stockouts - profile["stockout_day_fraction"]) < 0.07


def test_rejects_tampered_profile(tmp_path):
    profile = ml_data.load_calibration()
    for bad in (
        {**profile, "source": "unknown"},
        {**profile, "discount_bucket_counts": [0] * 6},
        {**profile, "weekend_weekday_sales_ratio": float("nan")},
    ):
        path = tmp_path / "profile.json"
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(ValueError):
            ml_data.load_calibration(path)


def test_calibrator_uses_observed_parquet_and_rejects_missing_fields(tmp_path):
    path = tmp_path / "small.parquet"
    db = duckdb.connect()
    db.execute("""
        COPY (
            SELECT s AS store_id, p AS product_id,
                   CAST(DATE '2024-01-01' + CAST(d AS INTEGER) AS VARCHAR) AS dt,
                   CASE WHEN dayofweek(DATE '2024-01-01' + CAST(d AS INTEGER)) IN (0,6)
                        THEN 1.2 ELSE 1.0 END AS sale_amount,
                   CASE WHEN d % 4 = 0 THEN 0.9 ELSE 1.0 END AS discount,
                   CASE WHEN d % 7 = 0 THEN 1 ELSE 0 END AS stock_hour6_22_cnt,
                   0 AS activity_flag, 0 AS holiday_flag
            FROM range(11) stores(s), range(10) products(p), range(90) days(d)
        ) TO ? (FORMAT PARQUET)
    """, [str(path)])
    profile = calibrate_freshretail.build_profile(path)
    assert profile["rows"] == 9900
    assert profile["stores"] == 11 and profile["products"] == 10
    assert profile["source_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert profile["discount_bucket_counts"][2] > 0
    assert profile["weekend_weekday_sales_ratio"] == pytest.approx(1.2)
    bad = tmp_path / "bad.parquet"
    db.execute("COPY (SELECT 1 AS store_id) TO ? (FORMAT PARQUET)", [str(bad)])
    with pytest.raises(ValueError, match="missing columns"):
        calibrate_freshretail.build_profile(bad)
    db.close()
