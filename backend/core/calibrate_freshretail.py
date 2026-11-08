"""Summarize FreshRetailNet training data without copying its customer-level rows.

Requires DuckDB only when this command runs. The resulting profile contains
aggregate observed patterns, never invented expiry dates or currency prices.
"""

import argparse
import hashlib
import json
from pathlib import Path


SOURCE = "Dingdong-Inc/FreshRetailNet-50K"
DISCOUNT_BUCKETS = (0, 5, 10, 15, 20, 30)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_profile(parquet_path):
    """Use full training split; exclude malformed discounts from price summaries."""
    import duckdb

    path = Path(parquet_path)
    if not path.is_file():
        raise ValueError(f"missing parquet file: {path}")
    db = duckdb.connect()
    try:
        db.from_parquet(str(path)).create_view("source")
        required = {"store_id", "product_id", "dt", "sale_amount", "discount",
                    "stock_hour6_22_cnt", "activity_flag", "holiday_flag"}
        columns = {row[1] for row in db.execute("PRAGMA table_info('source')").fetchall()}
        if not required <= columns:
            raise ValueError(f"missing columns: {sorted(required - columns)}")
        rows, stores, products, first, last, stockout_days, stockout_hours, invalid = db.execute("""
            SELECT count(*), count(DISTINCT store_id), count(DISTINCT product_id),
                   min(dt), max(dt),
                   avg(CAST(stock_hour6_22_cnt > 0 AS DOUBLE)),
                   avg(stock_hour6_22_cnt / 16.0),
                   sum(CAST(discount IS NULL OR discount <= 0 OR discount > 1 AS BIGINT))
            FROM source
        """).fetchone()
        if rows < 1000 or stores < 2 or products < 2:
            raise ValueError("source is too small for calibration")
        if not 0 <= stockout_days <= 1 or not 0 <= stockout_hours <= 1:
            raise ValueError("invalid stockout values")
        counts = db.execute("""
            SELECT CASE WHEN discount >= 0.975 THEN 0
                        WHEN discount >= 0.925 THEN 5
                        WHEN discount >= 0.875 THEN 10
                        WHEN discount >= 0.825 THEN 15
                        WHEN discount >= 0.75 THEN 20 ELSE 30 END AS bucket,
                   count(*) FROM source
            WHERE discount > 0 AND discount <= 1
            GROUP BY 1 ORDER BY 1
        """).fetchall()
        # Compare like-for-like, fully stocked, undiscounted days
        # within each store-product series. This is descriptive, not causal.
        weekend = db.execute("""
            WITH series AS (
                SELECT store_id, product_id,
                       avg(CASE WHEN dayofweek(CAST(dt AS DATE)) IN (0, 6)
                                THEN sale_amount END) AS weekend_sales,
                       avg(CASE WHEN dayofweek(CAST(dt AS DATE)) NOT IN (0, 6)
                                THEN sale_amount END) AS weekday_sales,
                       count(CASE WHEN dayofweek(CAST(dt AS DATE)) IN (0, 6)
                                  THEN 1 END) AS weekend_n,
                       count(CASE WHEN dayofweek(CAST(dt AS DATE)) NOT IN (0, 6)
                                  THEN 1 END) AS weekday_n
                FROM source
                WHERE stock_hour6_22_cnt = 0 AND discount = 1
                GROUP BY store_id, product_id
            )
            SELECT median(weekend_sales / weekday_sales), count(*)
            FROM series
            WHERE weekend_n >= 3 AND weekday_n >= 7 AND weekday_sales > 0
                  AND weekend_sales IS NOT NULL
        """).fetchone()
        if weekend[0] is None or weekend[1] < 100:
            raise ValueError("insufficient comparable series for weekend calibration")
        buckets = dict(counts)
        total = sum(buckets.values())
        if total == 0:
            raise ValueError("no valid discounts")
        return {
            "schema_version": 1,
            "source": SOURCE,
            "source_split": "train",
            "source_sha256": _sha256(path),
            "rows": rows, "stores": stores, "products": products,
            "first_date": first, "last_date": last,
            "discount_bucket_pct": list(DISCOUNT_BUCKETS),
            "discount_bucket_counts": [buckets.get(x, 0) for x in DISCOUNT_BUCKETS],
            "discount_valid_rows": total,
            "discount_invalid_rows": invalid,
            "stockout_day_fraction": round(stockout_days, 6),
            "stockout_open_hour_fraction": round(stockout_hours, 6),
            "weekend_weekday_sales_ratio": round(float(weekend[0]), 6),
            "weekend_comparable_series": weekend[1],
            "interpretation": {
                "weekend_ratio": "observed association among fully stocked, undiscounted days; events may remain",
                "discount_buckets": "observed frequencies, not causal price elasticity",
                "stockouts": "real descriptive benchmark; not forced into synthetic inventory",
                "missing": ["lot expiry", "unit cost", "absolute price", "uncensored demand"],
            },
        }
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Calibrate simulator from FreshRetailNet train.parquet")
    parser.add_argument("parquet", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    profile = build_profile(args.parquet)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Calibrated {profile['rows']} real rows; profile: {args.output}")


if __name__ == "__main__":
    main()
