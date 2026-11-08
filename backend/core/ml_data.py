"""Synthetic demand data for phase 4.1. Never reads or writes operational tables."""

import csv
import hashlib
import json
import math
import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING
from pathlib import Path


DATASET_VERSION = "synthetic-demand-v3-freshretail-calibrated"
PROFILE_PATH = Path(__file__).with_name("freshretail_profile.json")
START_DATE = date(2025, 1, 1)
DAYS = 180
SPLIT_ENDS = (108, 144, 180)  # 60/20/20; all boundaries are nine-day lot cycles.
STORES = ("Mercado Verde", "Dulce y Fresco", "Frutas del Barrio")
PRODUCTS = (
    ("ALM", "Frutos secos", 3.3, 1.1),
    ("PAS", "Frutos secos", 2.2, 0.4),
    ("FRE", "Fruta", 4.0, 1.7),
    ("MAN", "Fruta", 3.0, 1.4),
    ("PAT", "Fruta", 3.2, 1.3),
    ("NUE", "Frutos secos", 1.8, 0.3),
    ("ARA", "Frutos secos", 2.7, 0.8),
    ("UVA", "Fruta", 3.7, 1.6),
    ("DAT", "Frutos secos", 1.5, 0.5),
    ("CIR", "Fruta", 3.1, 1.5),
    ("HIG", "Fruta", 2.0, 1.2),
    ("MAN2", "Fruta", 3.4, 1.0),
)
DEMAND_FIELDS = (
    "date", "split", "store_id", "product_id", "category", "price_ratio",
    "current_price", "days_to_close", "stock_steps", "weekday", "lot_age_days",
    "lag7_sales_sum", "lag7_days", "lag14_sales_sum", "lag14_days",
    "latent_demand_steps", "observed_sales_steps", "stockout",
)
FEATURE_FIELDS = ("store_id", "product_id", "category", "price_ratio", "current_price",
                  "days_to_close", "stock_steps", "weekday", "lot_age_days",
                  "lag7_sales_sum", "lag7_days", "lag14_sales_sum", "lag14_days")
TARGET_FIELD = "latent_demand_steps"
HOLDOUT_STORE = "S3"
HOLDOUT_PRODUCT = "S2-UVA"
LOT_FIELDS = ("lot_id", "split", "store_id", "product_id", "received_date",
              "sales_close_date", "expiry_date", "received_steps", "unsold_steps")
ALLOCATION_FIELDS = ("date", "lot_id", "product_id", "sold_steps")


def split_for_day(day):
    if not isinstance(day, int) or not 0 <= day < DAYS:
        raise ValueError("day outside 180-day dataset")
    return "train" if day < SPLIT_ENDS[0] else "validation" if day < SPLIT_ENDS[1] else "test"


def _poisson(rng, mean):
    """Small-rate Poisson sampler using only the standard library."""
    threshold = math.exp(-mean)
    product = 1.0
    count = 0
    while product > threshold:
        product *= rng.random()
        count += 1
    return count - 1


def load_calibration(path=PROFILE_PATH):
    """Reject incompatible profiles instead of silently using invented defaults."""
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    if profile.get("schema_version") != 1 or profile.get("source") != "Dingdong-Inc/FreshRetailNet-50K":
        raise ValueError("incompatible FreshRetailNet calibration profile")
    if profile.get("discount_bucket_pct") != [0, 5, 10, 15, 20, 30]:
        raise ValueError("invalid discount buckets")
    counts = profile.get("discount_bucket_counts")
    if not isinstance(counts, list) or len(counts) != 6 or any(
            isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in counts) or sum(counts) == 0:
        raise ValueError("invalid discount counts")
    ratio = profile.get("weekend_weekday_sales_ratio")
    if not isinstance(ratio, (int, float)) or not math.isfinite(ratio) or not 0.5 <= ratio <= 2:
        raise ValueError("invalid weekend ratio")
    return profile


