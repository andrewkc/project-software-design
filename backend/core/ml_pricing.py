"""Pure, conservative price recommendation over a fitted demand predictor.

All inputs are explicit snapshots; this module never changes an offer or stock.
"""

import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


CENT = Decimal("0.01")
TARGET_COVERAGE = 0.90
MIN_GAIN = 0.05


def _money(value, name):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"invalid {name}") from None
    if not amount.is_finite() or amount <= 0 or amount != amount.quantize(CENT):
        raise ValueError(f"invalid {name}")
    return amount


def candidate_prices(original_price, current_price, floor):
    original = _money(original_price, "original_price")
    current = _money(current_price, "current_price")
    minimum = _money(floor, "floor")
    if not minimum <= current <= original:
        raise ValueError("price order violates floor or original")
    step = max(CENT, (original / 100).quantize(CENT, rounding=ROUND_HALF_UP))
    values = [current]
    price = current - step
    while price > minimum:
        values.append(price.quantize(CENT))
        price -= step
    if values[-1] != minimum:
        values.append(minimum)
    return values


def _forecasts(predictor, features, candidates, original, days, first_day_fraction):
    cases = []
    for candidate in candidates:
        ratio = float(candidate / original)
        for offset in range(days + 1):
            cases.append({**features, "current_price": float(candidate),
                          "price_ratio": ratio,
                          "days_to_close": days - offset,
                          "weekday": (int(features["weekday"]) + offset) % 7,
                          "lot_age_days": int(features["lot_age_days"]) + offset})
    predictions = predictor(cases)
    if len(predictions) != len(cases):
        raise ValueError("predictor returned wrong number of rows")
    if any(not math.isfinite(float(x)) or float(x) < 0 for x in predictions):
        raise ValueError("predictor returned invalid demand")
    result = []
    width = days + 1
    for start in range(0, len(predictions), width):
        result.append(sum(float(value) * (first_day_fraction if index == 0 else 1.0)
                          for index, value in enumerate(predictions[start:start + width])))
    return result


def recommend_price(predictor, features, *, original_price, current_price, floor,
                    available_steps, first_day_fraction=1.0):
    """Return KEEP or a lower, bounded price based on coverage until sales close.

    Future lagged-sales and stock features remain fixed at the snapshot value.
    This is an approximation, reported in the result, not a live forecast.
    """
    prices = candidate_prices(original_price, current_price, floor)
    original = _money(original_price, "original_price")
    if isinstance(available_steps, bool) or not isinstance(available_steps, int) or available_steps < 0:
        raise ValueError("invalid available_steps")
    if not isinstance(first_day_fraction, (int, float)) or not math.isfinite(first_day_fraction) or not 0 <= first_day_fraction <= 1:
        raise ValueError("invalid first_day_fraction")
    days = features.get("days_to_close")
    if isinstance(days, bool) or not isinstance(days, int) or days < 0:
        raise ValueError("invalid days_to_close")
    current = prices[0]
    base = {"current_price": str(current), "proposed_price": str(current),
            "available_steps": available_steps, "status": "KEEP",
            "assumptions": "Future sales history and product stock held at snapshot values"}
    if available_steps == 0:
        return {**base, "reason": "NO_STOCK"}
    if days > 8:
        return {**base, "reason": "OUTSIDE_TRAINING_HORIZON"}
    if days == 0 and first_day_fraction == 0:
        return {**base, "reason": "SALES_CLOSED"}
    if int(features.get("lag7_days", 0)) < 3:
        return {**base, "reason": "INSUFFICIENT_HISTORY"}
    estimates = []
    forecasts = _forecasts(predictor, features, prices, original, days,
                           first_day_fraction)
    for price, demand in zip(prices, forecasts):
        sales = min(float(available_steps), demand)
        estimates.append({"price": price, "sales": sales,
                          "coverage": sales / available_steps,
                          "revenue": sales * float(price)})
    at_current = estimates[0]
    if at_current["coverage"] >= TARGET_COVERAGE:
        chosen, reason = at_current, "CURRENT_PRICE_COVERS_STOCK"
    else:
        qualifying = [item for item in estimates if item["coverage"] >= TARGET_COVERAGE]
        if qualifying:
            chosen, reason = max(qualifying, key=lambda item: item["price"]), "TARGET_COVERAGE"
        else:
            chosen, reason = max(estimates, key=lambda item: (item["sales"], item["revenue"], item["price"])), "MAX_EXPECTED_SALES"
        if chosen["coverage"] - at_current["coverage"] < MIN_GAIN:
            chosen, reason = at_current, "GAIN_BELOW_FIVE_POINTS"
    status = "PENDING" if chosen["price"] < current else "KEEP"
    return {**base, "status": status, "reason": reason,
            "proposed_price": str(chosen["price"]),
            "current_coverage": round(at_current["coverage"], 4),
            "proposed_coverage": round(chosen["coverage"], 4),
            "current_expected_sales": round(at_current["sales"], 4),
            "proposed_expected_sales": round(chosen["sales"], 4),
            "candidate_count": len(prices)}
