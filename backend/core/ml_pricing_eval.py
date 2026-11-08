"""Counterfactual expected-outcome check on independent synthetic lot snapshots.

This is a deterministic scenario comparison, not proof of real sales or waste.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING

from . import ml_data, ml_pricing, ml_train


def _cent_up(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_CEILING)


def _outcome(row, lot, price, stock, hidden, weekend_factor):
    original = Decimal(str(hidden["original_price"]))
    ratio = float(price / original)
    today = date.fromisoformat(row["date"])
    close = date.fromisoformat(lot["sales_close_date"])
    demand = 0.0
    for offset in range((close - today).days + 1):
        day = today + timedelta(days=offset)
        weekday_factor = weekend_factor if day.weekday() in (5, 6) else 1.0
        expiry_factor = .92 if (close - day).days <= 2 else 1.0
        demand += hidden["interest"] * weekday_factor * expiry_factor * ratio ** (-hidden["elasticity"])
    sold = min(stock, demand)
    return {"unsold": stock - sold,
            "revenue": sold * float(price),
            "margin": sold * (float(price) - hidden["unit_cost"])}


def compare_price_policies(bundle, seed=42):
    """Compare one day-2 snapshot per earliest lot; same true demand equation."""
    rows, lots, allocations, metadata = ml_data.generate(seed=seed)
    hidden = {item["product_id"]: item for item in
              metadata["simulator"]["hidden_parameters_not_features"]}
    earliest = {(lot["product_id"], lot["received_date"]): lot for lot in lots
                if lot["lot_id"].endswith("-A")}
    sold_before = defaultdict(int)
    for item in allocations:
        sold_before[item["lot_id"], item["date"]] += item["sold_steps"]
    totals = {name: {"unsold": 0.0, "revenue": 0.0, "margin": 0.0}
              for name in ("hold", "expiry_rule", "model")}
    scenarios = 0
    discounts = 0
    violations = 0
    for row in rows:
        if row["split"] != "test" or row["lot_age_days"] != 2:
            continue
        received = (date.fromisoformat(row["date"]) - timedelta(days=2)).isoformat()
        lot = earliest[row["product_id"], received]
        stock = lot["received_steps"] - sum(
            qty for (lot_id, sold_date), qty in sold_before.items()
            if lot_id == lot["lot_id"] and sold_date < row["date"])
        if stock <= 0:
            continue
        params = hidden[row["product_id"]]
        original = Decimal(str(params["original_price"]))
        current = Decimal(str(row["current_price"]))
        floor = max(Decimal("0.01"), _cent_up(original * Decimal("0.70")),
                    Decimal(str(params["unit_cost"])))
        if floor > current:
            raise ValueError("simulated offer violates cost/discount floor")
        proposal = ml_pricing.recommend_price(
            lambda cases: ml_train.predict(bundle, cases), row,
            original_price=original, current_price=current, floor=floor,
            available_steps=stock)
        model_price = Decimal(proposal["proposed_price"])
        rule_price = min(current, max(floor, _cent_up(original * Decimal("0.90"))))
        if not floor <= model_price <= current:
            violations += 1
        discounts += model_price < current
        scenarios += 1
        for name, price in (("hold", current), ("expiry_rule", rule_price),
                            ("model", model_price)):
            result = _outcome(row, lot, price, stock, params,
                              metadata["calibration"]["weekend_ratio_used"])
            for key in totals[name]:
                totals[name][key] += result[key]
    if scenarios == 0:
        raise ValueError("no eligible lot scenarios")
    return {"seed": seed, "scenarios": scenarios, "model_discount_actions": discounts,
            "price_violations": violations,
            "totals": {name: {key: round(value, 2) for key, value in values.items()}
                       for name, values in totals.items()},
            "model_expected_unsold_no_worse_than_hold":
                totals["model"]["unsold"] <= totals["hold"]["unsold"] + 1e-9,
            "method": "one day-2 snapshot per first-closing lot; expected Poisson means with fixed history and common latent-demand equation",
            "limitation": "synthetic counterfactual expectation, not observed waste or causal evidence"}
