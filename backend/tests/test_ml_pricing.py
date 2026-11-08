"""Adversarial checks for bounded, read-only model price recommendations."""

from decimal import Decimal

import pytest

from core import ml_data, ml_pricing, ml_train


def features(**updates):
    result = {"store_id": "S1", "category": "Fruta", "price_ratio": 1.0,
              "current_price": 10.0, "days_to_close": 1, "stock_steps": 20,
              "weekday": 1, "lot_age_days": 4, "lag7_sales_sum": 20,
              "lag7_days": 7, "lag14_sales_sum": 40, "lag14_days": 14}
    return {**result, **updates}


def demand_response(rows):
    return [3 + 10 * (1 - row["price_ratio"]) for row in rows]


def call(predictor=demand_response, row=None, **overrides):
    args = {"original_price": "10.00", "current_price": "10.00",
            "floor": "7.00", "available_steps": 10}
    args.update(overrides)
    return ml_pricing.recommend_price(predictor, row or features(), **args)


def test_candidate_grid_includes_exact_endpoints_and_never_crosses_floor():
    values = ml_pricing.candidate_prices("9.99", "9.43", "7.01")
    assert values[0] == Decimal("9.43") and values[-1] == Decimal("7.01")
    assert all(Decimal("7.01") <= x <= Decimal("9.43") for x in values)
    assert all(a > b for a, b in zip(values, values[1:]))
    assert len(values) < 40


def test_chooses_highest_price_reaching_ninety_percent_coverage():
    result = call()
    assert result["status"] == "PENDING"
    assert result["proposed_price"] == "8.50"
    assert result["reason"] == "TARGET_COVERAGE"
    assert result["proposed_coverage"] >= .9
    assert result["current_coverage"] == .6


def test_keeps_price_when_current_coverage_is_enough():
    result = call(lambda rows: [6.0] * len(rows))
    assert result["status"] == "KEEP" and result["proposed_price"] == "10.00"
    assert result["reason"] == "CURRENT_PRICE_COVERS_STOCK"


def test_chooses_max_sales_if_target_unreachable():
    result = call(lambda rows: [1 + 2 * (1 - row["price_ratio"]) for row in rows])
    assert result["status"] == "PENDING"
    assert result["proposed_price"] == "7.00"
    assert result["reason"] == "MAX_EXPECTED_SALES"


def test_five_point_gain_threshold_blocks_cosmetic_discount():
    result = call(lambda rows: [3 + .1 * (1 - row["price_ratio"]) for row in rows])
    assert result["status"] == "KEEP"
    assert result["reason"] == "GAIN_BELOW_FIVE_POINTS"


def test_no_stock_history_or_closed_sale_does_not_invoke_model():
    def forbidden(_):
        raise AssertionError("predictor should not be called")
    assert call(forbidden, available_steps=0)["reason"] == "NO_STOCK"
    assert call(forbidden, row=features(lag7_days=2))["reason"] == "INSUFFICIENT_HISTORY"
    assert call(forbidden, row=features(days_to_close=9))["reason"] == "OUTSIDE_TRAINING_HORIZON"
    assert call(forbidden, row=features(days_to_close=0), first_day_fraction=0)["reason"] == "SALES_CLOSED"


def test_partial_day_reduces_expected_sales():
    full = call(lambda rows: [3.0] * len(rows), floor="10.00")
    half = call(lambda rows: [3.0] * len(rows), floor="10.00", first_day_fraction=.5)
    assert full["current_expected_sales"] == 6
    assert half["current_expected_sales"] == 4.5


@pytest.mark.parametrize("field,value", [("original_price", "NaN"),
                                          ("current_price", "0"),
                                          ("floor", "10.01"),
                                          ("available_steps", -1),
                                          ("available_steps", True),
                                          ("first_day_fraction", 1.1)])
def test_rejects_invalid_bounds(field, value):
    with pytest.raises(ValueError):
        call(**{field: value})


def test_rejects_bad_predictor_output():
    with pytest.raises(ValueError, match="wrong number"):
        call(lambda rows: [])
    with pytest.raises(ValueError, match="invalid demand"):
        call(lambda rows: [float("nan")] * len(rows))
    with pytest.raises(ValueError, match="invalid demand"):
        call(lambda rows: [-1] * len(rows))


def test_trained_model_recommendations_respect_floor_and_never_raise_price():
    bundle, _ = ml_train.train_model(42)
    rows, _, _, _ = ml_data.generate(42)
    for row in [r for r in rows if r["split"] == "test" and r["lag7_days"] >= 3][:25]:
        current = Decimal(row["current_price"])
        floor = max(Decimal("0.01"), (current * Decimal("0.7")).quantize(Decimal("0.01")))
        result = ml_pricing.recommend_price(
            lambda cases: ml_train.predict(bundle, cases), row,
            original_price=current, current_price=current, floor=floor,
            available_steps=row["stock_steps"])
        proposed = Decimal(result["proposed_price"])
        assert floor <= proposed <= current
        assert result["status"] in ("KEEP", "PENDING")
