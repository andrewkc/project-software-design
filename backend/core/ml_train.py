"""Offline demand-model training for the synthetic DESSOF demo.

The model is experimental until a separate pricing-policy evaluation passes.
No operational database tables or external services are touched here.
"""

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import OneHotEncoder

from . import ml_data


FEATURES_VERSION = "demand-features-v1"
CATEGORICAL_FIELDS = ("store_id", "category")
# Product identity is omitted: recent sales already carry product-level signal,
# and a product unseen in fitting must still receive a sensible prediction.
NUMERIC_FIELDS = tuple(field for field in ml_data.FEATURE_FIELDS
                       if field not in CATEGORICAL_FIELDS and field != "product_id")
MODEL_FIELDS = CATEGORICAL_FIELDS + NUMERIC_FIELDS
MODEL_PARAMETERS = {
    "loss": "poisson", "max_iter": 250, "max_leaf_nodes": 15,
    "min_samples_leaf": 10, "learning_rate": 0.05,
    "l2_regularization": 1.0,
}


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _feature_matrix(rows):
    if not rows:
        raise ValueError("no rows to transform")
    result = []
    for row in rows:
        missing = set(MODEL_FIELDS) - row.keys()
        if missing:
            raise ValueError(f"missing model features: {sorted(missing)}")
        numeric = []
        for field in NUMERIC_FIELDS:
            value = float(row[field])
            if not math.isfinite(value):
                raise ValueError(f"non-finite model feature: {field}")
            numeric.append(value)
        result.append([str(row[field]) for field in CATEGORICAL_FIELDS] + numeric)
    return result


def _selected(rows, split, group="all"):
    selected = [row for row in rows if row["split"] == split]
    if group == "seen":
        return [row for row in selected if row["store_id"] != ml_data.HOLDOUT_STORE
                and row["product_id"] != ml_data.HOLDOUT_PRODUCT]
    if group == "unseen_product":
        return [row for row in selected if row["product_id"] == ml_data.HOLDOUT_PRODUCT]
    if group == "unseen_store":
        return [row for row in selected if row["store_id"] == ml_data.HOLDOUT_STORE]
    if group != "all":
        raise ValueError(f"unknown evaluation group: {group}")
    return selected


def train_model(seed=42):
    """Fit on past rows from seen groups only; leave all later rows untouched."""
    rows, _, _, source = ml_data.generate(seed=seed)
    if source["calibration"]["source"] != ml_data.load_calibration()["source"]:
        raise ValueError("training requires the FreshRetailNet calibration profile")
    train = _selected(rows, "train", "seen")
    if not train:
        raise ValueError("no training rows")
    transformer = ColumnTransformer(
        [("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False),
          list(range(len(CATEGORICAL_FIELDS)))),
         ("numeric", "passthrough", list(range(len(CATEGORICAL_FIELDS),
                                               len(MODEL_FIELDS))))],
        sparse_threshold=0,
    )
    x_train = transformer.fit_transform(_feature_matrix(train))
    constraints = [0] * x_train.shape[1]
    numeric_start = x_train.shape[1] - len(NUMERIC_FIELDS)
    for name in ("price_ratio", "current_price"):
        constraints[numeric_start + NUMERIC_FIELDS.index(name)] = -1
    model = HistGradientBoostingRegressor(
        **MODEL_PARAMETERS, monotonic_cst=constraints, random_state=seed,
    )
    model.fit(x_train, [row[ml_data.TARGET_FIELD] for row in train])
    bundle = {"transformer": transformer, "model": model,
              "feature_fields": MODEL_FIELDS,
              "features_version": FEATURES_VERSION}
    report = {
        "state": "EXPERIMENTAL", "seed": seed,
        "dataset_version": source["dataset_version"],
        "calibration_sha256": source["calibration"]["source_sha256"],
        "features_version": FEATURES_VERSION,
        "feature_fields": list(MODEL_FIELDS),
        "model_parameters": {**MODEL_PARAMETERS, "monotonic_price_features":
                             ["price_ratio", "current_price"]},
        "versions": {"scikit_learn": sklearn.__version__, "numpy": np.__version__},
        "rows_fit": len(train),
        "evaluation": {},
    }
    for split, group in (("validation", "seen"), ("test", "all"),
                         ("test", "seen"), ("test", "unseen_product"),
                         ("test", "unseen_store")):
        subset = _selected(rows, split, group)
        report["evaluation"][f"{split}_{group}"] = evaluate(bundle, subset)
    for stress_seed in (43, 44, 45, 46, 47):
        stress_rows, _, _, _ = ml_data.generate(seed=stress_seed)
        report["evaluation"][f"stress_seed_{stress_seed}"] = evaluate(
            bundle, _selected(stress_rows, "test"))
    report["monotonic_price_violations"] = monotonic_price_violations(
        bundle, _selected(rows, "test", "seen")[:30])
    report["demand_quality_gate"] = (
        report["monotonic_price_violations"] == 0 and
        all(report["evaluation"][name]["model_mae"] <=
            report["evaluation"][name]["baseline_mae"]
            for name in ("validation_seen", "test_all", "test_unseen_product",
                         "test_unseen_store", "stress_seed_43", "stress_seed_44",
                         "stress_seed_45", "stress_seed_46", "stress_seed_47"))
    )
    return bundle, report