def generate(seed=42, start_date=START_DATE, calibration=None):
    """Produce one target per product/day and separate FEFO lot allocations."""
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if not isinstance(start_date, date):
        raise ValueError("start_date must be a date")
    if calibration is None and PROFILE_PATH.is_file():
        calibration = load_calibration()
    if calibration is not None:
        # Validate caller-supplied profiles using the same contract as the file.
        if calibration.get("schema_version") != 1 or calibration.get("source") != "Dingdong-Inc/FreshRetailNet-50K":
            raise ValueError("incompatible calibration profile")
        counts = calibration.get("discount_bucket_counts")
        if not isinstance(counts, list) or len(counts) != 6 or sum(counts) <= 0:
            raise ValueError("invalid calibration discount counts")
        weekend_factor = max(0.8, min(1.3, calibration["weekend_weekday_sales_ratio"]))
    else:
        counts = [1, 1, 1, 1, 1, 1]
        weekend_factor = 1.18
    rng = random.Random(seed)
    demand_rows, lot_rows, allocation_rows = [], [], []
    hidden = []
    for product_index, (code, category, interest, elasticity) in enumerate(PRODUCTS):
        store_id = f"S{product_index // 4 + 1}"
        product_id = f"{store_id}-{code}"
        low, high = (6.0, 12.0) if category == "Fruta" else (7.0, 15.0)
        original_price = round(rng.uniform(low, high), 2)
        unit_cost = round(original_price * rng.uniform(0.45, 0.70), 2)
        hidden.append({"product_id": product_id, "interest": interest, "elasticity": elasticity,
                       "unit_cost": unit_cost, "original_price": original_price})
        history = []
        active_lots = []
        for day in range(DAYS):
            today = start_date + timedelta(days=day)
            cycle_day = day % 9
            if cycle_day == 0:
                for lot in active_lots:
                    lot["unsold_steps"] = lot.pop("remaining_steps")
                active_lots = []
                for suffix, close_offset in (("A", 6), ("B", 8)):
                    qty = rng.randint(5, 15) if suffix == "A" else rng.randint(3, 11)
                    lot = {
                        "lot_id": f"{product_id}-{day // 9:02d}-{suffix}",
                        "split": split_for_day(day), "store_id": store_id,
                        "product_id": product_id, "received_date": today.isoformat(),
                        "sales_close_date": (today + timedelta(days=close_offset)).isoformat(),
                        "expiry_date": (today + timedelta(days=close_offset + 1)).isoformat(),
                        "received_steps": qty, "remaining_steps": qty,
                    }
                    active_lots.append(lot)
                    lot_rows.append(lot)

            sellable = [lot for lot in active_lots if lot["sales_close_date"] >= today.isoformat()
                        and lot["remaining_steps"] > 0]
            sellable.sort(key=lambda lot: (lot["sales_close_date"], lot["lot_id"]))
            stock = sum(lot["remaining_steps"] for lot in sellable)
            closing_candidates = sellable or [lot for lot in active_lots
                                             if lot["sales_close_date"] >= today.isoformat()]
            days_to_close = min((date.fromisoformat(lot["sales_close_date"]) - today).days
                                for lot in closing_candidates)
            # Prices vary independently of observed sales. Expiry only biases the offered discount.
            discount_pct = rng.choices((0, 5, 10, 15, 20, 30), weights=counts, k=1)[0]
            if days_to_close <= 2 and discount_pct:
                discount_pct = min(30, discount_pct + 5)
            intended_ratio = Decimal(100 - discount_pct) / Decimal(100)
            current_price = (Decimal(str(original_price)) * intended_ratio).quantize(
                Decimal("0.01"), rounding=ROUND_CEILING)
            ratio = round(float(current_price / Decimal(str(original_price))), 6)
            weekday = today.weekday()
            weekday_factor = weekend_factor if weekday in (5, 6) else 1.0
            expiry_factor = 0.92 if days_to_close <= 2 else 1.0
            latent_mean = interest * weekday_factor * expiry_factor * ratio ** (-elasticity)
            latent = _poisson(rng, latent_mean)
            remaining = latent
            for lot in sellable:
                taken = min(remaining, lot["remaining_steps"])
                if taken:
                    lot["remaining_steps"] -= taken
                    allocation_rows.append({"date": today.isoformat(), "lot_id": lot["lot_id"],
                                            "product_id": product_id, "sold_steps": taken})
                    remaining -= taken
                if remaining == 0:
                    break
            observed = latent - remaining
            demand_rows.append({
                "date": today.isoformat(), "split": split_for_day(day), "store_id": store_id,
                "product_id": product_id, "category": category, "price_ratio": ratio,
                "current_price": f"{current_price:.2f}", "days_to_close": days_to_close,
                "stock_steps": stock, "weekday": weekday, "lot_age_days": cycle_day,
                "lag7_sales_sum": sum(history[-7:]), "lag7_days": min(7, len(history)),
                "lag14_sales_sum": sum(history[-14:]), "lag14_days": min(14, len(history)),
                "latent_demand_steps": latent, "observed_sales_steps": observed,
                "stockout": int(observed < latent),
            })
            history.append(observed)
        for lot in active_lots:
            lot["unsold_steps"] = lot.pop("remaining_steps")

    metadata = {
        "dataset_version": DATASET_VERSION, "seed": seed, "start_date": start_date.isoformat(),
        "days": DAYS, "stores": {f"S{i + 1}": name for i, name in enumerate(STORES)},
        "feature_fields": list(FEATURE_FIELDS), "target_field": TARGET_FIELD,
        "split_boundaries": {"train_end": (start_date + timedelta(days=108)).isoformat(),
                             "validation_end": (start_date + timedelta(days=144)).isoformat()},
        "holdout_protocol": {"unseen_store": HOLDOUT_STORE, "unseen_product": HOLDOUT_PRODUCT,
                             "training_rule": "exclude both groups from model fitting and transforms"},
        "simulator": {
            "latent_mean_equation": "interest * weekday_factor * expiry_factor * price_ratio ** (-elasticity)",
            "weekday_factor": f"{weekend_factor} on Saturday/Sunday, otherwise 1.0",
            "expiry_factor": "synthetic 0.92 buyer-aversion assumption when earliest lot closes within two days, otherwise 1.0",
            "discount_rule": "observed discount frequencies; synthetic 5-point increase for already discounted near-expiry items, capped at 30%",
            "absolute_price_rule": "seeded uniform PEN 6-12 fruit or 7-15 nuts per step",
            "price_rounding": "round up to cent so intended discount floor is never crossed",
            "unit_cost_rule": "seeded 45%-70% of reference price; not observed in FreshRetailNet",
            "latent_distribution": "Poisson", "observed_sales": "min(latent demand, sellable stock)",
            "allocation": "earliest sales close first (FEFO)",
            "hidden_parameters_not_features": hidden,
        },
        "calibration": ({"source": calibration["source"],
                          "source_sha256": calibration["source_sha256"],
                          "profile_schema_version": calibration["schema_version"],
                          "weekend_ratio_used": weekend_factor,
                          "discount_bucket_counts": counts,
                          "real_stockout_day_fraction": calibration["stockout_day_fraction"]}
                         if calibration else {"source": "uncalibrated_defaults"}),
    }
    return demand_rows, lot_rows, allocation_rows, metadata