def predict(bundle, rows):
    if tuple(bundle["feature_fields"]) != MODEL_FIELDS:
        raise ValueError("model feature schema mismatch")
    values = bundle["model"].predict(bundle["transformer"].transform(
        _feature_matrix(rows)))
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("model returned invalid demand")
    return values


def evaluate(bundle, rows):
    if not rows:
        raise ValueError("empty evaluation group")
    actual = [row[ml_data.TARGET_FIELD] for row in rows]
    estimated = predict(bundle, rows)
    baseline = [row["lag7_sales_sum"] / row["lag7_days"]
                if row["lag7_days"] else 0.0 for row in rows]
    return {"rows": len(rows),
            "model_mae": round(float(mean_absolute_error(actual, estimated)), 4),
            "baseline_mae": round(float(mean_absolute_error(actual, baseline)), 4)}


def monotonic_price_violations(bundle, rows):
    """Increasing both price features must not increase predicted demand."""
    count = 0
    for row in rows:
        reference = float(row["current_price"]) / float(row["price_ratio"])
        variants = [{**row, "price_ratio": ratio,
                     "current_price": round(reference * ratio, 2)}
                    for ratio in (0.7, 0.8, 0.9, 1.0)]
        predictions = predict(bundle, variants)
        count += sum(a + 1e-9 < b for a, b in zip(predictions, predictions[1:]))
    return int(count)


def train_and_save(output_dir, seed=42):
    """Save a hash-verified local artifact and a readable evaluation report."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    bundle, report = train_model(seed=seed)
    artifact = output / f"demand-seed-{seed}.joblib"
    temporary = output / f"demand-seed-{seed}.joblib.tmp"
    joblib.dump(bundle, temporary)
    temporary.replace(artifact)
    report["artifact"] = artifact.name
    report["artifact_sha256"] = _sha256(artifact)
    report["trained_at_utc"] = datetime.now(timezone.utc).isoformat()
    report_path = output / f"demand-seed-{seed}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                      sort_keys=True) + "\n", encoding="utf-8")
    return report


def load_trained(artifact_path, report_path):
    """Only load our own trusted local artifact after verifying its hash."""
    artifact = Path(artifact_path)
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    if report.get("artifact") != artifact.name or report.get("artifact_sha256") != _sha256(artifact):
        raise ValueError("model artifact hash mismatch")
    if report.get("features_version") != FEATURES_VERSION:
        raise ValueError("incompatible model feature version")
    if report.get("versions", {}).get("scikit_learn") != sklearn.__version__:
        raise ValueError("incompatible scikit-learn version")
    return joblib.load(artifact), report