def baseline_metrics(rows):
    """A causal seven-day observed-sales mean, evaluated against latent demand."""
    selected = list(rows)
    if not selected:
        raise ValueError("cannot evaluate an empty split")
    errors = []
    stockouts = 0
    unobserved = 0
    for row in selected:
        days = int(row["lag7_days"])
        prediction = int(row["lag7_sales_sum"]) / days if days else 0.0
        latent = int(row["latent_demand_steps"])
        observed = int(row["observed_sales_steps"])
        errors.append(abs(prediction - latent))
        stockouts += int(row["stockout"])
        unobserved += latent - observed
    return {"rows": len(selected), "mae_steps_per_day": round(sum(errors) / len(errors), 4),
            "stockout_days": stockouts, "unobserved_demand_steps": unobserved}


def evaluate_splits(rows):
    return {split: baseline_metrics(row for row in rows if row["split"] == split)
            for split in ("train", "validation", "test")}


def evaluate_holdouts(rows):
    """Diagnostic groups for later testing with unseen store and product."""
    test_rows = [row for row in rows if row["split"] == "test"]
    return {
        "seen_groups": baseline_metrics(row for row in test_rows
                                        if row["store_id"] != HOLDOUT_STORE and
                                        row["product_id"] != HOLDOUT_PRODUCT),
        "unseen_product": baseline_metrics(row for row in test_rows
                                           if row["product_id"] == HOLDOUT_PRODUCT),
        "unseen_store": baseline_metrics(row for row in test_rows
                                         if row["store_id"] == HOLDOUT_STORE),
    }


def scenario_metrics(rows, lots, metadata):
    """Report observed simulator outcomes; future policies use the same definitions."""
    cost_by_product = {item["product_id"]: Decimal(str(item["unit_cost"]))
                       for item in metadata["simulator"]["hidden_parameters_not_features"]}
    result = {}
    for split in ("train", "validation", "test"):
        selected = [row for row in rows if row["split"] == split]
        sold = sum(row["observed_sales_steps"] for row in selected)
        revenue = sum((Decimal(str(row["current_price"])) * row["observed_sales_steps"]
                       for row in selected), Decimal("0"))
        cost = sum((cost_by_product[row["product_id"]] * row["observed_sales_steps"]
                    for row in selected), Decimal("0"))
        discount_sum = sum((Decimal(str(1 - row["price_ratio"])) * row["observed_sales_steps"]
                            for row in selected), Decimal("0"))
        result[split] = {
            "sold_steps": sold,
            "unsold_steps_at_close": sum(lot["unsold_steps"] for lot in lots if lot["split"] == split),
            "revenue_pen": f"{revenue:.2f}", "margin_pen": f"{revenue - cost:.2f}",
            "mean_realized_discount_pct": round(float(discount_sum * 100 / sold), 2) if sold else 0.0,
            "stock_violations": sum(int(row["observed_sales_steps"] > row["stock_steps"] or
                                        row["observed_sales_steps"] < 0) for row in selected),
            "price_violations": sum(int(Decimal(str(row["current_price"])) <= 0 or
                                        not 0.7 <= float(row["price_ratio"]) <= 1.0) for row in selected),
        }
    return result


def write_dataset(output_dir, seed=42, start_date=START_DATE):
    """Write reproducible files outside operational data; return their manifest."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    rows, lots, allocations, metadata = generate(seed, start_date)
    files = {}
    for name, records, fields in (("demand.csv", rows, DEMAND_FIELDS),
                                  ("lots.csv", lots, LOT_FIELDS),
                                  ("allocations.csv", allocations, ALLOCATION_FIELDS)):
        path = root / name
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)
        files[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rows": len(records)}
    manifest = {**metadata, "files": files, "baseline": evaluate_splits(rows),
                "holdout_baseline": evaluate_holdouts(rows),
                "scenario": scenario_metrics(rows, lots, metadata),
                "validation_state": "SYNTHETIC_BASELINE_ONLY"}
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2,
                                                    sort_keys=True) + "\n", encoding="utf-8")
    return manifest
